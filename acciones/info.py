import xml.etree.ElementTree as ET

import requests
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from config import PAIS_NOTICIAS

TIEMPO_LIMITE = 4
# Wikipedia rechaza peticiones sin User-Agent identificable.
CABECERAS_WIKIPEDIA = {"User-Agent": "Jarvis/1.0 (asistente personal)"}


def _recortar(texto: str, largo: int = 200) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= largo else texto[:largo].rsplit(" ", 1)[0] + "..."


def _buscar_en_duckduckgo(pregunta: str) -> list[str]:
    resultados = DDGS(timeout=TIEMPO_LIMITE).text(pregunta, region="es-es", max_results=4)
    return [f"{r['title']}: {_recortar(r['body'])}" for r in resultados if r.get("body")]


def _buscar_en_wikipedia(pregunta: str) -> list[str]:
    respuesta = requests.get(
        "https://es.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": pregunta,
            "gsrlimit": 1,
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "exsentences": 3,
        },
        headers=CABECERAS_WIKIPEDIA,
        timeout=TIEMPO_LIMITE,
    )
    respuesta.raise_for_status()
    paginas = respuesta.json().get("query", {}).get("pages", {}).values()
    return [f"{p['title']}: {_recortar(p['extract'], 400)}" for p in paginas if p.get("extract")]


def buscar_informacion(pregunta: str) -> str:
    try:
        resultados = _buscar_en_duckduckgo(pregunta)
    except DDGSException:
        resultados = []
    if not resultados:
        try:
            resultados = _buscar_en_wikipedia(pregunta)
        except (requests.RequestException, ValueError):
            pass
    if not resultados:
        return "No encontré información sobre eso."
    return " | ".join(resultados)


def noticias(tema: str = "") -> str:
    idioma = "es" if PAIS_NOTICIAS == "ES" else "es-419"
    url = "https://news.google.com/rss/search" if tema else "https://news.google.com/rss"
    parametros = {"hl": idioma, "gl": PAIS_NOTICIAS, "ceid": f"{PAIS_NOTICIAS}:{idioma}"}
    if tema:
        parametros["q"] = tema
    try:
        respuesta = requests.get(url, params=parametros, timeout=TIEMPO_LIMITE)
        respuesta.raise_for_status()
        titulos = [item.findtext("title", "") for item in ET.fromstring(respuesta.content).iter("item")]
    except (requests.RequestException, ET.ParseError):
        return "No pude consultar las noticias ahora."
    # Google News termina cada titular con " - Medio"; para voz sobra.
    titulares = [titulo.rsplit(" - ", 1)[0] for titulo in titulos if titulo][:4]
    if not titulares:
        return f"No encontré noticias sobre {tema}." if tema else "No encontré noticias."
    return "Titulares: " + ". ".join(titulares) + "."


def convertir_moneda(cantidad: float, de: str, a: str) -> str:
    cantidad = float(cantidad)
    de, a = de.strip().upper(), a.strip().upper()
    try:
        respuesta = requests.get(f"https://open.er-api.com/v6/latest/{de}", timeout=TIEMPO_LIMITE)
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "No pude consultar el cambio de moneda ahora."
    if datos.get("result") != "success":
        return f"No conozco la moneda {de}."
    tasa = datos.get("rates", {}).get(a)
    if tasa is None:
        return f"No conozco la moneda {a}."
    return f"{cantidad:g} {de} son {cantidad * tasa:.2f} {a}."
