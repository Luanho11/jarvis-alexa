import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from acciones import google

URL = "https://script.google.com/macros/s/ABC123/exec"
CLAVE = "clave-secreta-de-prueba-123456"
CARPETA = Path(__file__).resolve().parent.parent / "google"


@pytest.fixture
def configurado(monkeypatch):
    monkeypatch.setenv("GOOGLE_SCRIPT_URL", URL)
    monkeypatch.setenv("GOOGLE_SCRIPT_CLAVE", CLAVE)


class Respuesta:
    def __init__(self, datos=None, estado=200, texto=None):
        self.datos = datos
        self.status_code = estado
        self.texto = texto

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        if self.texto is not None:
            return json.loads(self.texto)
        return self.datos


@pytest.fixture
def google_falso(monkeypatch):
    estado = {"respuesta": Respuesta({}), "pedidos": []}

    def enviar(url, json, timeout):
        estado["pedidos"].append({"url": url, "json": json, "timeout": timeout})
        if isinstance(estado["respuesta"], Exception):
            raise estado["respuesta"]
        return estado["respuesta"]

    monkeypatch.setattr(google.requests, "post", enviar)
    return estado


def _correo(de="Ana López <ana@correo.com>", asunto="Factura", fragmento="Te envío la factura de noviembre"):
    return {"de": de, "asunto": asunto, "fragmento": fragmento, "fecha": "2026-11-05T10:00:00.000Z", "no_leido": True}


def test_sin_configurar_no_llama_a_google(google_falso):
    assert google.leer_correos() == google.SIN_CONFIGURAR
    assert google_falso["pedidos"] == []
    assert not google.configurado() and not google.agenda_activa()


def test_url_que_no_es_de_google_no_recibe_la_clave(google_falso, monkeypatch):
    monkeypatch.setenv("GOOGLE_SCRIPT_URL", "https://malicioso.com/macros/s/x/exec")
    monkeypatch.setenv("GOOGLE_SCRIPT_CLAVE", CLAVE)
    assert google.leer_correos().startswith("GOOGLE_SCRIPT_URL debe empezar por")
    assert google_falso["pedidos"] == []


def test_lee_correos_sin_leer(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"correos": [_correo(), _correo(de="avisos@banco.com", asunto="Saldo", fragmento="")], "no_leidos": 2})
    assert google.leer_correos() == (
        "Tienes 2 sin leer. De Ana López: «Factura», dice: Te envío la factura de noviembre. De avisos@banco.com: «Saldo»."
    )
    pedido = google_falso["pedidos"][0]
    assert pedido["url"] == URL and CLAVE not in pedido["url"]
    assert pedido["json"] == {"clave": CLAVE, "accion": "correos", "cantidad": 5, "solo_no_leidos": True}
    assert pedido["timeout"] == google.TIEMPO_LIMITE


def test_un_solo_correo_y_mas_sin_leer_que_los_mostrados(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"correos": [_correo()], "no_leidos": 1})
    assert google.leer_correos().startswith("Tienes 1 sin leer. De Ana López")
    google_falso["respuesta"] = Respuesta({"correos": [_correo()], "no_leidos": 12})
    assert google.leer_correos(1).startswith("Tienes 12 sin leer; el más reciente. De Ana")
    google_falso["respuesta"] = Respuesta({"correos": [_correo(), _correo()], "no_leidos": 9})
    assert google.leer_correos(2).startswith("Tienes 9 sin leer; los 2 más recientes. De Ana")


def test_todos_los_correos(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"correos": [_correo()], "no_leidos": 0})
    assert google.leer_correos(3, solo_no_leidos=False).startswith("Tu último correo. De Ana López")
    assert google_falso["pedidos"][0]["json"]["solo_no_leidos"] is False


def test_sin_correos(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"correos": [], "no_leidos": 0})
    assert google.leer_correos() == "No tienes correos sin leer."
    assert google.leer_correos(solo_no_leidos=False) == "Tu bandeja de entrada está vacía."


@pytest.mark.parametrize("pedida, enviada", [(50, 10), (0, 5), (-3, 1), (3, 3)])
def test_cantidad_con_limites(configurado, google_falso, pedida, enviada):
    google_falso["respuesta"] = Respuesta({"correos": []})
    google.leer_correos(pedida)
    assert google_falso["pedidos"][0]["json"]["cantidad"] == enviada


def test_fragmento_largo_recortado_y_entidades_html(configurado, google_falso):
    largo = "palabra " * 125
    google_falso["respuesta"] = Respuesta({"correos": [_correo(asunto="Tom &amp; Jerry", fragmento=largo)]})
    texto = google.leer_correos()
    fragmento = texto.split("dice: ", 1)[1]
    assert len(fragmento) <= google.MAX_FRAGMENTO + 4 and fragmento.endswith("....")
    assert "«Tom & Jerry»" in texto


def test_entradas_raras_no_rompen(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"correos": ["basura", {"de": None, "asunto": None}], "no_leidos": "x"})
    assert google.leer_correos() == "Tienes 1 sin leer. De alguien: «sin asunto»."


def test_clave_incorrecta(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"error": "clave"})
    assert "rechazó la clave" in google.leer_correos()


def test_error_de_google_se_registra_sin_secretos(configurado, google_falso, caplog):
    google_falso["respuesta"] = Respuesta({"error": "google", "detalle": "Exception: Gmail no habilitado"})
    with caplog.at_level(logging.WARNING):
        assert google.leer_correos() == "Google dio un error, inténtalo más tarde."
    assert "Gmail no habilitado" in caplog.text
    assert CLAVE not in caplog.text and URL not in caplog.text


def test_tiempo_agotado(configurado, google_falso):
    google_falso["respuesta"] = requests.Timeout()
    assert google.leer_correos() == "Google no respondió."


def test_sin_conexion_o_error_http(configurado, google_falso):
    google_falso["respuesta"] = requests.ConnectionError()
    assert google.leer_correos() == "No pude conectar con Google."
    google_falso["respuesta"] = Respuesta(estado=500)
    assert google.leer_correos() == "No pude conectar con Google."


@pytest.mark.parametrize("texto", ["<html>Inicia sesión</html>", "[1, 2]", "{roto"])
def test_respuesta_que_no_es_json_del_script(configurado, google_falso, texto):
    google_falso["respuesta"] = Respuesta(texto=texto)
    assert "revisa el acceso del Apps Script" in google.leer_correos()


def _local(*fecha):
    return datetime(*fecha, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)


def test_eventos_de_google_en_hora_local(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"eventos": [
        {"titulo": "Dentista", "inicio": "2026-11-05T21:00:00.000Z", "todo_el_dia": False, "dia": "2026-11-05"},
        {"titulo": "Cumpleaños", "inicio": "2026-11-05T06:00:00.000Z", "todo_el_dia": True, "dia": "2026-11-05"},
        {"titulo": "", "inicio": "2026-11-05T06:00:00.000Z"},
        {"titulo": "Sin fecha"},
        {"titulo": "Fecha rota", "inicio": "mañana"},
    ]})
    desde = datetime(2026, 11, 5)
    eventos = google.eventos_google(desde, datetime(2026, 11, 6))
    assert eventos == [
        {"titulo": "Dentista", "fecha_hora": _local(2026, 11, 5, 21, 0).isoformat(timespec="minutes")},
        {"titulo": "Cumpleaños", "fecha_hora": "2026-11-05T00:00", "todo_el_dia": True},
    ]
    enviado = google_falso["pedidos"][0]["json"]
    assert enviado["accion"] == "eventos"
    assert datetime.fromisoformat(enviado["desde"]) == desde.astimezone()
    assert datetime.fromisoformat(enviado["desde"]).tzinfo is not None


def test_eventos_sin_google_o_caido(configurado, google_falso, monkeypatch):
    google_falso["respuesta"] = requests.Timeout()
    assert google.eventos_google(datetime(2026, 11, 5), datetime(2026, 11, 6)) == []
    monkeypatch.delenv("GOOGLE_SCRIPT_URL")
    assert google.eventos_google(datetime(2026, 11, 5), datetime(2026, 11, 6)) == []


def test_crear_evento(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"ok": True, "id": "x"})
    assert google.crear_evento_google("Dentista", datetime(2026, 11, 5, 15, 0)) is True
    enviado = google_falso["pedidos"][0]["json"]
    inicio, fin = datetime.fromisoformat(enviado["inicio"]), datetime.fromisoformat(enviado["fin"])
    assert enviado["titulo"] == "Dentista"
    assert inicio == datetime(2026, 11, 5, 15, 0).astimezone() and fin - inicio == google.DURACION_EVENTO


def test_crear_evento_falla(configurado, google_falso):
    google_falso["respuesta"] = Respuesta({"error": "google"})
    assert google.crear_evento_google("Dentista", datetime(2026, 11, 5, 15, 0)) is False


def test_crear_en_segundo_plano_no_bloquea(monkeypatch):
    soltar = threading.Event()
    hecho = threading.Event()

    def lento(titulo, momento):
        soltar.wait(2)
        hecho.set()

    monkeypatch.setattr(google, "crear_evento_google", lento)
    google.crear_evento_en_segundo_plano("Dentista", datetime(2026, 11, 5, 15, 0))
    assert not hecho.is_set()
    soltar.set()
    assert hecho.wait(2)


def test_google_agenda_no_desactiva_solo_la_agenda(configurado, monkeypatch):
    assert google.agenda_activa()
    monkeypatch.setenv("GOOGLE_AGENDA", "No")
    assert google.configurado() and not google.agenda_activa()


def test_script_comprueba_la_clave_y_no_envia_correos():
    codigo = (CARPETA / "Codigo.gs").read_text(encoding="utf-8")
    assert "function doPost(e)" in codigo
    assert "if (!claveCorrecta(pedido.clave))" in codigo
    assert "getProperty('CLAVE')" in codigo
    for prohibido in ("GmailApp", "sendEmail", "createDraft", "send(", "trash", "UrlFetchApp"):
        assert prohibido not in codigo
    for accion in ("'correos'", "'eventos'", "'crear_evento'"):
        assert accion in codigo


def test_manifiesto_solo_lectura_de_gmail():
    manifiesto = json.loads((CARPETA / "appsscript.json").read_text(encoding="utf-8"))
    assert sorted(manifiesto["oauthScopes"]) == [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    assert manifiesto["webapp"] == {"executeAs": "USER_DEPLOYING", "access": "ANYONE_ANONYMOUS"}
    assert manifiesto["dependencies"]["enabledAdvancedServices"][0]["serviceId"] == "gmail"


def test_contar_no_leidos(configurado, google_falso, monkeypatch):
    google_falso["respuesta"] = Respuesta({"correos": [_correo()], "no_leidos": 7})
    assert google.contar_no_leidos() == 7
    assert google_falso["pedidos"][0]["json"]["cantidad"] == 1
    google_falso["respuesta"] = Respuesta({"correos": [], "no_leidos": "x"})
    assert google.contar_no_leidos() is None
    google_falso["respuesta"] = requests.Timeout()
    assert google.contar_no_leidos() is None
    monkeypatch.delenv("GOOGLE_SCRIPT_URL")
    assert google.contar_no_leidos() is None
