import json
from types import SimpleNamespace

import pytest
import requests

from acciones import echo


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("ECHO_USO_ARCHIVO", str(tmp_path / "echo_uso.json"))
    monkeypatch.setattr(echo.config, "VOICEMONKEY_TOKEN", "token")
    monkeypatch.setattr(echo.config, "VOICEMONKEY_DISPOSITIVO", "echo-salon")
    monkeypatch.setattr(echo.config, "LIMITE_ECHO_MES", 10)
    return tmp_path / "echo_uso.json"


@pytest.fixture
def enviados(monkeypatch):
    peticiones = []

    def post(url, json, timeout):
        peticiones.append((url, json))
        return SimpleNamespace(ok=True, status_code=200, text='{"success": true}')

    monkeypatch.setattr(echo.requests, "post", post)
    return peticiones


def mes_actual():
    return echo.date.today().strftime("%Y-%m")


def test_envia_el_anuncio_a_voice_monkey(enviados, entorno):
    assert echo.decir_en_echo("Recordatorio: dentista & café") == "Lo dije en el Echo."
    url, datos = enviados[0]
    assert url == "https://api-v3.voicemonkey.io/announce"
    assert datos == {"token": "token", "device": "echo-salon", "speech": "Recordatorio: dentista &amp; café"}
    assert json.loads(entorno.read_text()) == {"mes": mes_actual(), "envios": 1}


def test_sin_token_no_hace_nada(enviados, monkeypatch):
    monkeypatch.setattr(echo.config, "VOICEMONKEY_TOKEN", "")
    assert "falta configurar Voice Monkey" in echo.decir_en_echo("hola")
    assert enviados == []


def test_cerca_del_limite_avisa_cuantos_quedan(enviados, entorno):
    entorno.write_text(json.dumps({"mes": mes_actual(), "envios": 7}))
    assert echo.decir_en_echo("Se acabó el tiempo.") == "Lo dije en el Echo. Quedan 2 avisos este mes."
    assert enviados[0][1]["speech"].endswith("me quedan 2 avisos en el Echo este mes.")


def test_no_pasa_del_limite_mensual(enviados, entorno):
    entorno.write_text(json.dumps({"mes": mes_actual(), "envios": 10}))
    assert echo.decir_en_echo("hola").startswith("Ya usé los 10 avisos")
    assert enviados == []


def test_el_contador_se_reinicia_cada_mes(enviados, entorno):
    entorno.write_text(json.dumps({"mes": "2020-01", "envios": 10}))
    assert echo.decir_en_echo("hola") == "Lo dije en el Echo."
    assert json.loads(entorno.read_text())["envios"] == 1


def test_un_rechazo_no_gasta_cuota(monkeypatch, entorno):
    monkeypatch.setattr(
        echo.requests, "post",
        lambda *_, **__: SimpleNamespace(ok=False, status_code=429, text="MONTHLY_QUOTA_EXCEEDED"),
    )
    assert echo.decir_en_echo("hola") == "Voice Monkey rechazó el aviso (429: MONTHLY_QUOTA_EXCEEDED)."
    assert not entorno.exists()


def test_sin_conexion_no_falla(monkeypatch, entorno):
    def sin_red(*_, **__):
        raise requests.ConnectionError

    monkeypatch.setattr(echo.requests, "post", sin_red)
    assert echo.decir_en_echo("hola") == "No pude hablar por el Echo: Voice Monkey no responde."
    assert not entorno.exists()


@pytest.mark.parametrize("contenido", ["{roto", "[]", '{"mes": "x"}'])
def test_cuenta_ilegible_no_impide_avisar(enviados, entorno, contenido):
    entorno.write_text(contenido, encoding="utf-8")
    assert echo.decir_en_echo("hola") == "Lo dije en el Echo."
    assert json.loads(entorno.read_text(encoding="utf-8")) == {"mes": mes_actual(), "envios": 1}
