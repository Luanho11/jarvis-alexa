"""Arranca servidor.py de verdad, como iniciar.bat, y le habla por HTTP."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

PROYECTO = Path(__file__).parent.parent
URL = "http://127.0.0.1:5000"


def puerto_ocupado() -> bool:
    with socket.socket() as conexion:
        return conexion.connect_ex(("127.0.0.1", 5000)) == 0


@pytest.fixture
def servidor(tmp_path):
    if puerto_ocupado():
        pytest.skip("el puerto 5000 está ocupado (¿Jarvis abierto?)")
    entorno = {
        **os.environ,
        "ALEXA_SKILL_ID": "amzn1.ask.skill.prueba",
        "GROQ_API_KEY": "clave-de-prueba",
        "HUD_ACTIVO": "no",
        "AVISOS_EN_ECHO": "no",
        "AGENDA_ARCHIVO": str(tmp_path / "agenda.json"),
        "MEMORIA_ARCHIVO": str(tmp_path / "memoria.json"),
    }
    proceso = subprocess.Popen([sys.executable, "servidor.py"], cwd=PROYECTO, env=entorno)
    sesion = requests.Session()
    # Sin esto, un proxy del sistema podría desviar las peticiones a 127.0.0.1.
    sesion.trust_env = False
    limite = time.monotonic() + 30
    while time.monotonic() < limite and proceso.poll() is None:
        try:
            sesion.get(f"{URL}/hud", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.3)
    yield sesion, proceso
    proceso.terminate()
    proceso.wait(timeout=10)


def test_servidor_arranca_sirve_el_hud_y_exige_la_firma_de_alexa(servidor):
    sesion, proceso = servidor
    assert proceso.poll() is None, "servidor.py se cerró al arrancar"
    hud = sesion.get(f"{URL}/hud", timeout=5)
    assert hud.status_code == 200 and "Jarvis HUD" in hud.text
    assert sesion.get(f"{URL}/hud/hud.js", timeout=5).status_code == 200
    peticion = {"version": "1.0", "request": {"type": "LaunchRequest", "requestId": "1", "timestamp": "2026-01-01T00:00:00Z"}}
    assert sesion.post(f"{URL}/alexa", json=peticion, timeout=5).status_code == 400
    assert sesion.get(f"{URL}/hud", headers={"X-Forwarded-For": "1.2.3.4"}, timeout=5).status_code == 403
