import sys
from types import SimpleNamespace

import pytest

from acciones import archivos, sistema


class Lista(list):
    pass


@pytest.fixture
def ejecutados(monkeypatch):
    llamadas = Lista()
    llamadas.codigo = 0
    monkeypatch.setattr(
        sistema.subprocess, "run", lambda comando, capture_output: llamadas.append(comando) or SimpleNamespace(returncode=llamadas.codigo)
    )
    return llamadas


def test_apagar_con_margen_minimo(ejecutados):
    assert sistema.apagar(0) == "Apagaré el PC en 1 minuto. Si cambias de idea, di cancela el apagado."
    assert ejecutados == [["shutdown", "/s", "/t", "60"]]


def test_reiniciar_en_minutos(ejecutados):
    assert sistema.reiniciar(5).startswith("Reiniciaré el PC en 5 minutos.")
    assert ejecutados == [["shutdown", "/r", "/t", "300"]]


def test_apagar_falla(ejecutados):
    ejecutados.codigo = 1190
    assert sistema.apagar() == "No pude programar el apagado."


def test_cancelar_apagado(ejecutados):
    assert sistema.cancelar_apagado() == "Cancelé el apagado."
    ejecutados.codigo = 1116
    assert sistema.cancelar_apagado() == "No había ningún apagado programado."
    assert ejecutados == [["shutdown", "/a"]] * 2


def test_fuera_de_windows_no_lanza(monkeypatch):
    def run(comando, capture_output):
        raise FileNotFoundError

    monkeypatch.setattr(sistema.subprocess, "run", run)
    assert sistema.bloquear() == "No pude bloquear el PC."


def test_bloquear(ejecutados):
    assert sistema.bloquear() == "PC bloqueado."
    assert ejecutados == [["rundll32.exe", "user32.dll,LockWorkStation"]]


def test_suspender_espera_para_responder(monkeypatch):
    programados = []

    class Timer:
        def __init__(self, segundos, funcion, args):
            programados.append((segundos, args))

        def start(self):
            pass

    monkeypatch.setattr(sistema.threading, "Timer", Timer)
    assert sistema.suspender() == "Suspendo el PC."
    assert programados == [(3, [["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]])]


def test_captura_pantalla_va_a_la_carpeta_imagenes_real(monkeypatch, tmp_path):
    guardadas = []
    imagen = SimpleNamespace(save=guardadas.append)
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(ImageGrab=SimpleNamespace(grab=lambda: imagen)))
    imagenes = tmp_path / "OneDrive" / "Imágenes"
    monkeypatch.setattr(archivos, "ruta_carpeta", lambda nombre: imagenes if nombre == "imagenes" else None)
    assert "Jarvis" in sistema.captura_pantalla()
    assert guardadas[0].parent == imagenes / "Jarvis"
    assert guardadas[0].suffix == ".png"


@pytest.fixture
def teclado(monkeypatch):
    acciones = []
    falso = SimpleNamespace(
        KEYBOARD_KEYS=["ctrl", "alt", "f4", "win", "d", "v", "w", "enter"],
        write=lambda texto: acciones.append(("write", texto)),
        hotkey=lambda *teclas: acciones.append(("hotkey", teclas)),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", falso)
    monkeypatch.setitem(sys.modules, "pyperclip", SimpleNamespace(copy=lambda texto: acciones.append(("copy", texto))))
    return acciones


def test_escribir_ascii_teclea(teclado):
    assert sistema.escribir_texto("hola") == "Escrito."
    assert teclado == [("write", "hola")]


def test_escribir_con_tildes_pega(teclado):
    sistema.escribir_texto("canción")
    assert teclado == [("copy", "canción"), ("hotkey", ("ctrl", "v"))]


def test_atajo_traduce_y_pulsa(teclado):
    assert sistema.atajo_teclado("Control + W") == "Hecho."
    sistema.atajo_teclado("windows+d")
    assert teclado == [("hotkey", ("ctrl", "w")), ("hotkey", ("win", "d"))]


def test_atajo_tecla_desconocida(teclado):
    assert sistema.atajo_teclado("ctrl+patata") == "No conozco la tecla patata."
    assert teclado == []


def test_sin_pyautogui(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    assert "Windows" in sistema.escribir_texto("hola")
    assert "Windows" in sistema.atajo_teclado("alt+f4")


def test_estado_pc_con_y_sin_bateria(monkeypatch):
    monkeypatch.setattr(sistema.psutil, "cpu_percent", lambda interval: 12.4)
    monkeypatch.setattr(sistema.psutil, "virtual_memory", lambda: SimpleNamespace(percent=40.6))
    monkeypatch.setattr(sistema.psutil, "sensors_battery", lambda: None)
    assert sistema.estado_pc() == "Procesador al 12 por ciento y memoria al 41 por ciento."
    monkeypatch.setattr(sistema.psutil, "sensors_battery", lambda: SimpleNamespace(percent=80, power_plugged=True))
    assert sistema.estado_pc().endswith("Batería al 80 por ciento, cargando.")


def test_el_hud_recibe_la_cuenta_atras_y_su_cancelacion(ejecutados, monkeypatch):
    eventos = []
    monkeypatch.setattr(sistema.panel, "emitir", lambda tipo, texto="": eventos.append((tipo, texto)))
    sistema.apagar(2)
    sistema.reiniciar(1)
    sistema.cancelar_apagado()
    assert eventos == [("apagado", "120"), ("reinicio", "60"), ("apagado", "0")]


def test_sin_apagado_programado_el_hud_no_cambia(ejecutados, monkeypatch):
    eventos = []
    monkeypatch.setattr(sistema.panel, "emitir", lambda tipo, texto="": eventos.append((tipo, texto)))
    ejecutados.codigo = 1
    sistema.apagar()
    assert eventos == []
