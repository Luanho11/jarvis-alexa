import re
import webbrowser
from urllib.parse import quote_plus

import requests

from acciones.sistema import teclado

YOUTUBE = "https://www.youtube.com"


def _pulsar(tecla: str, veces: int = 1) -> None:
    teclado().press(tecla, presses=veces)


def subir_volumen(pasos: int = 5) -> str:
    _pulsar("volumeup", pasos)
    return "Subí el volumen."


def bajar_volumen(pasos: int = 5) -> str:
    _pulsar("volumedown", pasos)
    return "Bajé el volumen."


def _control_volumen():
    import comtypes
    from pycaw.pycaw import AudioUtilities

    # comtypes solo inicia COM en el hilo que lo importa y cada petición llega en otro hilo.
    comtypes.CoInitialize()
    altavoces = AudioUtilities.GetSpeakers()
    # pycaw reciente expone EndpointVolume; las versiones antiguas exigen activar la interfaz COM.
    if hasattr(altavoces, "EndpointVolume"):
        return altavoces.EndpointVolume

    from ctypes import POINTER, cast

    from pycaw.pycaw import IAudioEndpointVolume

    interfaz = altavoces.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
    return cast(interfaz, POINTER(IAudioEndpointVolume))


def fijar_volumen(porcentaje: int) -> str:
    porcentaje = max(0, min(100, int(porcentaje)))
    try:
        volumen = _control_volumen()
    except ImportError:
        return "Solo puedo fijar el volumen exacto en Windows."
    volumen.SetMasterVolumeLevelScalar(porcentaje / 100, None)
    return f"Volumen al {porcentaje} por ciento."


def silenciar() -> str:
    _pulsar("volumemute")
    return "Listo, silencio."


def pausar_reanudar() -> str:
    _pulsar("playpause")
    return "Hecho."


def siguiente() -> str:
    _pulsar("nexttrack")
    return "Siguiente."


def anterior() -> str:
    _pulsar("prevtrack")
    return "Anterior."


# Atajos de YouTube: actúan sobre el video de la ventana con foco.
def pantalla_completa() -> str:
    _pulsar("f")
    return "Pantalla completa."


def _saltos(segundos: int) -> int:
    return max(1, round(int(segundos) / 10))


def adelantar(segundos: int = 10) -> str:
    _pulsar("l", _saltos(segundos))
    return "Adelanté."


def retroceder(segundos: int = 10) -> str:
    _pulsar("j", _saltos(segundos))
    return "Retrocedí."


def siguiente_video() -> str:
    teclado().hotkey("shift", "n")
    return "Siguiente video."


def _url_resultados(busqueda: str) -> str:
    return f"{YOUTUBE}/results?search_query={quote_plus(busqueda)}"


def abrir_youtube(busqueda: str = "") -> str:
    if not busqueda:
        webbrowser.open(YOUTUBE)
        return "Abrí YouTube."
    webbrowser.open(_url_resultados(busqueda))
    return f"Busqué {busqueda} en YouTube."


def _primer_video(busqueda: str) -> str | None:
    respuesta = requests.get(_url_resultados(busqueda), timeout=3)
    respuesta.raise_for_status()
    encontrado = re.search(r'"videoId":"([\w-]{11})"', respuesta.text)
    return encontrado.group(1) if encontrado else None


def reproducir_en_youtube(busqueda: str) -> str:
    try:
        video = _primer_video(busqueda)
    except requests.RequestException:
        video = None
    if video is None:
        webbrowser.open(_url_resultados(busqueda))
        return f"No pude reproducirlo directo, te dejé los resultados de {busqueda}."
    webbrowser.open(f"{YOUTUBE}/watch?v={video}")
    return f"Reproduciendo {busqueda} en YouTube."


def abrir_web(url: str) -> str:
    url = url.strip()
    if not re.match(r"https?://", url):
        url = f"https://{url}"
    webbrowser.open(url)
    return "Abrí la página."

