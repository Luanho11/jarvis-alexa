import importlib.util
import threading
import time
from pathlib import Path

import pytest

import config
import herramientas
import panel
import rapido

RUTA_SCRIPT = Path(__file__).parent.parent / "scripts" / "medir_latencia.py"


@pytest.fixture
def script(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(tmp_path / "memoria.json"))
    # El script cambia estos valores globales: monkeypatch los deja como estaban al terminar.
    monkeypatch.setattr(herramientas, "ejecutar", herramientas.ejecutar)
    monkeypatch.setattr(config, "HUD_ACTIVO", config.HUD_ACTIVO)
    especificacion = importlib.util.spec_from_file_location("medir_latencia", RUTA_SCRIPT)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def test_script_mide_los_tres_escenarios_con_el_llm_falso(script, capsys):
    script.main(["-n", "3", "--falso"])
    salida = capsys.readouterr().out
    assert salida.count("mediana") == 3
    assert "Orden directa (ruta rápida)" in salida and "llamadas al LLM por petición 0.0" in salida
    assert salida.count("llamadas al LLM por petición 1.0") == 2


def test_percentil(script):
    assert script.percentil([5, 1, 3, 2, 4], 50) == 3
    assert script.percentil(list(range(1, 11)), 90) == 9
    assert script.percentil([7], 90) == 7


def test_el_servidor_con_llm_instantaneo_responde_en_milisegundos(script):
    resultado = script.medir(20, 0, True)
    medianas = [float(linea.split("mediana ")[1].split(" ms")[0]) for linea in resultado.splitlines() if "mediana" in linea]
    assert len(medianas) == 3 and max(medianas) < 100


def test_la_ruta_rapida_decide_en_menos_de_un_milisegundo():
    frases = ["sube el volumen", "pon música de bad bunny", "cuéntame la historia de roma en pocas palabras"]
    inicio = time.perf_counter()
    for _ in range(100):
        for frase in frases:
            rapido.interpretar(frase)
    assert (time.perf_counter() - inicio) / 300 < 0.001


def test_mostrar_el_hud_no_espera_a_que_abra_edge(monkeypatch):
    soltar = threading.Event()
    monkeypatch.setattr(config, "HUD_ACTIVO", True)
    monkeypatch.setattr(panel, "_traer_al_frente", lambda: soltar.wait(5))
    inicio = time.perf_counter()
    panel.mostrar()
    assert time.perf_counter() - inicio < 0.1
    soltar.set()
