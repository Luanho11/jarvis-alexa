import io
import ipaddress
import re
import socket
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from docx import Document
from docx.opc.exceptions import OpcError
from pypdf import PdfReader
from pypdf.errors import DependencyError, PyPdfError

from acciones.archivos import buscar_rutas, ruta_carpeta
from acciones.programas import normalizar

# ~1.700 tokens: cabe en una ronda de Groq gratis junto al resto del prompt.
MAX_TEXTO = 6000
MAX_DESCARGA = 2 * 1024 * 1024
MAX_ARCHIVO_TEXTO = 20 * 1024 * 1024
TIEMPO_LIMITE = 4
TIEMPO_TOTAL = 8
MAX_REDIRECCIONES = 5
MAXIMO_LISTADO = 3
EXTENSIONES = {".pdf", ".docx", ".txt", ".md", ".csv"}
TIPOS_PEDIDOS = {"pdf": {".pdf"}, "word": {".docx"}, "docx": {".docx"}, "texto": {".txt", ".md"}, "txt": {".txt"}}
PALABRAS_SOBRANTES = {"el", "la", "los", "las", "mi", "archivo", "documento", "de", "en", "que", "tengo", "descargas"}
# Algunas webs rechazan el User-Agent de requests.
CABECERAS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/1.0"}
DOMINIO = re.compile(r"^[\w-]+(\.[\w-]+)+(:\d+)?(/.*)?$")

NO_ABRE = "No pude abrir esa página."


class Bloqueada(Exception):
    pass


def _ip_publica(direccion: str) -> bool:
    ip = ipaddress.ip_address(direccion)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _comprobar_url(url: str) -> None:
    """Lanza Bloqueada si la URL no es http(s) o su host resuelve a una IP de la red local."""
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise Bloqueada("Solo leo páginas web que empiecen por http o https.")
    try:
        direcciones = socket.getaddrinfo(partes.hostname, None, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError):
        raise Bloqueada(NO_ABRE) from None
    # Todas, no solo la primera: requests puede conectar a cualquiera de ellas.
    if not direcciones or not all(_ip_publica(direccion[4][0]) for direccion in direcciones):
        raise Bloqueada("Por seguridad no leo direcciones de tu red local ni de este PC.")


def _descargar(url: str) -> tuple[bytes, str, str]:
    """Contenido (como mucho MAX_DESCARGA), tipo y URL final. Cada redirección se comprueba de nuevo."""
    limite = time.monotonic() + TIEMPO_TOTAL
    for _ in range(MAX_REDIRECCIONES + 1):
        _comprobar_url(url)
        respuesta = requests.get(url, headers=CABECERAS, timeout=TIEMPO_LIMITE, stream=True, allow_redirects=False)
        with respuesta:
            if respuesta.is_redirect:
                url = urljoin(url, respuesta.headers["Location"])
                continue
            respuesta.raise_for_status()
            contenido = bytearray()
            for trozo in respuesta.iter_content(64 * 1024):
                contenido += trozo
                if len(contenido) >= MAX_DESCARGA or time.monotonic() > limite:
                    break
            tipo = respuesta.headers.get("Content-Type", "").split(";")[0].strip().lower()
            return bytes(contenido[:MAX_DESCARGA]), tipo, url
    raise Bloqueada("Esa página redirige demasiadas veces.")


def _texto_html(contenido: bytes, url: str) -> str:
    # trafilatura tarda ~0,5 s en importarse: solo se carga la primera vez que se lee una web.
    import trafilatura

    return trafilatura.extract(contenido, url=url, include_comments=False) or ""


def _cuantas(numero: int, palabra: str) -> str:
    return f"{numero} {palabra}" if numero == 1 else f"{numero} {palabra}s"


def _limpiar(texto: str) -> str:
    lineas = (" ".join(linea.split()) for linea in texto.splitlines())
    return "\n".join(linea for linea in lineas if linea)


def _en_partes(nombre: str, texto: str, parte: int) -> str:
    texto = _limpiar(texto)
    if not texto:
        return f"«{nombre}» no tiene texto."
    total = -(-len(texto) // MAX_TEXTO)
    if parte > total:
        return f"«{nombre}» solo tiene {_cuantas(total, 'parte')}."
    trozo = texto[(parte - 1) * MAX_TEXTO:parte * MAX_TEXTO]
    if total == 1:
        return f"«{nombre}»: {trozo}"
    sigue = f"…(sigue en la parte {parte + 1})" if parte < total else ""
    return f"«{nombre}», parte {parte} de {total}: {trozo}{sigue}"


def _leer_pdf(nombre: str, origen, pagina_inicial: int) -> str:
    try:
        lector = PdfReader(origen)
        # Muchos PDF solo tienen contraseña de propietario (impide editar): se abren con la contraseña vacía.
        if lector.is_encrypted and not lector.decrypt(""):
            return f"«{nombre}» está protegido con contraseña."
        paginas = lector.pages
        total = len(paginas)
        if pagina_inicial > total:
            return f"«{nombre}» solo tiene {_cuantas(total, 'página')}."
        textos = []
        largo = 0
        numero = pagina_inicial
        while numero <= total:
            texto = _limpiar(paginas[numero - 1].extract_text() or "")
            if largo + len(texto) > MAX_TEXTO:
                # Se cortan solo páginas enteras para que "sigue en la página N" no pierda texto,
                # salvo si la primera ya no cabe: entonces se recorta y se sigue en la siguiente.
                if not textos:
                    textos.append(texto[:MAX_TEXTO])
                    numero += 1
                break
            textos.append(texto)
            largo += len(texto) + 1
            numero += 1
    except DependencyError:
        return f"«{nombre}» está protegido con contraseña."
    except (PyPdfError, OSError, ValueError, KeyError, TypeError):
        return f"No pude leer «{nombre}», parece dañado."
    texto = "\n".join(texto for texto in textos if texto)
    if not texto:
        return f"«{nombre}» parece escaneado; ábrelo y pídeme que mire la pantalla."
    ultima = numero - 1
    rango = f"pág. {pagina_inicial}" if ultima == pagina_inicial else f"págs. {pagina_inicial}-{ultima}"
    sigue = f"…(sigue en la página {numero})" if numero <= total else ""
    return f"«{nombre}», {_cuantas(total, 'página')}, {rango}: {texto}{sigue}"


def _leer_docx(ruta: Path) -> str:
    documento = Document(ruta)
    lineas = [parrafo.text for parrafo in documento.paragraphs]
    for tabla in documento.tables:
        lineas += [" | ".join(celda.text for celda in fila.cells) for fila in tabla.rows]
    return "\n".join(lineas)


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        # El Bloc de notas antiguo y Excel guardan en ANSI.
        return contenido.decode("cp1252", errors="replace")


def _leer_archivo(ruta: Path, pagina_inicial: int) -> str:
    extension = ruta.suffix.lower()
    if extension == ".pdf":
        return _leer_pdf(ruta.name, ruta, pagina_inicial)
    try:
        if extension == ".docx":
            texto = _leer_docx(ruta)
        else:
            with ruta.open("rb") as archivo:
                texto = _decodificar(archivo.read(MAX_ARCHIVO_TEXTO))
    except PermissionError:
        return f"«{ruta.name}» está bloqueado por otro programa."
    except (OSError, ValueError, KeyError, OpcError, zipfile.BadZipFile):
        return f"No pude leer «{ruta.name}», parece dañado."
    return _en_partes(ruta.name, texto, pagina_inicial)


def _leer_web(url: str, pagina_inicial: int) -> str:
    try:
        contenido, tipo, url = _descargar(url)
    except Bloqueada as error:
        return str(error)
    except requests.HTTPError as error:
        return f"{NO_ABRE[:-1]} (error {error.response.status_code})."
    except requests.RequestException:
        return NO_ABRE
    nombre = urlsplit(url).hostname
    if tipo == "application/pdf" or contenido.startswith(b"%PDF"):
        if len(contenido) >= MAX_DESCARGA:
            return "Ese PDF es demasiado grande para leerlo desde internet: descárgalo y te lo leo."
        return _leer_pdf(nombre, io.BytesIO(contenido), pagina_inicial)
    if tipo in ("text/html", "application/xhtml+xml", ""):
        texto = _texto_html(contenido, url)
    elif tipo.startswith("text/"):
        texto = _decodificar(contenido)
    else:
        return "Esa dirección no es una página de texto ni un PDF."
    if not _limpiar(texto):
        return "No encontré texto que leer en esa página."
    return _en_partes(nombre, texto, pagina_inicial)


def _es_url(origen: str) -> bool:
    if "://" in origen:
        return True
    if "/" not in origen and Path(origen).suffix.lower() in EXTENSIONES:
        return False
    return bool(DOMINIO.match(origen))


def _mas_reciente(extensiones: set[str]) -> Path | None:
    descargas = ruta_carpeta("descargas")
    if descargas is None:
        return None
    archivos = [
        ruta for ruta in descargas.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in extensiones and not ruta.name.startswith("~$")
    ]
    return max(archivos, key=lambda ruta: ruta.stat().st_mtime) if archivos else None


def _pedido(origen: str) -> tuple[str, set[str], bool]:
    """Nombre a buscar, extensiones aceptadas y si pide el más reciente de Descargas."""
    texto = normalizar(origen)
    ruta = Path(texto)
    extensiones = EXTENSIONES
    if ruta.suffix in EXTENSIONES:
        extensiones = {ruta.suffix}
        texto = ruta.stem
    palabras = []
    for palabra in texto.split():
        if palabra in TIPOS_PEDIDOS:
            extensiones = TIPOS_PEDIDOS[palabra]
        elif palabra not in PALABRAS_SOBRANTES:
            palabras.append(palabra)
    reciente = bool({"ultimo", "reciente", "nuevo"} & set(palabras))
    nombre = " ".join(palabra for palabra in palabras if palabra not in {"ultimo", "mas", "reciente", "nuevo"})
    return nombre, extensiones, reciente


def _buscar_archivo(origen: str) -> Path | str:
    """La ruta del archivo pedido o, si no hay uno claro, el texto para decir al usuario."""
    directa = Path(origen.strip().strip('"')).expanduser()
    if directa.is_absolute() and directa.is_file():
        return directa
    nombre, extensiones, reciente = _pedido(origen)
    if reciente and not nombre:
        return _mas_reciente(extensiones) or "No encontré documentos en Descargas."
    if not nombre:
        return "Dime el nombre del documento o la página que quieres que lea."
    encontrados = [
        ruta for ruta in buscar_rutas(nombre)
        if ruta.suffix.lower() in extensiones and not ruta.name.startswith("~$")
    ]
    if not encontrados:
        return f"No encontré ningún documento con {nombre}."
    exactos = [ruta for ruta in encontrados if normalizar(ruta.stem) == nombre]
    recientes = sorted(exactos or encontrados, key=lambda ruta: ruta.stat().st_mtime, reverse=True)
    if len(recientes) == 1 or reciente:
        return recientes[0]
    nombres = ", ".join(ruta.name for ruta in recientes[:MAXIMO_LISTADO])
    return f"Encontré {len(recientes)} documentos. Los más recientes: {nombres}. ¿Cuál leo?"


def leer_documento(origen: str, pagina_inicial: int = 1) -> str:
    origen = (origen or "").strip()
    pagina_inicial = max(1, int(pagina_inicial or 1))
    if not origen:
        return "Dime qué documento o página quieres que lea."
    if _es_url(origen):
        url = origen if "://" in origen else "https://" + origen
        return _leer_web(url, pagina_inicial)
    ruta = _buscar_archivo(origen)
    if isinstance(ruta, str):
        return ruta
    return _leer_archivo(ruta, pagina_inicial)
