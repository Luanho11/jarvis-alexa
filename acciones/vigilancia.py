import logging
import threading
import time

import config
import panel
from acciones import recordatorios, vision

# El plan gratis de gemini-3.5-flash-lite admite 10 peticiones por minuto y 500 al día, compartidas con el
# respaldo del cerebro y "describir pantalla": cada 15 s como mucho, y no más de media hora seguida.
INTERVALO_MINIMO = 15
MAX_MINUTOS = 30
PREGUNTA = "comenta en una sola frase qué está pasando en la pantalla o algo útil que convenga saber."

registro = logging.getLogger(__name__)
_parada = threading.Event()
_parada.set()


def _comentar(parada: threading.Event, fin: float, intervalo: int, en_voz: bool) -> None:
    while time.monotonic() < fin:
        comentario = vision.describir_pantalla(PREGUNTA)
        if parada.is_set():
            return
        if en_voz:
            # Nunca en el Echo: con un comentario cada 20 s se agotaría la cuota mensual de Voice Monkey en minutos.
            recordatorios.avisar(comentario, en_echo=False)
        else:
            panel.emitir("comentario", comentario)
        if parada.wait(intervalo):
            return
    parada.set()
    panel.emitir("aviso", "Terminé de vigilar la pantalla.")
    panel.ocultar_luego()


def _vigilar(parada: threading.Event, fin: float, intervalo: int, en_voz: bool) -> None:
    try:
        _comentar(parada, fin, intervalo, en_voz)
    except Exception:
        # Sin esto, "vigilando" seguiría activo para siempre y el HUD no volvería a esconderse.
        registro.exception("Falló la vigilancia de la pantalla")
        parada.set()


def vigilando() -> bool:
    return not _parada.is_set()


def vigilar_pantalla(minutos: int = 5, intervalo: int = 20, en_voz: bool = False) -> str:
    global _parada
    minutos = int(minutos)
    if minutos <= 0:
        return "Dime cuántos minutos vigilo la pantalla."
    if not config.GEMINI_API_KEY:
        return "Para vigilar la pantalla necesito la clave de Gemini."
    minutos = min(minutos, MAX_MINUTOS)
    intervalo = max(int(intervalo), INTERVALO_MINIMO)
    _parada.set()
    _parada = threading.Event()
    fin = time.monotonic() + minutos * 60
    threading.Thread(target=_vigilar, args=(_parada, fin, intervalo, en_voz), daemon=True).start()
    panel.mostrar()
    donde = "en voz y en el panel" if en_voz else "en el panel de la pantalla"
    unidad = "minuto" if minutos == 1 else "minutos"
    return f"Vigilo la pantalla {minutos} {unidad} y comento cada {intervalo} segundos {donde}."


def dejar_de_vigilar() -> str:
    if not vigilando():
        return "No estaba vigilando la pantalla."
    _parada.set()
    return "Dejo de vigilar la pantalla."
