import sys
import threading
from types import SimpleNamespace

import pytest
import requests

from acciones import pc


@pytest.fixture
def teclas(monkeypatch):
    pulsadas = []
    falso = SimpleNamespace(press=lambda tecla, presses=1: pulsadas.append((tecla, presses)))
    monkeypatch.setitem(sys.modules, "pyautogui", falso)
    return pulsadas


@pytest.fixture
def navegador(monkeypatch):
    abiertas = []
    monkeypatch.setattr(pc.webbrowser, "open", abiertas.append)
    return abiertas


@pytest.mark.parametrize(
    "accion, tecla, veces",
    [
        (lambda: pc.subir_volumen(), "volumeup", 5),
        (lambda: pc.bajar_volumen(3), "volumedown", 3),
        (pc.silenciar, "volumemute", 1),
        (pc.pausar_reanudar, "playpause", 1),
        (pc.siguiente, "nexttrack", 1),
        (pc.anterior, "prevtrack", 1),
        (pc.pantalla_completa, "f", 1),
        (lambda: pc.adelantar(), "l", 1),
        (lambda: pc.adelantar(30), "l", 3),
        (lambda: pc.retroceder(5), "j", 1),
        (lambda: pc.retroceder(20), "j", 2),
    ],
)
def test_teclas_multimedia(teclas, accion, tecla, veces):
    assert accion()
    assert teclas == [(tecla, veces)]


def test_las_teclas_no_fallan_con_el_raton_en_una_esquina(teclas):
    pc.silenciar()
    assert sys.modules["pyautogui"].FAILSAFE is False


def test_siguiente_video(monkeypatch):
    combinaciones = []
    falso = SimpleNamespace(hotkey=lambda *teclas: combinaciones.append(teclas))
    monkeypatch.setitem(sys.modules, "pyautogui", falso)
    assert pc.siguiente_video() == "Siguiente video."
    assert combinaciones == [("shift", "n")]


def test_fijar_volumen_limita_entre_0_y_100(monkeypatch):
    niveles = []
    falso = SimpleNamespace(SetMasterVolumeLevelScalar=lambda nivel, _: niveles.append(nivel))
    monkeypatch.setattr(pc, "_control_volumen", lambda: falso)
    assert pc.fijar_volumen(150) == "Volumen al 100 por ciento."
    assert pc.fijar_volumen(30) == "Volumen al 30 por ciento."
    assert niveles == [1.0, 0.3]


def test_control_volumen_inicia_com_en_el_hilo_que_lo_usa(monkeypatch):
    pasos = []
    volumen = object()
    comtypes = SimpleNamespace(CoInitialize=lambda: pasos.append(("com", threading.get_ident())))

    def altavoces():
        pasos.append(("altavoces", threading.get_ident()))
        return SimpleNamespace(EndpointVolume=volumen)

    monkeypatch.setitem(sys.modules, "comtypes", comtypes)
    monkeypatch.setitem(sys.modules, "pycaw.pycaw", SimpleNamespace(AudioUtilities=SimpleNamespace(GetSpeakers=altavoces)))
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(pc._control_volumen()))
    hilo.start()
    hilo.join()
    assert resultado == [volumen]
    assert [paso for paso, _ in pasos] == ["com", "altavoces"]
    assert pasos[0][1] == pasos[1][1] == hilo.ident


def test_fijar_volumen_sin_pycaw(monkeypatch):
    def sin_pycaw():
        raise ImportError

    monkeypatch.setattr(pc, "_control_volumen", sin_pycaw)
    assert "Windows" in pc.fijar_volumen(50)


def test_abrir_youtube_portada_y_busqueda(navegador):
    pc.abrir_youtube()
    pc.abrir_youtube("lofi hip hop")
    assert navegador == [
        "https://www.youtube.com",
        "https://www.youtube.com/results?search_query=lofi+hip+hop",
    ]


def test_reproducir_abre_primer_video(monkeypatch, navegador):
    html = 'algo "videoId":"dQw4w9WgXcQ" y "videoId":"otroVideo12"'
    respuesta = SimpleNamespace(text=html, raise_for_status=lambda: None)
    monkeypatch.setattr(pc.requests, "get", lambda url, timeout: respuesta)
    assert pc.reproducir_en_youtube("rick astley") == "Reproduciendo rick astley en YouTube."
    assert navegador == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]


def test_reproducir_sin_red_abre_resultados(monkeypatch, navegador):
    def sin_red(url, timeout):
        raise requests.ConnectionError

    monkeypatch.setattr(pc.requests, "get", sin_red)
    pc.reproducir_en_youtube("queen")
    assert navegador == ["https://www.youtube.com/results?search_query=queen"]


def test_reproducir_sin_videos_abre_resultados(monkeypatch, navegador):
    respuesta = SimpleNamespace(text="<html></html>", raise_for_status=lambda: None)
    monkeypatch.setattr(pc.requests, "get", lambda url, timeout: respuesta)
    pc.reproducir_en_youtube("nada")
    assert navegador == ["https://www.youtube.com/results?search_query=nada"]


@pytest.mark.parametrize(
    "url, esperada",
    [
        ("google.com", "https://google.com"),
        ("http://ejemplo.org", "http://ejemplo.org"),
        (" https://youtube.com ", "https://youtube.com"),
    ],
)
def test_abrir_web_agrega_https(navegador, url, esperada):
    pc.abrir_web(url)
    assert navegador == [esperada]

