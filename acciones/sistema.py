import ctypes
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil

import panel

NOMBRES_TECLAS = {
    "control": "ctrl",
    "windows": "win",
    "mayus": "shift",
    "mayús": "shift",
    "intro": "enter",
    "escape": "esc",
    "suprimir": "delete",
    "espacio": "space",
    "tabulador": "tab",
    "retroceso": "backspace",
    "borrar": "backspace",
    "inicio": "home",
    "fin": "end",
    "arriba": "up",
    "abajo": "down",
    "izquierda": "left",
    "derecha": "right",
}
# Lo que tarda Windows en animar el minimizado del HUD y devolver el foco a la ventana anterior.
ESPERA_HUD = 0.4

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
TECLAS_DE_CONTROL = {"\n": 0x0D, "\t": 0x09}
# Un texto largo de golpe puede desbordar la cola de mensajes de la ventana (10.000) y perder letras.
CARACTERES_POR_ENVIO = 500


class _Teclado(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_uint16),
        ("wScan", ctypes.c_uint16),
        ("dwFlags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _Raton(ctypes.Structure):
    # Solo hace falta para que INPUT mida lo que espera SendInput: la unión mide lo que su miembro mayor.
    _fields_ = [
        ("dx", ctypes.c_int32),
        ("dy", ctypes.c_int32),
        ("mouseData", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _Evento(ctypes.Union):
    _fields_ = [("ki", _Teclado), ("mi", _Raton)]


class _Entrada(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("evento", _Evento)]


def _ejecutar(comando: list[str]) -> bool:
    try:
        return subprocess.run(comando, capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def _minutos(minutos: int) -> int:
    return max(1, int(minutos))


def apagar(minutos: int = 1) -> str:
    minutos = _minutos(minutos)
    if not _ejecutar(["shutdown", "/s", "/t", str(minutos * 60)]):
        return "No pude programar el apagado."
    return f"Apagaré el PC en {minutos} minuto{'s' if minutos > 1 else ''}. Si cambias de idea, di cancela el apagado."


def reiniciar(minutos: int = 1) -> str:
    minutos = _minutos(minutos)
    if not _ejecutar(["shutdown", "/r", "/t", str(minutos * 60)]):
        return "No pude programar el reinicio."
    return f"Reiniciaré el PC en {minutos} minuto{'s' if minutos > 1 else ''}. Si cambias de idea, di cancela el apagado."


def cancelar_apagado() -> str:
    if not _ejecutar(["shutdown", "/a"]):
        return "No había ningún apagado programado."
    return "Cancelé el apagado."


def suspender() -> str:
    # Se espera unos segundos para que la respuesta llegue a Alexa antes de cortar la red.
    # Si la hibernación está activa, SetSuspendState hiberna en vez de suspender.
    comando = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
    threading.Timer(3, _ejecutar, args=[comando]).start()
    return "Suspendo el PC."


def bloquear() -> str:
    if not _ejecutar(["rundll32.exe", "user32.dll,LockWorkStation"]):
        return "No pude bloquear el PC."
    return "PC bloqueado."


def _carpeta_capturas() -> Path:
    # archivos.py importa este módulo: importarlo arriba sería circular.
    from acciones.archivos import ruta_carpeta

    return (ruta_carpeta("imagenes") or Path.home() / "Pictures") / "Jarvis"


def captura_pantalla() -> str:
    try:
        from PIL import ImageGrab

        carpeta = _carpeta_capturas()
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"captura_{datetime.now():%Y%m%d_%H%M%S}.png"
        ImageGrab.grab().save(ruta)
    except (ImportError, OSError):
        return "No pude hacer la captura."
    return "Guardé la captura en Imágenes, carpeta Jarvis."


def pyautogui_sin_failsafe():
    import pyautogui

    # Su "failsafe" rechaza toda pulsación y todo movimiento si el ratón quedó en una esquina de la pantalla:
    # con Jarvis nadie mueve el ratón para pararlo, solo haría fallar las órdenes al azar.
    pyautogui.FAILSAFE = False
    return pyautogui


def soltar_foco_del_hud() -> None:
    # Al restaurarse, el HUD puede quedarse con el foco: lo escrito, las teclas o "esta ventana" serían suyos.
    try:
        import pygetwindow

        activa = pygetwindow.getActiveWindow()
    except (ImportError, NotImplementedError):
        return
    if activa is not None and panel.TITULO in activa.title and panel.ocultar():
        time.sleep(ESPERA_HUD)


def _pulsaciones(texto: str) -> list[tuple[int, int, int]]:
    """(tecla virtual, carácter UTF-16, flags) de cada pulsación y suelta."""
    pulsaciones = []
    for caracter in texto.replace("\r\n", "\n"):
        if caracter in TECLAS_DE_CONTROL:
            tecla = TECLAS_DE_CONTROL[caracter]
            pulsaciones += [(tecla, 0, 0), (tecla, 0, KEYEVENTF_KEYUP)]
            continue
        # Un emoji ocupa dos unidades UTF-16 y cada una va en su propia pulsación.
        codificado = caracter.encode("utf-16-le")
        for inicio in range(0, len(codificado), 2):
            unidad = int.from_bytes(codificado[inicio : inicio + 2], "little")
            pulsaciones += [(0, unidad, KEYEVENTF_UNICODE), (0, unidad, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)]
    return pulsaciones


def escribir_texto(texto: str) -> str:
    # KEYEVENTF_UNICODE escribe cada carácter tal cual: no depende de la distribución del teclado (pyautogui
    # teclea la @ o el # del teclado de EE. UU. y en uno español sale otra cosa) ni pisa el portapapeles.
    try:
        enviar = ctypes.windll.user32.SendInput
    except AttributeError:
        return "Solo puedo escribir en Windows."
    soltar_foco_del_hud()
    for inicio in range(0, len(texto), CARACTERES_POR_ENVIO):
        pulsaciones = _pulsaciones(texto[inicio : inicio + CARACTERES_POR_ENVIO])
        entradas = (_Entrada * len(pulsaciones))(
            *(_Entrada(INPUT_KEYBOARD, _Evento(ki=_Teclado(tecla, unidad, flags, 0, 0))) for tecla, unidad, flags in pulsaciones)
        )
        if enviar(len(entradas), entradas, ctypes.sizeof(_Entrada)) != len(entradas):
            # Pasa con la pantalla bloqueada o un aviso de permisos de administrador delante.
            return "No pude escribir: Windows tiene el teclado bloqueado ahora."
    return "Escrito."


def atajo_teclado(teclas: str) -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return "Solo puedo usar el teclado en Windows."
    nombres = [tecla.strip().removeprefix("flecha ") for tecla in teclas.lower().split("+")]
    combinacion = [NOMBRES_TECLAS.get(nombre, nombre) for nombre in nombres]
    for tecla in combinacion:
        if tecla not in pyautogui.KEYBOARD_KEYS:
            return f"No conozco la tecla {tecla}."
    soltar_foco_del_hud()
    pyautogui.hotkey(*combinacion)
    return "Hecho."


def estado_pc() -> str:
    cpu = round(psutil.cpu_percent(interval=0.3))
    memoria = round(psutil.virtual_memory().percent)
    estado = f"Procesador al {cpu} por ciento y memoria al {memoria} por ciento."
    bateria = psutil.sensors_battery()
    if bateria is not None:
        cargando = ", cargando" if bateria.power_plugged else ""
        estado += f" Batería al {round(bateria.percent)} por ciento{cargando}."
    return estado
