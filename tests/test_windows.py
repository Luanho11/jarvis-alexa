"""Comprueba en Windows de verdad (GitHub Actions) que las librerías tienen lo que usa Jarvis, sin pulsar teclas ni mover ventanas."""
import os
import sys

import pytest

from acciones import archivos, programas, sistema

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="solo en Windows")


def test_pycaw_y_comtypes():
    import comtypes
    from pycaw.pycaw import AudioUtilities
    from pycaw.utils import AudioDevice

    assert callable(comtypes.CoInitialize) and callable(AudioUtilities.GetSpeakers)
    assert isinstance(AudioDevice.EndpointVolume, property)


def test_pyautogui_conoce_todas_las_teclas_que_usa_jarvis():
    import pyautogui

    usadas = {"volumeup", "volumedown", "volumemute", "playpause", "nexttrack", "prevtrack", "f", "l", "j", "n", "v", "d", "end"}
    usadas |= {"ctrl", "shift", "win", "alt", "f4", "w", "enter", "esc", "delete", "space"}
    assert usadas | set(sistema.NOMBRES_TECLAS.values()) <= set(pyautogui.KEYBOARD_KEYS)


def test_pygetwindow_tiene_lo_que_usan_el_hud_y_las_ventanas():
    import pygetwindow

    for funcion in ("getWindowsWithTitle", "getActiveWindow", "getAllWindows"):
        assert callable(getattr(pygetwindow, funcion))
    assert issubclass(pygetwindow.PyGetWindowException, Exception)
    for atributo in ("isMinimized", "restore", "minimize", "maximize", "activate", "close"):
        assert hasattr(pygetwindow.Win32Window, atributo)


def test_portapapeles_captura_y_api_de_ventanas():
    import ctypes

    import pyperclip
    from PIL import ImageGrab

    assert callable(pyperclip.copy) and callable(ImageGrab.grab)
    assert callable(ctypes.windll.user32.SetWindowPos)
    assert callable(os.startfile)


def test_carpetas_del_usuario_salen_del_registro():
    for nombre in ("documentos", "descargas", "escritorio"):
        carpeta = archivos.ruta_carpeta(nombre)
        assert carpeta is not None and carpeta.is_dir()


def test_menu_inicio_se_puede_leer():
    assert programas._carpetas_inicio()
    assert isinstance(programas._accesos_directos(), dict)
