import json
import threading
from types import SimpleNamespace

import pytest
from flask import Flask

import panel


@pytest.fixture
def cliente():
    app = Flask(__name__)
    app.register_blueprint(panel.rutas)
    return app.test_client()


def test_sirve_la_pagina_y_sus_archivos(cliente):
    with cliente.get("/hud") as pagina:
        assert b"<title>Jarvis HUD</title>" in pagina.data
    for archivo in ("hud.css", "hud.js"):
        with cliente.get(f"/hud/{archivo}") as respuesta:
            assert respuesta.status_code == 200


@pytest.mark.parametrize(
    "opciones",
    [
        {"headers": {"X-Forwarded-For": "1.2.3.4"}},
        {"base_url": "https://jarvis-feliz.ngrok-free.app"},
    ],
)
def test_no_se_sirve_fuera_de_este_pc(cliente, opciones):
    assert cliente.get("/hud", **opciones).status_code == 403
    assert cliente.get("/hud/eventos", **opciones).status_code == 403


def test_eventos_llegan_por_sse_y_el_cliente_se_borra_al_cerrar(cliente):
    respuesta = cliente.get("/hud/eventos", buffered=False)
    assert respuesta.mimetype == "text/event-stream"
    flujo = iter(respuesta.response)
    assert next(flujo) == b": conectado\n\n"

    panel.emitir("respuesta", "Hola & adiós")
    linea = next(flujo).decode()
    assert linea.startswith("data: ") and linea.endswith("\n\n")
    assert json.loads(linea[6:]) == {"tipo": "respuesta", "texto": "Hola & adiós"}

    respuesta.close()
    assert panel._clientes == []


def test_emitir_sin_ventanas_no_falla():
    panel.emitir("aviso", "nadie escucha")


def test_un_cliente_atascado_no_bloquea(monkeypatch):
    llena = panel.queue.Queue(maxsize=1)
    llena.put("viejo")
    monkeypatch.setattr(panel, "_clientes", [llena])
    panel.emitir("aviso", "nuevo")
    assert llena.get_nowait() == "viejo"


@pytest.fixture
def ventanas(monkeypatch):
    abiertas = []
    listo = threading.Event()
    monkeypatch.setattr(panel.config, "HUD_ACTIVO", True)
    monkeypatch.setattr(panel, "_ultima_apertura", float("-inf"))
    monkeypatch.setattr(panel, "_ocultador", None)
    monkeypatch.setattr(panel, "abrir_ventana", lambda: abiertas.append(1))
    monkeypatch.setattr(panel, "_buscar_ventana", lambda intentos: listo.set())
    return abiertas, listo


def mostrar_y_esperar(listo):
    listo.clear()
    panel.mostrar()
    assert listo.wait(2)


def test_mostrar_abre_una_sola_ventana_aunque_lleguen_varias_peticiones(ventanas):
    abiertas, listo = ventanas
    mostrar_y_esperar(listo)
    mostrar_y_esperar(listo)
    assert abiertas == [1]


def test_mostrar_no_abre_si_ya_hay_una_ventana_conectada(ventanas, monkeypatch):
    abiertas, listo = ventanas
    monkeypatch.setattr(panel, "_clientes", [panel.queue.Queue()])
    mostrar_y_esperar(listo)
    assert abiertas == []


def test_hud_desactivado_no_abre_nada(ventanas, monkeypatch):
    abiertas, _ = ventanas
    monkeypatch.setattr(panel.config, "HUD_ACTIVO", False)
    panel.mostrar()
    panel.ocultar_luego()
    assert abiertas == [] and panel._ocultador is None


def test_abrir_ventana_lanza_edge_en_modo_app(monkeypatch):
    lanzados = []
    monkeypatch.setattr(panel.subprocess, "Popen", lambda orden, **_: lanzados.append(orden))
    panel.abrir_ventana()
    assert lanzados[0][:5] == ["cmd", "/c", "start", "", "msedge"]
    assert f"--app={panel.URL}" in lanzados[0]


def test_abrir_ventana_sin_edge_no_falla(monkeypatch):
    def sin_edge(*_, **__):
        raise FileNotFoundError

    monkeypatch.setattr(panel.subprocess, "Popen", sin_edge)
    panel.abrir_ventana()


def test_mostrar_cancela_el_ocultado_pendiente(ventanas, monkeypatch):
    _, listo = ventanas
    monkeypatch.setattr(panel, "ESPERA_OCULTAR", 60)
    panel.ocultar_luego()
    temporizador = panel._ocultador
    mostrar_y_esperar(listo)
    assert panel._ocultador is None
    assert not temporizador.is_alive() or temporizador.finished.is_set()


def test_ocultar_minimiza_y_dice_si_habia_ventana(monkeypatch):
    acciones = []
    ventana = SimpleNamespace(minimize=lambda: acciones.append("minimizar"))
    monkeypatch.setattr(panel.config, "HUD_ACTIVO", True)
    monkeypatch.setattr(panel, "_poner_encima", lambda ventana, encima: acciones.append(("encima", encima)))
    monkeypatch.setattr(panel, "_buscar_ventana", lambda intentos: ventana)
    assert panel.ocultar() is True
    assert acciones == [("encima", False), "minimizar"]
    monkeypatch.setattr(panel, "_buscar_ventana", lambda intentos: None)
    assert panel.ocultar() is False
    monkeypatch.setattr(panel.config, "HUD_ACTIVO", False)
    monkeypatch.setattr(panel, "_buscar_ventana", lambda intentos: ventana)
    assert panel.ocultar() is False


def _esperar_evento(flujo) -> dict:
    linea = next(flujo).decode()
    while not linea.startswith("data: "):
        linea = next(flujo).decode()
    return json.loads(linea[6:])


def test_orden_del_hud_ejecuta_solo_las_permitidas(cliente, monkeypatch):
    hechas = []
    monkeypatch.setattr(panel, "_ordenes", lambda: {"pausa": lambda: hechas.append("pausa") or "Hecho."})
    assert cliente.post("/hud/orden", json={"orden": "pausa"}).status_code == 200
    assert hechas == ["pausa"]
    assert cliente.post("/hud/orden", json={"orden": "apagar"}).status_code == 400


@pytest.mark.parametrize(
    "opciones",
    [
        {"data": '{"orden": "pausa"}', "content_type": "text/plain"},
        {"json": {"orden": "pausa"}, "headers": {"Origin": "https://web-mala.com"}},
        {"json": {"orden": "pausa"}, "headers": {"X-Forwarded-For": "1.2.3.4"}},
    ],
)
def test_otra_web_o_internet_no_pueden_mandar_ordenes(cliente, monkeypatch, opciones):
    monkeypatch.setattr(panel, "_ordenes", lambda: pytest.fail("no debía ejecutarse"))
    assert cliente.post("/hud/orden", **opciones).status_code == 403


def test_las_ordenes_reales_existen():
    assert set(panel._ordenes()) == {"pausa", "cancelar_apagado", "dejar_de_vigilar", "ocultar"}


def test_lo_escrito_se_contesta_por_los_eventos(cliente, monkeypatch):
    monkeypatch.setattr(panel, "_responder", lambda texto: f"Respuesta a {texto}")
    respuesta = cliente.get("/hud/eventos", buffered=False)
    flujo = iter(respuesta.response)
    next(flujo)
    assert cliente.post("/hud/escribir", json={"texto": "  hola  "}).status_code == 202
    assert _esperar_evento(flujo) == {"tipo": "usuario", "texto": "hola"}
    assert _esperar_evento(flujo) == {"tipo": "respuesta", "texto": "Respuesta a hola"}
    respuesta.close()


def test_un_fallo_al_contestar_lo_escrito_se_explica(cliente, monkeypatch):
    def falla(texto):
        raise RuntimeError("sin red")

    monkeypatch.setattr(panel, "_responder", falla)
    respuesta = cliente.get("/hud/eventos", buffered=False)
    flujo = iter(respuesta.response)
    next(flujo)
    cliente.post("/hud/escribir", json={"texto": "hola"})
    _esperar_evento(flujo)
    assert _esperar_evento(flujo) == {"tipo": "respuesta", "texto": panel.FALLO_ESCRITO}
    respuesta.close()


def test_texto_vacio_o_sin_cerebro_se_rechaza(cliente, monkeypatch):
    monkeypatch.setattr(panel, "_responder", None)
    assert cliente.post("/hud/escribir", json={"texto": "hola"}).status_code == 400
    monkeypatch.setattr(panel, "_responder", lambda texto: "x")
    assert cliente.post("/hud/escribir", json={"texto": "   "}).status_code == 400
