import logging
import re
import threading
import time
from collections import deque

import config
import panel
from acciones import recordatorios, vision

# El plan gratis de gemini-3.5-flash-lite admite 10 peticiones por minuto y 500 al día, compartidas con el
# respaldo del cerebro y "describir pantalla": cada 15 s como mucho, y no más de media hora seguida.
INTERVALO_MINIMO = 15
MAX_MINUTOS = 30
OBJETIVO = "comentar qué está pasando en la pantalla o algo útil que convenga saber"
MAX_OBJETIVO = 300
SILENCIO = "NADA"
# Lo último que dijo va en cada pregunta para que no repita el mismo consejo cada 20 segundos.
RECIENTES = 3

registro = logging.getLogger(__name__)
_parada = threading.Event()
_parada.set()


def _instruccion(objetivo: str, recientes: deque) -> str:
    instruccion = (
        f"Esta es la pantalla de mi PC y me acompañas mientras la uso. Tu tarea: {objetivo}. "
        "Responde en español, en una o dos frases cortas y sin formato. "
        f"Si no hay nada nuevo o útil que decir, responde solo {SILENCIO}."
    )
    if recientes:
        instruccion += " Ya dijiste esto, no lo repitas: " + " | ".join(recientes)
    return instruccion


def _callar(comentario: str, recientes: deque) -> bool:
    limpio = re.sub(r"\W", "", comentario).upper()
    return not limpio or limpio == SILENCIO or comentario in recientes


def _decir(comentario: str, en_voz: bool) -> None:
    if en_voz:
        # Nunca en el Echo: con un comentario cada 20 s se agotaría la cuota mensual de Voice Monkey en minutos.
        recordatorios.avisar(comentario, en_echo=False)
    else:
        panel.emitir("comentario", comentario)


def _comentar(parada: threading.Event, fin: float, intervalo: int, en_voz: bool, objetivo: str) -> None:
    recientes = deque(maxlen=RECIENTES)
    error_anterior = ""
    while time.monotonic() < fin:
        try:
            comentario = vision.mirar_pantalla(_instruccion(objetivo, recientes)).strip()
            error_anterior = ""
        except vision.SinVision as error:
            # Un fallo de cuota dura minutos: se avisa una vez y se sigue intentando sin repetirlo.
            comentario = "" if str(error) == error_anterior else str(error)
            error_anterior = str(error)
        else:
            if _callar(comentario, recientes):
                comentario = ""
            else:
                recientes.append(comentario)
        if parada.is_set():
            return
        if comentario:
            _decir(comentario, en_voz)
        if parada.wait(intervalo):
            return
    parada.set()
    panel.emitir("aviso", "Terminé de vigilar la pantalla.")
    panel.ocultar_luego()


def _vigilar(parada: threading.Event, fin: float, intervalo: int, en_voz: bool, objetivo: str) -> None:
    try:
        _comentar(parada, fin, intervalo, en_voz, objetivo)
    except Exception:
        # Sin esto, "vigilando" seguiría activo para siempre y el HUD no volvería a esconderse.
        registro.exception("Falló la vigilancia de la pantalla")
        parada.set()


def vigilando() -> bool:
    return not _parada.is_set()


def vigilar_pantalla(minutos: int = 5, intervalo: int = 20, en_voz: bool = False, objetivo: str = "") -> str:
    global _parada
    minutos = int(minutos)
    if minutos <= 0:
        return "Dime cuántos minutos vigilo la pantalla."
    if not config.GEMINI_API_KEY:
        return "Para vigilar la pantalla necesito la clave de Gemini."
    minutos = min(minutos, MAX_MINUTOS)
    intervalo = max(int(intervalo), INTERVALO_MINIMO)
    objetivo = objetivo.strip()[:MAX_OBJETIVO] or OBJETIVO
    _parada.set()
    _parada = threading.Event()
    fin = time.monotonic() + minutos * 60
    threading.Thread(target=_vigilar, args=(_parada, fin, intervalo, en_voz, objetivo), daemon=True).start()
    panel.mostrar()
    donde = "en voz y en el panel" if en_voz else "en el panel de la pantalla"
    unidad = "minuto" if minutos == 1 else "minutos"
    return f"Vigilo la pantalla {minutos} {unidad}: la miro cada {intervalo} segundos y comento {donde} solo si veo algo útil."


def dejar_de_vigilar() -> str:
    if not vigilando():
        return "No estaba vigilando la pantalla."
    _parada.set()
    return "Dejo de vigilar la pantalla."
