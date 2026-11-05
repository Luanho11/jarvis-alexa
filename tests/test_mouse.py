import sys
from types import SimpleNamespace

import pytest

from acciones import mouse, vision


class FalsoPyautogui:
    def __init__(self, ancho=1920, alto=1080, posicion=(500, 500)):
        self.ancho, self.alto = ancho, alto
        self.posicion = posicion
        self.acciones = []
        self.FAILSAFE = True

    def size(self):
        return self.ancho, self.alto

    def position(self):
        return self.posicion

    def moveTo(self, x, y, duration):
        self.acciones.append(("mover", x, y))

    def click(self, *punto, button, clicks):
        self.acciones.append(("clic", *punto, button, clicks))

    def scroll(self, cantidad):
        self.acciones.append(("scroll", cantidad))


@pytest.fixture
def raton(monkeypatch):
    falso = FalsoPyautogui()
    monkeypatch.setitem(sys.modules, "pyautogui", falso)
    monkeypatch.setattr(mouse.panel, "ocultar", lambda: falso.acciones.append(("ocultar_hud",)) or False)
    monkeypatch.setattr(mouse, "_rueda_horizontal", lambda cantidad: falso.acciones.append(("rueda_horizontal", cantidad)))
    return falso


@pytest.mark.parametrize(
    "direccion, destino",
    [("derecha", (600, 500)), ("a la izquierda", (400, 500)), ("arriba", (500, 400)), ("Abajo", (500, 600))],
)
def test_mover_en_una_direccion(raton, direccion, destino):
    assert mouse.mover_mouse(direccion) == "Listo."
    assert raton.acciones == [("mover", *destino)]
    assert raton.FAILSAFE is False


def test_mover_no_sale_de_la_pantalla(raton):
    mouse.mover_mouse("derecha", 5000)
    mouse.mover_mouse("arriba", 5000)
    assert raton.acciones == [("mover", 1919, 500), ("mover", 500, 0)]


@pytest.mark.parametrize(
    "posicion, destino",
    [
        ("centro", (960, 540)),
        ("esquina superior izquierda", (0, 0)),
        ("esquina superior derecha", (1919, 0)),
        ("esquina inferior izquierda", (0, 1079)),
        ("abajo a la derecha", (1919, 1079)),
        ("lado izquierdo", (0, 540)),
    ],
)
def test_mover_a_una_posicion(raton, posicion, destino):
    assert mouse.mover_mouse(posicion=posicion) == "Listo."
    assert raton.acciones == [("mover", *destino)]


def test_mover_sin_saber_a_donde(raton):
    assert mouse.mover_mouse() == "Dime si muevo el mouse arriba, abajo, a la izquierda o a la derecha."
    assert mouse.mover_mouse(posicion="la cocina") == "No conozco la posición la cocina."
    assert raton.acciones == []


@pytest.mark.parametrize(
    "boton, veces, esperado, respuesta",
    [
        ("izquierdo", 1, ("clic", "left", 1), "Clic."),
        ("", 2, ("clic", "left", 2), "Doble clic."),
        ("botón derecho", 1, ("clic", "right", 1), "Clic."),
        ("medio", 9, ("clic", "middle", 3), "Clic."),
    ],
)
def test_hacer_clic_aparta_el_hud(raton, boton, veces, esperado, respuesta):
    assert mouse.hacer_clic(boton, veces) == respuesta
    assert raton.acciones == [("ocultar_hud",), esperado]


def test_boton_desconocido(raton):
    assert mouse.hacer_clic("lateral") == "No conozco el botón lateral."
    assert raton.acciones == []


def test_desplazar_en_muescas_de_windows(raton):
    assert mouse.desplazar() == "Listo."
    mouse.desplazar("arriba", 2)
    mouse.desplazar("derecha", 1)
    mouse.desplazar("izquierda", 500)
    rueda = [accion for accion in raton.acciones if accion != ("ocultar_hud",)]
    assert rueda == [("scroll", -600), ("scroll", 240), ("rueda_horizontal", 120), ("rueda_horizontal", -6000)]


def test_desplazar_sin_direccion(raton):
    assert mouse.desplazar("en diagonal").startswith("Dime si desplazo")


def test_sin_pyautogui(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    for accion in (lambda: mouse.mover_mouse("derecha"), mouse.hacer_clic, mouse.desplazar, lambda: mouse.clic_en("Aceptar")):
        assert accion() == "Solo puedo usar el mouse en Windows."


def test_apartar_hud_espera_solo_si_lo_escondio(monkeypatch):
    esperas = []
    monkeypatch.setattr(mouse.time, "sleep", esperas.append)
    monkeypatch.setattr(mouse.panel, "ocultar", lambda: True)
    mouse._apartar_hud()
    monkeypatch.setattr(mouse.panel, "ocultar", lambda: False)
    mouse._apartar_hud()
    assert esperas == [mouse.ESPERA_HUD]


@pytest.mark.parametrize(
    "texto, caja",
    [
        ('{"box_2d": [100, 200, 300, 400]}', (100, 200, 300, 400)),
        ('```json\n{"box_2d": [0, 0, 1000, 1000]}\n```', (0, 0, 1000, 1000)),
        ('[{"box_2d": [10, 20, 30, 40], "label": "Aceptar"}]', (10, 20, 30, 40)),
        ('{"box_2d": []}', None),
        ("No veo ningún botón Aceptar.", None),
        ('{"box_2d": [100, 200, 300]}', None),
        ('{"box_2d": [300, 200, 100, 400]}', None),
        ('{"box_2d": [100, 200, 300, 1400]}', None),
        ('{"box_2d": ["a", 1, 2, 3]}', None),
        ('{"box_2d": [true, 1, 2, 3]}', None),
        ('{"caja": [1, 2, 3, 4]}', None),
        ("[]", None),
        ("", None),
    ],
)
def test_leer_caja_de_gemini(texto, caja):
    assert mouse._leer_caja(texto) == caja


def test_coordenadas_a_pixeles_de_pantalla():
    # [ymin, xmin, ymax, xmax] de 0 a 1000: centro en x=500, y=250.
    assert mouse._a_pantalla((200, 400, 300, 600), 1920, 1080) == (960, 270)
    assert mouse._a_pantalla((1000, 1000, 1000, 1000), 1920, 1080) == (1919, 1079)


def test_coordenadas_con_escalado_dpi():
    # Windows al 125 %: un botón en (1200, 600) físicos de 1920x1080. Gemini ve la captura reducida a 1280x720
    # (botón en 800, 400) y lo da normalizado: x=625, y=556. Sirve para los dos espacios de pyautogui.
    caja = (556, 625, 556, 625)
    assert mouse._a_pantalla(caja, 1920, 1080) == (1200, 600)
    assert mouse._a_pantalla(caja, 1536, 864) == (960, 480)


@pytest.fixture
def gemini(monkeypatch, raton):
    pedidos = []
    respuesta = SimpleNamespace(texto='{"box_2d": [900, 450, 940, 550]}')

    def mirar_pantalla(instruccion, **opciones):
        raton.acciones.append(("captura",))
        pedidos.append((instruccion, opciones))
        return respuesta.texto

    monkeypatch.setattr(mouse.vision, "mirar_pantalla", mirar_pantalla)
    eventos = []
    monkeypatch.setattr(mouse.panel, "emitir", lambda tipo, texto="": eventos.append((tipo, texto)))
    return SimpleNamespace(pedidos=pedidos, respuesta=respuesta, eventos=eventos)


def test_clic_en_un_elemento(raton, gemini):
    assert mouse.clic_en(" botón Aceptar ", veces=2) == "Hice clic en botón Aceptar."
    assert raton.acciones == [("ocultar_hud",), ("captura",), ("clic", 960, 994, "left", 2)]
    instruccion, opciones = gemini.pedidos[0]
    assert "botón Aceptar" in instruccion and "box_2d" in instruccion and "0 a 1000" in instruccion
    assert opciones == {"response_format": mouse.FORMATO_JSON}
    assert gemini.eventos == [("accion", "Clic en botón Aceptar")]


@pytest.mark.parametrize("texto", ['{"box_2d": []}', "Lo siento, no lo veo.", '{"box_2d": "abajo"}'])
def test_clic_en_algo_que_no_esta(raton, gemini, texto):
    gemini.respuesta.texto = texto
    assert mouse.clic_en("el video") == "No encontré eso en la pantalla."
    assert not [accion for accion in raton.acciones if accion[0] == "clic"]


def test_clic_en_sin_vision(raton, monkeypatch):
    def falla(instruccion, **opciones):
        raise vision.SinVision("Para ver la pantalla necesito la clave de Gemini.")

    monkeypatch.setattr(mouse.vision, "mirar_pantalla", falla)
    assert mouse.clic_en("el buscador") == "Para ver la pantalla necesito la clave de Gemini."


def test_clic_en_sin_descripcion_o_con_boton_raro(raton, gemini):
    assert mouse.clic_en("  ") == "Dime en qué hago clic."
    assert mouse.clic_en("Aceptar", boton="lateral") == "No conozco el botón lateral."
    assert gemini.pedidos == [] and raton.acciones == []
