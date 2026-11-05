import os
import webbrowser
from urllib.parse import quote, quote_plus

import requests

from config import CIUDAD


def buscar_en_google(busqueda: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(busqueda)}")
    return f"Busqué {busqueda} en Google."


def _consultar_clima(ciudad: str) -> tuple[str, dict]:
    ciudad = ciudad.strip() or CIUDAD
    respuesta = requests.get(f"https://wttr.in/{quote(ciudad)}", params={"format": "j1", "lang": "es"}, timeout=3)
    respuesta.raise_for_status()
    datos = respuesta.json()
    lugar = ciudad or datos["nearest_area"][0]["areaName"][0]["value"]
    return lugar, datos


def clima(ciudad: str = "") -> str:
    try:
        lugar, datos = _consultar_clima(ciudad)
        actual = datos["current_condition"][0]
        estado = actual.get("lang_es", actual["weatherDesc"])[0]["value"]
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return "No pude consultar el clima ahora."
    return f"En {lugar} hace {actual['temp_C']} grados, {estado.lower()}."


def pronostico_hoy(ciudad: str = "") -> str:
    """Temperatura actual, máxima y lluvia de hoy. Sin red o con datos raros lanza la excepción."""
    lugar, datos = _consultar_clima(ciudad)
    hoy = datos["weather"][0]
    lluvia = max((int(hora["chanceofrain"]) for hora in hoy.get("hourly", [])), default=0)
    return (
        f"En {lugar} {datos['current_condition'][0]['temp_C']} grados, "
        f"máxima {hoy['maxtempC']}, mínima {hoy['mintempC']} y {lluvia} % de lluvia."
    )


def abrir_en_spotify(busqueda: str) -> str:
    try:
        os.startfile(f"spotify:search:{quote(busqueda)}")
    except (AttributeError, OSError):
        # Sin la app de escritorio (o fuera de Windows) queda el reproductor web.
        webbrowser.open(f"https://open.spotify.com/search/{quote(busqueda)}")
    return f"Busqué {busqueda} en Spotify."
