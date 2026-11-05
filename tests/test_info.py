from types import SimpleNamespace
from typing import ClassVar

import requests

from acciones import info


def _respuesta(datos=None, contenido=b""):
    return SimpleNamespace(json=lambda: datos, content=contenido, raise_for_status=lambda: None)


def _sin_red(*args, **kwargs):
    raise requests.ConnectionError


class FalsoDDGS:
    resultados: ClassVar[list] = []

    def __init__(self, timeout):
        assert timeout == 4

    def text(self, pregunta, region, max_results):
        if isinstance(self.resultados, Exception):
            raise self.resultados
        return self.resultados


def test_buscar_informacion_con_duckduckgo(monkeypatch):
    FalsoDDGS.resultados = [
        {"title": "Torre Eiffel", "body": "Mide 330 metros."},
        {"title": "Vacío", "body": ""},
        {"title": "París", "body": "Capital  de\nFrancia."},
    ]
    monkeypatch.setattr(info, "DDGS", FalsoDDGS)
    resultado = info.buscar_informacion("altura torre eiffel")
    assert resultado == "Torre Eiffel: Mide 330 metros. | París: Capital de Francia."


def test_buscar_informacion_recorta_textos_largos(monkeypatch):
    FalsoDDGS.resultados = [{"title": "T", "body": "palabra " * 100}]
    monkeypatch.setattr(info, "DDGS", FalsoDDGS)
    resultado = info.buscar_informacion("x")
    assert len(resultado) < 220 and resultado.endswith("...")


def test_buscar_informacion_usa_wikipedia_si_falla_duckduckgo(monkeypatch):
    FalsoDDGS.resultados = info.DDGSException("bloqueado")
    monkeypatch.setattr(info, "DDGS", FalsoDDGS)
    paginas = {"query": {"pages": {"1": {"title": "Simón Bolívar", "extract": "Militar venezolano."}}}}
    monkeypatch.setattr(info.requests, "get", lambda url, params, headers, timeout: _respuesta(paginas))
    assert info.buscar_informacion("quién fue bolívar") == "Simón Bolívar: Militar venezolano."


def test_buscar_informacion_sin_resultados(monkeypatch):
    FalsoDDGS.resultados = []
    monkeypatch.setattr(info, "DDGS", FalsoDDGS)
    monkeypatch.setattr(info.requests, "get", _sin_red)
    assert info.buscar_informacion("xyz") == "No encontré información sobre eso."


RSS = """<rss><channel><title>Google News</title>
<item><title>Sube el dólar - El Universal</title></item>
<item><title>Gana el Cruz Azul - ESPN</title></item>
</channel></rss>""".encode()


def test_noticias_portada(monkeypatch):
    pedidas = []

    def falso_get(url, params, timeout):
        pedidas.append((url, params))
        return _respuesta(contenido=RSS)

    monkeypatch.setattr(info, "PAIS_NOTICIAS", "MX")
    monkeypatch.setattr(info.requests, "get", falso_get)
    assert info.noticias() == "Titulares: Sube el dólar. Gana el Cruz Azul."
    assert pedidas == [("https://news.google.com/rss", {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"})]


def test_noticias_con_tema_en_espana(monkeypatch):
    pedidas = []

    def falso_get(url, params, timeout):
        pedidas.append((url, params))
        return _respuesta(contenido=RSS)

    monkeypatch.setattr(info, "PAIS_NOTICIAS", "ES")
    monkeypatch.setattr(info.requests, "get", falso_get)
    info.noticias("fútbol")
    assert pedidas == [
        ("https://news.google.com/rss/search", {"hl": "es", "gl": "ES", "ceid": "ES:es", "q": "fútbol"})
    ]


def test_noticias_sin_resultados(monkeypatch):
    vacio = b"<rss><channel></channel></rss>"
    monkeypatch.setattr(info.requests, "get", lambda url, params, timeout: _respuesta(contenido=vacio))
    assert info.noticias("zzz") == "No encontré noticias sobre zzz."


def test_noticias_sin_red_o_xml_roto(monkeypatch):
    monkeypatch.setattr(info.requests, "get", _sin_red)
    assert info.noticias() == "No pude consultar las noticias ahora."
    monkeypatch.setattr(info.requests, "get", lambda url, params, timeout: _respuesta(contenido=b"<html"))
    assert info.noticias() == "No pude consultar las noticias ahora."


TASAS = {"result": "success", "rates": {"USD": 1, "MXN": 18.5}}


def test_convertir_moneda(monkeypatch):
    pedidas = []
    monkeypatch.setattr(info.requests, "get", lambda url, timeout: pedidas.append(url) or _respuesta(TASAS))
    assert info.convertir_moneda(100, "usd", "mxn") == "100 USD son 1850.00 MXN."
    assert pedidas == ["https://open.er-api.com/v6/latest/USD"]


def test_convertir_moneda_desconocida(monkeypatch):
    monkeypatch.setattr(info.requests, "get", lambda url, timeout: _respuesta(TASAS))
    assert info.convertir_moneda(1, "USD", "XXX") == "No conozco la moneda XXX."
    error = {"result": "error", "error-type": "unsupported-code"}
    monkeypatch.setattr(info.requests, "get", lambda url, timeout: _respuesta(error))
    assert info.convertir_moneda(1, "ABC", "USD") == "No conozco la moneda ABC."


def test_convertir_moneda_sin_red(monkeypatch):
    monkeypatch.setattr(info.requests, "get", _sin_red)
    assert info.convertir_moneda(1, "USD", "EUR") == "No pude consultar el cambio de moneda ahora."
