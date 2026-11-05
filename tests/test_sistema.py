import ctypes
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
        KEYBOARD_KEYS=["ctrl", "alt", "f4", "win", "d", "v", "w", "enter", "shift", "right"],
        hotkey=lambda *teclas: acciones.append(("hotkey", teclas)),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", falso)
    monkeypatch.setattr(sistema, "soltar_foco_del_hud", lambda: acciones.append(("hud",)))
    return acciones


@pytest.fixture
def send_input(monkeypatch):
    envios = []

    def enviar(cuantas, entradas, tamano):
        envios.append([(e.type, e.evento.ki.wVk, e.evento.ki.wScan, e.evento.ki.dwFlags) for e in entradas])
        return cuantas

    user32 = SimpleNamespace(SendInput=enviar)
    monkeypatch.setattr(sistema.ctypes, "windll", SimpleNamespace(user32=user32), raising=False)
    monkeypatch.setattr(sistema, "soltar_foco_del_hud", lambda: envios.append("hud"))
    return envios


UNICODE, SUELTA = sistema.KEYEVENTF_UNICODE, sistema.KEYEVENTF_KEYUP


def test_pulsaciones_unicode_sin_depender_del_teclado():
    assert sistema._pulsaciones("ñ@") == [(0, 0xF1, UNICODE), (0, 0xF1, UNICODE | SUELTA), (0, 0x40, UNICODE), (0, 0x40, UNICODE | SUELTA)]


def test_saltos_de_linea_y_tabuladores_son_teclas():
    assert sistema._pulsaciones("\r\n\t") == [(0x0D, 0, 0), (0x0D, 0, SUELTA), (0x09, 0, 0), (0x09, 0, SUELTA)]


def test_un_emoji_va_en_dos_unidades_utf16():
    assert [unidad for _, unidad, flags in sistema._pulsaciones("😀") if not flags & SUELTA] == [0xD83D, 0xDE00]


def test_la_entrada_mide_lo_que_espera_send_input():
    assert ctypes.sizeof(sistema._Entrada) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_escribir_con_tildes_suelta_el_hud_y_envia_todo(send_input):
    assert sistema.escribir_texto("Hola ñandú") == "Escrito."
    assert send_input[0] == "hud"
    teclas = send_input[1]
    assert len(teclas) == 20
    assert {tipo for tipo, *_ in teclas} == {sistema.INPUT_KEYBOARD}
    assert "".join(chr(scan) for _, _, scan, flags in teclas if flags == UNICODE) == "Hola ñandú"


def test_un_texto_largo_va_por_partes(send_input, monkeypatch):
    monkeypatch.setattr(sistema, "CARACTERES_POR_ENVIO", 4)
    sistema.escribir_texto("abcdefghij")
    assert [len(envio) for envio in send_input[1:]] == [8, 8, 4]


def test_escribir_con_el_teclado_bloqueado(send_input, monkeypatch):
    monkeypatch.setattr(sistema.ctypes.windll.user32, "SendInput", lambda cuantas, entradas, tamano: 0)
    assert sistema.escribir_texto("hola") == "No pude escribir: Windows tiene el teclado bloqueado ahora."


def test_atajo_traduce_y_pulsa(teclado):
    assert sistema.atajo_teclado("Control + W") == "Hecho."
    sistema.atajo_teclado("windows+d")
    sistema.atajo_teclado("mayús+flecha derecha")
    pulsadas = [accion for accion in teclado if accion != ("hud",)]
    assert pulsadas == [("hotkey", ("ctrl", "w")), ("hotkey", ("win", "d")), ("hotkey", ("shift", "right"))]
    assert teclado[0] == ("hud",)


def test_atajo_tecla_desconocida(teclado):
    assert sistema.atajo_teclado("ctrl+patata") == "No conozco la tecla patata."
    assert teclado == []


def test_sin_windows(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    monkeypatch.delattr(sistema.ctypes, "windll", raising=False)
    assert "Windows" in sistema.escribir_texto("hola")
    assert "Windows" in sistema.atajo_teclado("alt+f4")


@pytest.mark.parametrize("titulo, escondido", [("Jarvis HUD - Perfil 1 - Microsoft Edge", True), ("Bloc de notas", False)])
def test_suelta_el_foco_solo_si_lo_tiene_el_hud(monkeypatch, titulo, escondido):
    esperas, ocultados = [], []
    monkeypatch.setitem(sys.modules, "pygetwindow", SimpleNamespace(getActiveWindow=lambda: SimpleNamespace(title=titulo)))
    monkeypatch.setattr(sistema.panel, "ocultar", lambda: ocultados.append(True) or True)
    monkeypatch.setattr(sistema.time, "sleep", esperas.append)
    sistema.soltar_foco_del_hud()
    assert bool(ocultados) == escondido
    assert esperas == ([sistema.ESPERA_HUD] if escondido else [])


def test_estado_pc_con_y_sin_bateria(monkeypatch):
    monkeypatch.setattr(sistema.psutil, "cpu_percent", lambda interval: 12.4)
    monkeypatch.setattr(sistema.psutil, "virtual_memory", lambda: SimpleNamespace(percent=40.6))
    monkeypatch.setattr(sistema.psutil, "sensors_battery", lambda: None)
    assert sistema.estado_pc() == "Procesador al 12 por ciento y memoria al 41 por ciento."
    monkeypatch.setattr(sistema.psutil, "sensors_battery", lambda: SimpleNamespace(percent=80, power_plugged=True))
    assert sistema.estado_pc().endswith("Batería al 80 por ciento, cargando.")
