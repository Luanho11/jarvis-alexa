from types import SimpleNamespace

import pytest
import requests

from acciones import web


@pytest.fixture
def navegador(monkeypatch):
    abiertas = []
    monkeypatch.setattr(web.webbrowser, "open", abiertas.append)
    return abiertas


def _respuesta(datos):
    return SimpleNamespace(json=lambda: datos, raise_for_status=lambda: None)


DATOS_CLIMA = {
    "current_condition": [
        {"temp_C": "18", "weatherDesc": [{"value": "Cloudy"}], "lang_es": [{"value": "Nublado"}]}
    ],
    "nearest_area": [{"areaName": [{"value": "Lima"}]}],
}


def test_buscar_en_google(navegador):
    assert web.buscar_en_google("receta de pan") == "Busqué receta de pan en Google."
    assert navegador == ["https://www.google.com/search?q=receta+de+pan"]


def test_clima_con_ciudad(monkeypatch):
    pedidas = []

    def falso_get(url, params, timeout):
        pedidas.append((url, timeout))
        return _respuesta(DATOS_CLIMA)

    monkeypatch.setattr(web.requests, "get", falso_get)
    assert web.clima("Buenos Aires") == "En Buenos Aires hace 18 grados, nublado."
    assert pedidas == [("https://wttr.in/Buenos%20Aires", 3)]


def test_clima_sin_ciudad_usa_la_detectada(monkeypatch):
    monkeypatch.setattr(web, "CIUDAD", "")
    monkeypatch.setattr(web.requests, "get", lambda url, params, timeout: _respuesta(DATOS_CLIMA))
    assert web.clima() == "En Lima hace 18 grados, nublado."


def test_clima_sin_red(monkeypatch):
    def sin_red(url, params, timeout):
        raise requests.Timeout

    monkeypatch.setattr(web.requests, "get", sin_red)
    assert web.clima("Lima") == "No pude consultar el clima ahora."


def test_clima_respuesta_rara(monkeypatch):
    monkeypatch.setattr(web.requests, "get", lambda url, params, timeout: _respuesta({}))
    assert web.clima("Lima") == "No pude consultar el clima ahora."


def test_spotify_abre_la_app(monkeypatch, navegador):
    abiertos = []
    monkeypatch.setattr(web.os, "startfile", abiertos.append, raising=False)
    assert web.abrir_en_spotify("bad bunny") == "Busqué bad bunny en Spotify."
    assert abiertos == ["spotify:search:bad%20bunny"]
    assert navegador == []


def test_spotify_sin_app_usa_la_web(monkeypatch, navegador):
    def sin_app(_):
        raise OSError

    monkeypatch.setattr(web.os, "startfile", sin_app, raising=False)
    web.abrir_en_spotify("bad bunny")
    assert navegador == ["https://open.spotify.com/search/bad%20bunny"]
