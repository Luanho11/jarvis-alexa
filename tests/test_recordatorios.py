import base64
import subprocess
import sys
from datetime import datetime

import pytest

from acciones import agenda, recordatorios


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENDA_ARCHIVO", str(tmp_path / "agenda.json"))
    monkeypatch.setattr(recordatorios, "avisados", set())


@pytest.fixture(autouse=True)
def echo(monkeypatch):
    dichos = []
    monkeypatch.setattr(recordatorios.config, "AVISOS_EN_ECHO", True)
    monkeypatch.setattr(recordatorios.echo, "decir_en_echo", dichos.append)
    monkeypatch.setattr(recordatorios.subprocess, "Popen", lambda *_, **__: None)
    return dichos


@pytest.fixture
def avisos(monkeypatch):
    dichos = []
    monkeypatch.setattr(recordatorios, "avisar", dichos.append)
    return dichos


def test_avisa_al_llegar_la_hora_una_sola_vez(avisos):
    agenda.agregar_evento("dentista", "2026-11-04T15:00")
    recordatorios.revisar(datetime(2026, 11, 4, 14, 59))
    assert avisos == []
    recordatorios.revisar(datetime(2026, 11, 4, 15, 0, 20))
    recordatorios.revisar(datetime(2026, 11, 4, 15, 0, 50))
    assert avisos == ["Recordatorio: dentista"]


def test_evento_con_zona_horaria_se_guarda_en_hora_local(avisos):
    agenda.agregar_evento("reunión", "2026-11-04T15:00:00Z")
    recordatorios.revisar(datetime(2026, 11, 4, 15, 0, 30))
    assert avisos == ["Recordatorio: reunión"]


def test_un_evento_mal_escrito_a_mano_no_bloquea_los_demas(avisos):
    agenda._guardar([
        {"titulo": "sin fecha"},
        {"titulo": "fecha rara", "fecha_hora": "mañana"},
        {"titulo": "con zona", "fecha_hora": "2026-11-04T15:00:00+01:00"},
        {"titulo": "dentista", "fecha_hora": "2026-11-04T15:00"},
    ])
    recordatorios.revisar(datetime(2026, 11, 4, 15, 0, 30))
    assert avisos == ["Recordatorio: con zona", "Recordatorio: dentista"]


def test_no_avisa_eventos_viejos(avisos):
    agenda.agregar_evento("ayer", "2026-11-03T09:00")
    recordatorios.revisar(datetime(2026, 11, 4, 10, 0))
    assert avisos == []


def test_temporizador(monkeypatch):
    creados = []

    class TimerFalso:
        def __init__(self, segundos, funcion, args):
            creados.append((segundos, funcion, args))

        def start(self):
            pass

    monkeypatch.setattr(recordatorios.threading, "Timer", TimerFalso)
    assert recordatorios.poner_temporizador(5, "la pasta") == "Temporizador de 5 minutos en marcha."
    assert recordatorios.poner_temporizador(1) == "Temporizador de 1 minuto en marcha."
    assert creados == [
        (300, recordatorios.avisar, ["Se acabó el tiempo: la pasta"]),
        (60, recordatorios.avisar, ["Se acabó el tiempo."]),
    ]


def test_temporizador_sin_minutos():
    assert recordatorios.poner_temporizador(0) == "Dime cuántos minutos."


def script_lanzado(orden):
    assert orden[:2] == ["powershell", "-NoProfile"] and orden[-2] == "-EncodedCommand"
    return base64.b64decode(orden[-1]).decode("utf-16-le")


def test_avisar_escapa_comillas_para_powershell(monkeypatch):
    lanzados = []
    monkeypatch.setattr(recordatorios.subprocess, "Popen", lambda args, **_: lanzados.append(args))
    recordatorios.avisar("Recordatorio: cumple de O'Brien y de D’Angelo, \"el de $casa\"")
    script = script_lanzado(lanzados[0])
    assert "'Recordatorio: cumple de O''Brien y de D''Angelo, \"el de $casa\"'" in script


@pytest.mark.skipif(sys.platform != "win32", reason="necesita PowerShell de Windows")
def test_powershell_recibe_el_texto_intacto(monkeypatch):
    lanzados = []
    monkeypatch.setattr(recordatorios, "SCRIPT_AVISO", "[Console]::OutputEncoding = [Text.Encoding]::UTF8\nWrite-Output '{texto}'")
    monkeypatch.setattr(recordatorios.subprocess, "Popen", lambda args, **_: lanzados.append(args))
    texto = "Cita con O'Brien: \"café\" a las 5 $(calc) `n ñandú"
    recordatorios.avisar(texto, en_echo=False)
    salida = subprocess.run(lanzados[0], capture_output=True, timeout=60)
    assert salida.stdout.decode("utf-8").strip() == texto


def test_avisar_sin_powershell_no_falla(monkeypatch, capsys):
    def sin_powershell(args, **_):
        raise FileNotFoundError

    monkeypatch.setattr(recordatorios.subprocess, "Popen", sin_powershell)
    recordatorios.avisar("hola")
    assert "hola" in capsys.readouterr().out


def test_avisar_tambien_lo_dice_en_el_echo(echo):
    recordatorios.avisar("Recordatorio: dentista")
    assert echo == ["Recordatorio: dentista"]


def test_avisar_sin_echo(echo, monkeypatch):
    recordatorios.avisar("comentario de la pantalla", en_echo=False)
    monkeypatch.setattr(recordatorios.config, "AVISOS_EN_ECHO", False)
    recordatorios.avisar("Recordatorio: dentista")
    assert echo == []


def test_el_vigilante_revisa_agenda_y_programadas_aunque_fallen(monkeypatch):
    from acciones import programadas

    revisadas = []

    def falla(ahora):
        revisadas.append("agenda")
        raise ValueError("agenda.json roto")

    class Parar(Exception):
        pass

    def parar(segundos):
        raise Parar

    monkeypatch.setattr(recordatorios, "revisar", falla)
    monkeypatch.setattr(programadas, "revisar", lambda ahora: revisadas.append("programadas"))
    monkeypatch.setattr(recordatorios.time, "sleep", parar)
    with pytest.raises(Parar):
        recordatorios._vigilar()
    assert revisadas == ["agenda", "programadas"]
