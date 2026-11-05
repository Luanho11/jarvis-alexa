import os
import time
from pathlib import Path

from acciones.programas import abrir, normalizar
from acciones.sistema import atajo_teclado

# Windows anota en el registro dónde está cada carpeta, también si OneDrive la movió.
CARPETAS_SHELL = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
CLAVES_REGISTRO = {
    "documentos": "Personal",
    "descargas": "{374DE290-123F-4565-9164-39C4925E467B}",
    "escritorio": "Desktop",
    "imagenes": "My Pictures",
    "musica": "My Music",
    "videos": "My Video",
}
# Sin registro se adivina: Windows usa el nombre en inglés y OneDrive, si las respalda, el traducido.
CARPETAS = {
    "documentos": ["Documents", "Documentos"],
    "descargas": ["Downloads", "Descargas"],
    "escritorio": ["Desktop", "Escritorio"],
    "imagenes": ["Pictures", "Imágenes"],
    "musica": ["Music", "Música"],
    "videos": ["Videos", "Vídeos"],
}

CARPETAS_BUSQUEDA = ["documentos", "descargas", "escritorio"]
SEGUNDOS_BUSQUEDA = 2.5
MAXIMO_LISTADO = 3


def _carpeta_registro(clave: str) -> Path | None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CARPETAS_SHELL) as carpetas:
            valor, _ = winreg.QueryValueEx(carpetas, CLAVES_REGISTRO[clave])
    except (ImportError, OSError):
        return None
    ruta = Path(os.path.expandvars(valor))
    return ruta if ruta.is_dir() else None


def ruta_carpeta(nombre: str) -> Path | None:
    clave = normalizar(nombre)
    nombres = CARPETAS.get(clave)
    if nombres is None:
        return None
    registrada = _carpeta_registro(clave)
    if registrada:
        return registrada
    onedrive = Path(os.environ.get("OneDrive", Path.home() / "OneDrive"))
    for raiz in (onedrive, Path.home()):
        for carpeta in nombres:
            if (raiz / carpeta).is_dir():
                return raiz / carpeta
    return None


def abrir_carpeta(nombre: str) -> str:
    carpeta = ruta_carpeta(nombre)
    if carpeta is None:
        return f"No encontré la carpeta {nombre}."
    if not abrir(carpeta):
        return "No pude abrir la carpeta."
    return f"Abrí {nombre}."


def _buscar(nombre: str) -> list[Path]:
    limite = time.monotonic() + SEGUNDOS_BUSQUEDA
    encontrados = []
    for clave in CARPETAS_BUSQUEDA:
        carpeta = ruta_carpeta(clave)
        if carpeta is None:
            continue
        for raiz, subcarpetas, archivos in os.walk(carpeta):
            if time.monotonic() > limite:
                return encontrados
            subcarpetas[:] = [sub for sub in subcarpetas if not sub.startswith(".")]
            encontrados += [Path(raiz, archivo) for archivo in archivos if nombre in normalizar(Path(archivo).stem)]
    return encontrados


def buscar_archivo(nombre: str) -> str:
    nombre = normalizar(nombre)
    encontrados = _buscar(nombre)
    if not encontrados:
        return f"No encontré ningún archivo con {nombre}."
    exactos = [archivo for archivo in encontrados if normalizar(archivo.stem) == nombre]
    if len(encontrados) == 1 or exactos:
        archivo = (exactos or encontrados)[0]
        if not abrir(archivo):
            return "Lo encontré pero no pude abrirlo."
        return f"Abrí {archivo.name}."
    recientes = sorted(encontrados, key=lambda archivo: archivo.stat().st_mtime, reverse=True)
    nombres = ", ".join(archivo.name for archivo in recientes[:MAXIMO_LISTADO])
    return f"Encontré {len(encontrados)} archivos. Los más recientes: {nombres}. ¿Cuál abro?"


def _ventanas():
    try:
        import pygetwindow
    except (ImportError, NotImplementedError):
        return None
    return pygetwindow


def minimizar_todo() -> str:
    resultado = atajo_teclado("win+d")
    return "Listo, escritorio despejado." if resultado == "Hecho." else resultado


def _ventana_activa():
    ventanas = _ventanas()
    if ventanas is None:
        return None
    ventana = ventanas.getActiveWindow()
    return ventana if ventana is not None and ventana.title else None


def enfocar_ventana(nombre: str) -> str:
    ventanas = _ventanas()
    if ventanas is None:
        return "Solo puedo manejar ventanas en Windows."
    nombre = normalizar(nombre)
    coincidencias = [ventana for ventana in ventanas.getAllWindows() if ventana.title and nombre in normalizar(ventana.title)]
    if not coincidencias:
        return f"No veo ninguna ventana de {nombre}."
    ventana = coincidencias[0]
    if ventana.isMinimized:
        ventana.restore()
    try:
        ventana.activate()
    except ventanas.PyGetWindowException:
        # Windows a veces bloquea SetForegroundWindow; minimizar y restaurar la trae al frente igual.
        ventana.minimize()
        ventana.restore()
    return f"Te muestro {ventana.title}."


def cerrar_ventana() -> str:
    ventana = _ventana_activa()
    if ventana is None:
        return "No hay ninguna ventana activa que cerrar."
    # close() envía WM_CLOSE, lo mismo que alt+f4, pero sin abrir el diálogo de apagado si el foco está en el escritorio.
    ventana.close()
    return "Ventana cerrada."


def maximizar_ventana() -> str:
    ventana = _ventana_activa()
    if ventana is None:
        return "No hay ninguna ventana activa que maximizar."
    ventana.maximize()
    return "Ventana maximizada."
