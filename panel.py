import json
import logging
import queue
import subprocess
import threading
import time
from pathlib import Path

from collections.abc import Callable

from flask import Blueprint, Response, abort, request, send_from_directory

import config

registro = logging.getLogger(__name__)

CARPETA = Path(__file__).parent / "hud"
URL = "http://127.0.0.1:5000/hud"
TITULO = "Jarvis HUD"
TAMANO = "420,680"
LATIDO = 15
# Edge tarda unos segundos en abrir y conectarse: sin esta espera, dos peticiones seguidas abrirían dos ventanas.
ESPERA_APERTURA = 10
ESPERA_OCULTAR = 8
ORIGENES = ("http://127.0.0.1:5000", "http://localhost:5000")
MAX_TEXTO = 500
FALLO_ESCRITO = "No pude responder a lo que escribiste; mira la consola de Jarvis."

rutas = Blueprint("hud", __name__)
_clientes: list[queue.Queue] = []
_candado = threading.Lock()
_ultima_apertura = float("-inf")
_ocultador: threading.Timer | None = None
_responder: Callable[[str], str] | None = None


def al_escribir(responder: Callable[[str], str]) -> None:
    """Fija quién contesta lo que se escribe en el HUD (el mismo cerebro que atiende a Alexa)."""
    global _responder
    _responder = responder


def _ordenes() -> dict[str, Callable[[], object]]:
    # Importadas aquí: vigilancia usa este módulo y se crearía un import circular.
    from acciones import pc, sistema, vigilancia

    return {
        "pausa": pc.pausar_reanudar,
        "cancelar_apagado": sistema.cancelar_apagado,
        "dejar_de_vigilar": vigilancia.dejar_de_vigilar,
        "ocultar": ocultar,
    }


def emitir(tipo: str, texto: str = "") -> None:
    evento = json.dumps({"tipo": tipo, "texto": texto}, ensure_ascii=False)
    with _candado:
        for cola in _clientes:
            try:
                cola.put_nowait(evento)
            except queue.Full:
                pass


def _escuchar():
    cola = queue.Queue(maxsize=100)
    with _candado:
        _clientes.append(cola)
    try:
        yield ": conectado\n\n"
        while True:
            try:
                yield f"data: {cola.get(timeout=LATIDO)}\n\n"
            except queue.Empty:
                # El latido hace que el servidor note pronto una ventana cerrada.
                yield ": latido\n\n"
    finally:
        with _candado:
            _clientes.remove(cola)


def abrir_ventana() -> None:
    # "start" encuentra msedge aunque no esté en el PATH (Windows lo registra en App Paths).
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", "msedge", f"--app={URL}", f"--window-size={TAMANO}"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        pass


def _buscar_ventana(intentos: int):
    try:
        import pygetwindow
    except (ImportError, NotImplementedError):
        return None
    for intento in range(intentos):
        ventanas = pygetwindow.getWindowsWithTitle(TITULO)
        if ventanas:
            return ventanas[0]
        if intento < intentos - 1:
            time.sleep(0.5)
    return None


def _poner_encima(ventana, encima: bool) -> None:
    import ctypes

    # SetWindowPos con HWND_TOPMOST (-1) o HWND_NOTOPMOST (-2), sin mover ni redimensionar (SWP_NOMOVE | SWP_NOSIZE).
    # A diferencia de "activar", Windows no lo bloquea cuando la orden llega desde un programa en segundo plano.
    ctypes.windll.user32.SetWindowPos(ventana._hWnd, -1 if encima else -2, 0, 0, 0, 0, 0x0003)


def _traer_al_frente() -> None:
    global _ultima_apertura
    with _candado:
        abrir = not _clientes and time.monotonic() - _ultima_apertura > ESPERA_APERTURA
        if abrir:
            _ultima_apertura = time.monotonic()
    if abrir:
        abrir_ventana()
    # La ventana es un extra: un fallo de Windows al moverla no debe afectar a Alexa.
    try:
        ventana = _buscar_ventana(intentos=10 if abrir else 1)
        if ventana:
            if ventana.isMinimized:
                ventana.restore()
            _poner_encima(ventana, True)
    except Exception:
        pass


def ocultar() -> bool:
    """Minimiza el HUD ya; dice si había una ventana que esconder."""
    if not config.HUD_ACTIVO:
        return False
    try:
        ventana = _buscar_ventana(intentos=1)
        if ventana:
            _poner_encima(ventana, False)
            ventana.minimize()
            return True
    except Exception:
        pass
    return False


def _cancelar_ocultar() -> None:
    global _ocultador
    with _candado:
        if _ocultador:
            _ocultador.cancel()
            _ocultador = None


def mostrar() -> None:
    """Abre el HUD si no hay ninguna ventana conectada y lo deja encima de todo."""
    if not config.HUD_ACTIVO:
        return
    _cancelar_ocultar()
    threading.Thread(target=_traer_al_frente, daemon=True).start()


def ocultar_luego() -> None:
    global _ocultador
    if not config.HUD_ACTIVO:
        return
    _cancelar_ocultar()
    with _candado:
        _ocultador = threading.Timer(ESPERA_OCULTAR, ocultar)
        _ocultador.daemon = True
        _ocultador.start()


@rutas.before_request
def solo_este_pc():
    # ngrok publica todo el servidor en internet y el HUD muestra la conversación: solo se sirve en local.
    if request.headers.get("X-Forwarded-For") or request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        abort(403)


def _datos_del_hud() -> dict:
    # Exigir JSON obliga al navegador a pedir permiso (CORS) antes de enviar: otra web abierta en este PC no puede mandar órdenes.
    if not request.is_json or request.headers.get("Origin", ORIGENES[0]) not in ORIGENES:
        abort(403)
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        abort(400)
    return datos


def _contestar_escrito(texto: str) -> None:
    try:
        respuesta = _responder(texto)
    except Exception:
        registro.exception("Falló la respuesta a un texto del HUD")
        respuesta = FALLO_ESCRITO
    emitir("respuesta", respuesta)


@rutas.post("/hud/orden")
def orden():
    nombre = _datos_del_hud().get("orden")
    accion = _ordenes().get(nombre)
    if accion is None:
        abort(400)
    try:
        resultado = accion()
    except Exception:
        registro.exception("Falló una orden del HUD")
        resultado = "No pude hacerlo."
    if isinstance(resultado, str):
        emitir("aviso", resultado)
    return {"ok": True}


@rutas.post("/hud/escribir")
def escribir():
    texto = str(_datos_del_hud().get("texto", "")).strip()[:MAX_TEXTO]
    if not texto or _responder is None:
        abort(400)
    emitir("usuario", texto)
    # Pensar puede tardar varios segundos: la respuesta llega por /hud/eventos, como la de Alexa.
    threading.Thread(target=_contestar_escrito, args=(texto,), daemon=True).start()
    return {"ok": True}, 202


@rutas.get("/hud")
def pagina():
    return send_from_directory(CARPETA, "index.html")


@rutas.get("/hud/eventos")
def eventos():
    return Response(_escuchar(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@rutas.get("/hud/<path:archivo>")
def recurso(archivo):
    return send_from_directory(CARPETA, archivo)
