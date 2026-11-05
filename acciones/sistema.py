import subprocess
import threading
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
}


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
    # El HUD enseña la cuenta atrás con un botón para cancelarla.
    panel.emitir("apagado", str(minutos * 60))
    return f"Apagaré el PC en {minutos} minuto{'s' if minutos > 1 else ''}. Si cambias de idea, di cancela el apagado."


def reiniciar(minutos: int = 1) -> str:
    minutos = _minutos(minutos)
    if not _ejecutar(["shutdown", "/r", "/t", str(minutos * 60)]):
        return "No pude programar el reinicio."
    panel.emitir("reinicio", str(minutos * 60))
    return f"Reiniciaré el PC en {minutos} minuto{'s' if minutos > 1 else ''}. Si cambias de idea, di cancela el apagado."


def cancelar_apagado() -> str:
    if not _ejecutar(["shutdown", "/a"]):
        return "No había ningún apagado programado."
    panel.emitir("apagado", "0")
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


def escribir_texto(texto: str) -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return "Solo puedo escribir en Windows."
    # pyautogui.write no escribe tildes ni eñes, por eso el texto no ASCII se pega desde el portapapeles.
    if texto.isascii():
        pyautogui.write(texto)
    else:
        import pyperclip

        pyperclip.copy(texto)
        pyautogui.hotkey("ctrl", "v")
    return "Escrito."


def atajo_teclado(teclas: str) -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return "Solo puedo usar el teclado en Windows."
    combinacion = [NOMBRES_TECLAS.get(tecla.strip(), tecla.strip()) for tecla in teclas.lower().split("+")]
    for tecla in combinacion:
        if tecla not in pyautogui.KEYBOARD_KEYS:
            return f"No conozco la tecla {tecla}."
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
