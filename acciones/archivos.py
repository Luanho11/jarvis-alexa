import contextlib
import ctypes
import os
import time
from pathlib import Path

import psutil

from acciones.programas import abrir, normalizar
from acciones.sistema import atajo_teclado, soltar_foco_del_hud

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

SIN_VENTANAS = "Solo puedo manejar ventanas en Windows."
POSICIONES = {
    "izquierd": "izquierda",
    "derech": "derecha",
    "arriba": "arriba",
    "superior": "arriba",
    "abajo": "abajo",
    "inferior": "abajo",
    "maximiz": "maximizar",
    "minimiz": "minimizar",
    "restaur": "restaurar",
    "normal": "restaurar",
    "centr": "centro",
    "medio": "centro",
}
LUGARES = {
    "izquierda": "a la izquierda",
    "derecha": "a la derecha",
    "arriba": "arriba",
    "abajo": "abajo",
    "centro": "en el centro",
}
# El escritorio y la barra de tareas: WM_CLOSE al escritorio abre el diálogo de apagar Windows.
CLASES_ESCRITORIO = {"Progman", "WorkerW", "Shell_TrayWnd"}
# Las ventanas de consola: cerrar la equivocada mataría a Jarvis o al túnel de ngrok.
CONSOLAS = {"cmd.exe", "conhost.exe", "openconsole.exe", "windowsterminal.exe", "python.exe", "pythonw.exe", "ngrok.exe", "cloudflared.exe"}
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
MONITOR_DEFAULTTONEAREST = 2
SWP_NOZORDER = 0x0004
DPI_POR_MONITOR_V2 = -4


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


def buscar_rutas(nombre: str) -> list[Path]:
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
    encontrados = buscar_rutas(nombre)
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


def _oculta(hwnd: int) -> bool:
    # Las apps de la Tienda suspendidas y las de otros escritorios virtuales dejan ventanas "visibles"
    # que DWM no pinta (cloaked): activarlas no muestra nada.
    oculta = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(oculta), ctypes.sizeof(oculta))
    return oculta.value != 0


def _buscar_ventana(ventanas, nombre: str):
    nombre = normalizar(nombre)
    for ventana in ventanas.getAllWindows():
        if ventana.title and nombre in normalizar(ventana.title) and not _oculta(ventana._hWnd):
            return ventana
    return None


def _ventana_activa():
    ventanas = _ventanas()
    if ventanas is None:
        return None
    soltar_foco_del_hud()
    ventana = ventanas.getActiveWindow()
    return ventana if ventana is not None and ventana.title else None


def _al_frente(ventana) -> None:
    if ventana.isMinimized:
        ventana.restore()
    user32 = ctypes.windll.user32
    # Windows solo deja pasar una ventana al frente al programa que recibió la última entrada, y Jarvis
    # corre en segundo plano: compartir la cola de entrada con la ventana activa levanta esa restricción.
    propio = ctypes.windll.kernel32.GetCurrentThreadId()
    activo = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    unido = activo not in (0, propio) and user32.AttachThreadInput(propio, activo, True)
    try:
        user32.SetForegroundWindow(ventana._hWnd)
        user32.BringWindowToTop(ventana._hWnd)
    finally:
        if unido:
            user32.AttachThreadInput(propio, activo, False)
    if user32.GetForegroundWindow() != ventana._hWnd:
        ventana.minimize()
        ventana.restore()


def minimizar_todo() -> str:
    # win+d alterna: pedirlo dos veces volvería a mostrar todas las ventanas. win+m solo minimiza.
    resultado = atajo_teclado("win+m")
    return "Listo, escritorio despejado." if resultado == "Hecho." else resultado


def enfocar_ventana(nombre: str) -> str:
    ventanas = _ventanas()
    if ventanas is None:
        return SIN_VENTANAS
    ventana = _buscar_ventana(ventanas, nombre)
    if ventana is None:
        return f"No veo ninguna ventana de {normalizar(nombre)}."
    _al_frente(ventana)
    return f"Te muestro {ventana.title}."


def _intocable(ventana) -> bool:
    user32 = ctypes.windll.user32
    clase = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(ventana._hWnd, clase, len(clase))
    if clase.value in CLASES_ESCRITORIO:
        return True
    proceso = ctypes.c_uint32(0)
    user32.GetWindowThreadProcessId(ventana._hWnd, ctypes.byref(proceso))
    try:
        return psutil.Process(proceso.value).name().lower() in CONSOLAS
    except psutil.Error:
        return False


def cerrar_ventana() -> str:
    ventana = _ventana_activa()
    if ventana is None:
        return "No hay ninguna ventana activa que cerrar."
    if _intocable(ventana):
        return "Esa ventana no la cierro: es el escritorio o una consola, y podría ser la mía o la del túnel."
    # close() envía WM_CLOSE, lo mismo que la X: el programa puede preguntar si guardar.
    ventana.close()
    return "Ventana cerrada."


def maximizar_ventana() -> str:
    return acomodar_ventana("maximizar")


def _posicion(texto: str) -> str | None:
    texto = normalizar(texto)
    return next((posicion for clave, posicion in POSICIONES.items() if clave in texto), None)


def _rectangulo(posicion: str, area: tuple[int, int, int, int], tamano: tuple[int, int]) -> tuple[int, int, int, int]:
    """(x, y, ancho, alto) visibles de la ventana dentro del área de trabajo (izquierda, arriba, derecha, abajo)."""
    izquierda, arriba, derecha, abajo = area
    ancho, alto = derecha - izquierda, abajo - arriba
    mitad_ancho, mitad_alto = ancho // 2, alto // 2
    if posicion == "izquierda":
        return izquierda, arriba, mitad_ancho, alto
    if posicion == "derecha":
        return izquierda + mitad_ancho, arriba, ancho - mitad_ancho, alto
    if posicion == "arriba":
        return izquierda, arriba, ancho, mitad_alto
    if posicion == "abajo":
        return izquierda, arriba + mitad_alto, ancho, alto - mitad_alto
    ancho_ventana, alto_ventana = min(tamano[0], ancho), min(tamano[1], alto)
    return izquierda + (ancho - ancho_ventana) // 2, arriba + (alto - alto_ventana) // 2, ancho_ventana, alto_ventana


class _Rect(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int32), ("top", ctypes.c_int32), ("right", ctypes.c_int32), ("bottom", ctypes.c_int32)]


class _InfoMonitor(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("rcMonitor", _Rect), ("rcWork", _Rect), ("dwFlags", ctypes.c_uint32)]


def _colocar(ventana, posicion: str) -> None:
    # Se calcula y se mueve en vez de pulsar win+flecha: el acople de Windows depende de la ventana activa,
    # de su estado (win+izquierda en una ventana a la derecha la devuelve al centro), abre el asistente
    # que pide elegir otra ventana y se puede desactivar en Configuración.
    user32 = ctypes.windll.user32
    hwnd = ventana._hWnd
    # Restaurar una ventana minimizada que estaba maximizada la deja maximizada: hace falta otro restore.
    if ventana.isMinimized:
        ventana.restore()
    if ventana.isMaximized:
        ventana.restore()
    user32.MonitorFromWindow.restype = ctypes.c_void_p
    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_InfoMonitor)]
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = _InfoMonitor(cbSize=ctypes.sizeof(_InfoMonitor))
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))
    marco, visible = _Rect(), _Rect()
    user32.GetWindowRect(hwnd, ctypes.byref(marco))
    # En Windows 10 y 11 el rectángulo de la ventana incluye unos bordes invisibles de ~7 px para agarrarla:
    # sin descontarlos, dos ventanas a izquierda y derecha dejarían un hueco entre ellas.
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(visible), ctypes.sizeof(visible))
    tamano = (visible.right - visible.left, visible.bottom - visible.top)
    area = (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
    x, y, ancho, alto = _rectangulo(posicion, area, tamano)
    izquierda, arriba = visible.left - marco.left, visible.top - marco.top
    derecha, abajo = marco.right - visible.right, marco.bottom - visible.bottom
    user32.SetWindowPos(hwnd, 0, x - izquierda, y - arriba, ancho + izquierda + derecha, alto + arriba + abajo, SWP_NOZORDER)


@contextlib.contextmanager
def _pixeles_reales():
    # Con el escalado de pantalla al 125 % o 150 %, Windows da a cada programa coordenadas "virtuales" según
    # su modo de DPI, pero DWM siempre las da reales: en este hilo se trabaja en píxeles reales por monitor.
    user32 = ctypes.windll.user32
    user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    anterior = user32.SetThreadDpiAwarenessContext(DPI_POR_MONITOR_V2)
    try:
        yield
    finally:
        user32.SetThreadDpiAwarenessContext(anterior)


def acomodar_ventana(posicion: str, nombre: str = "") -> str:
    accion = _posicion(posicion)
    if accion is None:
        return "Dime si la pongo a la izquierda, a la derecha, arriba, abajo, en el centro, maximizada, minimizada o normal."
    ventanas = _ventanas()
    if ventanas is None:
        return SIN_VENTANAS
    if nombre:
        ventana = _buscar_ventana(ventanas, nombre)
        if ventana is None:
            return f"No veo ninguna ventana de {normalizar(nombre)}."
    else:
        ventana = _ventana_activa()
        if ventana is None:
            return "No hay ninguna ventana activa que mover."
    if accion == "minimizar":
        ventana.minimize()
        return f"Minimicé {ventana.title}."
    if nombre:
        _al_frente(ventana)
    if accion == "maximizar":
        ventana.maximize()
        return f"Maximicé {ventana.title}."
    if accion == "restaurar":
        ventana.restore()
        return f"Dejé {ventana.title} en tamaño normal."
    with _pixeles_reales():
        _colocar(ventana, accion)
    return f"Puse {ventana.title} {LUGARES[accion]}."
