import difflib
import os
import re
import subprocess
import unicodedata
from pathlib import Path

ALIAS = {
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "bloc de notas": "notepad",
    "notas": "notepad",
    "calculadora": "calc",
    "explorador": "explorer",
    "explorador de archivos": "explorer",
    "configuracion": "ms-settings:",
    "ajustes": "ms-settings:",
    "panel de control": "control",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "spotify": "spotify:",
    "paint": "mspaint",
    "terminal": "wt",
    "simbolo del sistema": "cmd",
    "administrador de tareas": "taskmgr",
    "camara": "microsoft.windows.camera:",
    "whatsapp": "whatsapp:",
}

PROCESOS = {
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "bloc de notas": "notepad.exe",
    "notas": "notepad.exe",
    "calculadora": "CalculatorApp.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "spotify": "Spotify.exe",
    "paint": "mspaint.exe",
    "terminal": "WindowsTerminal.exe",
    "administrador de tareas": "Taskmgr.exe",
    "whatsapp": "WhatsApp.exe",
    "discord": "Discord.exe",
    "steam": "steam.exe",
}

# Matar estos tumba Windows o al propio Jarvis, su consola y su túnel.
# OpenConsole.exe es la consola de Windows Terminal, la que abre iniciar.bat por defecto en Windows 11.
PROTEGIDOS = {
    "explorer.exe", "python.exe", "pythonw.exe", "ngrok.exe", "cloudflared.exe", "cmd.exe", "conhost.exe",
    "windowsterminal.exe", "openconsole.exe", "svchost.exe", "winlogon.exe", "csrss.exe", "lsass.exe",
    "services.exe", "smss.exe", "wininit.exe", "dwm.exe", "sihost.exe", "ctfmon.exe", "fontdrvhost.exe",
}


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(sin_tildes.lower().split())


def _carpetas_inicio() -> list[Path]:
    menu = Path("Microsoft", "Windows", "Start Menu", "Programs")
    return [Path(os.environ[variable], menu) for variable in ("ProgramData", "APPDATA") if variable in os.environ]


def _accesos_directos() -> dict[str, Path]:
    accesos = {}
    for carpeta in _carpetas_inicio():
        for acceso in carpeta.rglob("*.lnk"):
            accesos.setdefault(normalizar(acceso.stem), acceso)
    return accesos


def _buscar_acceso(nombre: str) -> Path | None:
    accesos = _accesos_directos()
    contienen = [clave for clave in accesos if nombre in clave]
    if contienen:
        return accesos[min(contienen, key=len)]
    parecidos = difflib.get_close_matches(nombre, accesos, n=1, cutoff=0.6)
    return accesos[parecidos[0]] if parecidos else None


def abrir(destino: str | Path) -> bool:
    try:
        os.startfile(destino)
    except (OSError, AttributeError):
        return False
    return True


def abrir_programa(nombre: str) -> str:
    nombre = normalizar(nombre)
    if nombre in ALIAS and abrir(ALIAS[nombre]):
        return f"Abrí {nombre}."
    acceso = _buscar_acceso(nombre)
    if acceso and abrir(acceso):
        return f"Abrí {acceso.stem}."
    return "No encontré ese programa."


def cerrar_programa(nombre: str) -> str:
    nombre = normalizar(nombre)
    proceso = PROCESOS.get(nombre, nombre.replace(" ", "").removesuffix(".exe") + ".exe")
    # taskkill /IM acepta comodines: "*" cerraría todos los programas.
    if proceso.lower() in PROTEGIDOS or not re.fullmatch(r"[\w.-]+", proceso):
        return "Ese no lo puedo cerrar."
    try:
        resultado = subprocess.run(["taskkill", "/IM", proceso, "/F"], capture_output=True)
    except FileNotFoundError:
        return "Solo puedo cerrar programas en Windows."
    if resultado.returncode != 0:
        return f"{nombre} no estaba abierto."
    return f"Cerré {nombre}."
