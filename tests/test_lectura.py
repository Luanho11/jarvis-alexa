import io
import os
import socket
import sys

import pytest
import requests
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from acciones import archivos, lectura

PUBLICA = "93.184.216.34"


def crear_pdf(textos, clave=None, propietario=None) -> bytes:
    escritor = PdfWriter()
    fuente = escritor._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for texto in textos:
        pagina = escritor.add_blank_page(612, 792)
        pagina[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): fuente})})
        contenido = DecodedStreamObject()
        if texto:
            contenido.set_data(f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1"))
        pagina[NameObject("/Contents")] = escritor._add_object(contenido)
    if clave is not None:
        escritor.encrypt(clave, owner_password=propietario, algorithm="AES-128")
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()


@pytest.fixture
def casa(tmp_path, monkeypatch):
    monkeypatch.setattr(archivos.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setitem(sys.modules, "winreg", None)
    for carpeta in ("Documents", "Downloads", "Desktop"):
        (tmp_path / carpeta).mkdir()
    return tmp_path


class Respuesta:
    def __init__(self, contenido=b"", tipo="text/html; charset=utf-8", estado=200, ubicacion=None):
        self.contenido = contenido
        self.status_code = estado
        self.headers = {"Content-Type": tipo}
        if ubicacion:
            self.headers["Location"] = ubicacion
        self.is_redirect = ubicacion is not None
        self.leido = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def iter_content(self, tamano):
        for inicio in range(0, len(self.contenido), tamano):
            self.leido += tamano
            yield self.contenido[inicio:inicio + tamano]


@pytest.fixture
def red(monkeypatch):
    """Simula DNS y HTTP: ips[host] es la IP que resuelve; respuestas[url] lo que devuelve."""
    estado = {"ips": {}, "respuestas": {}, "pedidas": []}

    def resolver(host, puerto, proto=0):
        if host not in estado["ips"]:
            raise socket.gaierror("no existe")
        ips = estado["ips"][host]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in (ips if isinstance(ips, list) else [ips])]

    def pedir(url, **opciones):
        assert opciones["allow_redirects"] is False and opciones["stream"] is True
        assert opciones["timeout"] == lectura.TIEMPO_LIMITE
        estado["pedidas"].append(url)
        respuesta = estado["respuestas"][url]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(lectura.socket, "getaddrinfo", resolver)
    monkeypatch.setattr(lectura.requests, "get", pedir)
    return estado


ARTICULO = (
    "<html><head><title>Noticia</title></head><body><nav>Menú Inicio Contacto</nav><article>"
    "<h1>El río crece</h1>"
    + "".join(f"<p>Párrafo {numero} de la noticia sobre el río que creció durante la tormenta de anoche.</p>" for numero in range(8))
    + "</article><footer>Copyright</footer></body></html>"
).encode("utf-8")


def test_pdf_de_dos_paginas(casa):
    (casa / "Documents" / "Contrato.pdf").write_bytes(crear_pdf(["Primera clausula", "Segunda clausula"]))
    assert lectura.leer_documento("contrato") == "«Contrato.pdf», 2 páginas, págs. 1-2: Primera clausula\nSegunda clausula"


def test_pdf_protegido_con_contrasena(casa):
    (casa / "Documents" / "secreto.pdf").write_bytes(crear_pdf(["oculto"], clave="clave123"))
    assert lectura.leer_documento("secreto") == "«secreto.pdf» está protegido con contraseña."


def test_pdf_solo_con_contrasena_de_propietario_se_lee(casa):
    (casa / "Documents" / "banco.pdf").write_bytes(crear_pdf(["Saldo final"], clave="", propietario="dueno"))
    assert lectura.leer_documento("banco") == "«banco.pdf», 1 página, pág. 1: Saldo final"


def test_pdf_escaneado(casa):
    (casa / "Documents" / "escaneo.pdf").write_bytes(crear_pdf(["", ""]))
    assert "parece escaneado" in lectura.leer_documento("escaneo")


def test_pdf_danado(casa):
    (casa / "Documents" / "roto.pdf").write_bytes(b"esto no es un pdf")
    assert lectura.leer_documento("roto") == "No pude leer «roto.pdf», parece dañado."


def test_pdf_largo_se_corta_en_paginas_enteras(casa):
    paginas = [letra * 2500 for letra in "abcd"]
    (casa / "Documents" / "libro.pdf").write_bytes(crear_pdf(paginas))
    primera = lectura.leer_documento("libro")
    assert primera.startswith("«libro.pdf», 4 páginas, págs. 1-2: ")
    assert primera.endswith("…(sigue en la página 3)")
    assert "c" not in primera.split(": ", 1)[1]
    segunda = lectura.leer_documento("libro", pagina_inicial=3)
    assert segunda == f"«libro.pdf», 4 páginas, págs. 3-4: {'c' * 2500}\n{'d' * 2500}"
    assert lectura.leer_documento("libro", pagina_inicial=9) == "«libro.pdf» solo tiene 4 páginas."


def test_pagina_que_no_cabe_se_recorta_y_sigue_en_la_siguiente(casa):
    (casa / "Documents" / "enorme.pdf").write_bytes(crear_pdf(["x" * 7000, "fin"]))
    texto = lectura.leer_documento("enorme")
    assert texto == f"«enorme.pdf», 2 páginas, pág. 1: {'x' * lectura.MAX_TEXTO}…(sigue en la página 2)"


def test_pagina_inicial_invalida_empieza_en_la_primera(casa):
    (casa / "Documents" / "corto.pdf").write_bytes(crear_pdf(["hola"]))
    assert lectura.leer_documento("corto", pagina_inicial=0) == "«corto.pdf», 1 página, pág. 1: hola"
    assert lectura.leer_documento("corto", pagina_inicial=2) == "«corto.pdf» solo tiene 1 página."


def test_word_con_tabla(casa):
    documento = Document()
    documento.add_paragraph("Informe trimestral")
    tabla = documento.add_table(rows=1, cols=2)
    tabla.rows[0].cells[0].text = "Ventas"
    tabla.rows[0].cells[1].text = "100"
    documento.save(casa / "Desktop" / "Informe.docx")
    assert lectura.leer_documento("informe") == "«Informe.docx»: Informe trimestral\nVentas | 100"


def test_word_danado(casa):
    (casa / "Desktop" / "malo.docx").write_bytes(b"PK\x03\x04basura")
    assert lectura.leer_documento("malo") == "No pude leer «malo.docx», parece dañado."


def test_texto_utf8_con_bom_y_ansi(casa):
    (casa / "Documents" / "lista.txt").write_bytes("\ufeffpan\n\n  leche   entera \n".encode("utf-8"))
    (casa / "Documents" / "viejo.csv").write_bytes("año;niño\n2026;sí".encode("cp1252"))
    assert lectura.leer_documento("lista") == "«lista.txt»: pan\nleche entera"
    assert lectura.leer_documento("viejo") == "«viejo.csv»: año;niño\n2026;sí"


def test_texto_vacio(casa):
    (casa / "Documents" / "vacio.md").write_text("   \n", encoding="utf-8")
    assert lectura.leer_documento("vacio") == "«vacio.md» no tiene texto."


def test_texto_largo_por_partes(casa):
    (casa / "Documents" / "largo.txt").write_text("a" * 13000, encoding="utf-8")
    primera = lectura.leer_documento("largo")
    assert primera == f"«largo.txt», parte 1 de 3: {'a' * 6000}…(sigue en la parte 2)"
    assert lectura.leer_documento("largo", 3) == f"«largo.txt», parte 3 de 3: {'a' * 1000}"
    assert lectura.leer_documento("largo", 4) == "«largo.txt» solo tiene 3 partes."


def test_no_encontrado(casa):
    assert lectura.leer_documento("factura") == "No encontré ningún documento con factura."


def test_ignora_otras_extensiones_y_bloqueos_de_word(casa):
    (casa / "Documents" / "foto contrato.jpg").touch()
    (casa / "Documents" / "~$contrato.docx").write_bytes(b"x")
    assert lectura.leer_documento("contrato") == "No encontré ningún documento con contrato."


def test_varias_coincidencias_pregunta_por_las_mas_recientes(casa):
    for numero in range(4):
        ruta = casa / "Documents" / f"factura {numero}.pdf"
        ruta.write_bytes(crear_pdf(["x"]))
        os.utime(ruta, (numero, numero))
    assert lectura.leer_documento("factura") == (
        "Encontré 4 documentos. Los más recientes: factura 3.pdf, factura 2.pdf, factura 1.pdf. ¿Cuál leo?"
    )


def test_prefiere_el_nombre_exacto(casa):
    (casa / "Documents" / "notas.txt").write_text("exacto", encoding="utf-8")
    (casa / "Documents" / "notas viejas.txt").write_text("otro", encoding="utf-8")
    assert lectura.leer_documento("Notas") == "«notas.txt»: exacto"


def test_tipo_pedido_filtra_por_extension(casa):
    (casa / "Documents" / "contrato.pdf").write_bytes(crear_pdf(["en pdf"]))
    documento = Document()
    documento.add_paragraph("en word")
    documento.save(casa / "Documents" / "contrato.docx")
    assert lectura.leer_documento("el contrato en pdf").endswith(": en pdf")
    assert lectura.leer_documento("contrato word") == "«contrato.docx»: en word"
    assert lectura.leer_documento("contrato.docx") == "«contrato.docx»: en word"


def test_el_ultimo_pdf_de_descargas(casa):
    for numero, nombre in enumerate(["viejo.pdf", "nuevo.pdf", "reciente.txt"]):
        ruta = casa / "Downloads" / nombre
        ruta.write_bytes(crear_pdf([nombre.split(".")[0]]) if nombre.endswith(".pdf") else b"texto")
        os.utime(ruta, (numero, numero))
    assert lectura.leer_documento("el último pdf de descargas").endswith(": nuevo")
    assert lectura.leer_documento("el documento más reciente") == "«reciente.txt»: texto"


def test_el_ultimo_sin_descargas(casa):
    assert lectura.leer_documento("el último pdf") == "No encontré documentos en Descargas."


def test_ruta_absoluta(tmp_path):
    ruta = tmp_path / "fuera de carpetas.txt"
    ruta.write_text("directo", encoding="utf-8")
    assert lectura.leer_documento(f'"{ruta}"') == "«fuera de carpetas.txt»: directo"


def test_origen_vacio():
    assert lectura.leer_documento("  ") == "Dime qué documento o página quieres que lea."
    assert lectura.leer_documento("el pdf") == "Dime el nombre del documento o la página que quieres que lea."


@pytest.mark.parametrize(
    "origen, es_url",
    [
        ("https://elpais.com/a", True),
        ("elpais.com/internacional/nota.html", True),
        ("www.wikipedia.org", True),
        ("file:///C:/", True),
        ("contrato.pdf", False),
        ("notas.md", False),
        ("informe final", False),
        (r"C:\Users\ana\contrato.pdf", False),
        ("C:/Users/ana/contrato.pdf", False),
    ],
)
def test_distingue_urls_de_archivos(origen, es_url):
    assert lectura._es_url(origen) is es_url


def test_lee_una_web_con_trafilatura(red):
    red["ips"]["noticias.ejemplo.com"] = PUBLICA
    red["respuestas"]["https://noticias.ejemplo.com/rio"] = Respuesta(ARTICULO)
    texto = lectura.leer_documento("noticias.ejemplo.com/rio")
    assert texto.startswith("«noticias.ejemplo.com»: ")
    assert "Párrafo 3 de la noticia" in texto
    assert "Menú Inicio" not in texto and "Copyright" not in texto


def test_web_de_texto_plano_y_por_partes(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/a.txt"] = Respuesta(("b" * 7000).encode(), tipo="text/plain")
    assert lectura.leer_documento("https://ejemplo.com/a.txt", 2) == f"«ejemplo.com», parte 2 de 2: {'b' * 1000}"


def test_web_sin_texto(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/"] = Respuesta(b"<html><body></body></html>")
    assert lectura.leer_documento("https://ejemplo.com/") == "No encontré texto que leer en esa página."


@pytest.mark.parametrize(
    "url, ip",
    [
        ("http://127.0.0.1:5000/hud", "127.0.0.1"),
        ("http://192.168.1.1", "192.168.1.1"),
        ("http://10.0.0.5/admin", "10.0.0.5"),
        ("http://169.254.169.254/latest/meta-data", "169.254.169.254"),
        ("http://localhost:5000", "::1"),
        ("http://0x7f000001/", "127.0.0.1"),
        ("http://router.trampa.com/", "::ffff:192.168.0.1"),
        ("http://multicast.trampa.com/", "224.0.0.1"),
        ("http://mixta.trampa.com/", [PUBLICA, "192.168.1.1"]),
    ],
)
def test_rechaza_la_red_local(red, url, ip):
    from urllib.parse import urlsplit

    red["ips"][urlsplit(url).hostname] = ip
    assert lectura.leer_documento(url) == "Por seguridad no leo direcciones de tu red local ni de este PC."
    assert red["pedidas"] == []


@pytest.mark.parametrize("url", ["file:///C:/Windows/win.ini", "ftp://ejemplo.com/a.txt", "javascript://x"])
def test_solo_http_y_https(red, url):
    assert lectura.leer_documento(url) == "Solo leo páginas web que empiecen por http o https."
    assert red["pedidas"] == []


def test_host_que_no_existe(red):
    assert lectura.leer_documento("https://no-existe.ejemplo") == "No pude abrir esa página."


def test_redireccion_a_la_red_local_se_bloquea(red):
    red["ips"]["acortador.com"] = PUBLICA
    red["ips"]["192.168.1.1"] = "192.168.1.1"
    red["respuestas"]["https://acortador.com/x"] = Respuesta(estado=302, ubicacion="http://192.168.1.1/config")
    assert lectura.leer_documento("https://acortador.com/x") == "Por seguridad no leo direcciones de tu red local ni de este PC."
    assert red["pedidas"] == ["https://acortador.com/x"]


def test_sigue_redirecciones_relativas(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/viejo"] = Respuesta(estado=301, ubicacion="/nuevo")
    red["respuestas"]["https://ejemplo.com/nuevo"] = Respuesta(b"hola", tipo="text/plain")
    assert lectura.leer_documento("https://ejemplo.com/viejo") == "«ejemplo.com»: hola"


def test_demasiadas_redirecciones(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/bucle"] = Respuesta(estado=302, ubicacion="/bucle")
    assert lectura.leer_documento("https://ejemplo.com/bucle") == "Esa página redirige demasiadas veces."
    assert len(red["pedidas"]) == lectura.MAX_REDIRECCIONES + 1


def test_respuesta_enorme_se_corta_a_2_mb(red, monkeypatch):
    red["ips"]["ejemplo.com"] = PUBLICA
    respuesta = Respuesta(b"<p>" + b"a" * (5 * 1024 * 1024) + b"</p>")
    red["respuestas"]["https://ejemplo.com/"] = respuesta
    recibido = []
    monkeypatch.setattr(lectura, "_texto_html", lambda contenido, url: recibido.append(len(contenido)) or "corto")
    assert lectura.leer_documento("https://ejemplo.com/") == "«ejemplo.com»: corto"
    assert recibido == [lectura.MAX_DESCARGA]
    assert respuesta.leido <= lectura.MAX_DESCARGA + 64 * 1024


def test_tiempo_agotado(red):
    red["ips"]["lenta.com"] = PUBLICA
    red["respuestas"]["https://lenta.com/"] = requests.Timeout()
    assert lectura.leer_documento("https://lenta.com/") == "No pude abrir esa página."


def test_error_http(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/nada"] = Respuesta(estado=404)
    assert lectura.leer_documento("https://ejemplo.com/nada") == "No pude abrir esa página (error 404)."


def test_pdf_descargado_se_lee_como_archivo(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/doc"] = Respuesta(crear_pdf(["Hola", "Adios"]), tipo="application/pdf")
    assert lectura.leer_documento("https://ejemplo.com/doc", 2) == "«ejemplo.com», 2 páginas, pág. 2: Adios"


def test_pdf_descargado_demasiado_grande(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/gran.pdf"] = Respuesta(b"%PDF" + b"0" * (3 * 1024 * 1024), tipo="application/pdf")
    assert "demasiado grande" in lectura.leer_documento("https://ejemplo.com/gran.pdf")


def test_tipo_no_soportado(red):
    red["ips"]["ejemplo.com"] = PUBLICA
    red["respuestas"]["https://ejemplo.com/foto"] = Respuesta(b"\x89PNG", tipo="image/png")
    assert lectura.leer_documento("https://ejemplo.com/foto") == "Esa dirección no es una página de texto ni un PDF."
