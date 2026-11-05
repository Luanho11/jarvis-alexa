import json
import threading
from datetime import datetime

import pytest

from acciones import agenda


@pytest.fixture(autouse=True)
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "agenda.json"
    monkeypatch.setenv("AGENDA_ARCHIVO", str(ruta))
    monkeypatch.setattr(agenda, "_ahora", lambda: datetime(2026, 11, 4, 10, 0))
    return ruta


def test_agregar_guarda_evento(archivo):
    assert agenda.agregar_evento("dentista", "2026-11-05T15:00") == (
        "Listo, agendé dentista. Mañana a las 15:00."
    )
    assert json.loads(archivo.read_text(encoding="utf-8")) == [
        {"titulo": "dentista", "fecha_hora": "2026-11-05T15:00"}
    ]


def test_agregar_rechaza_fecha_invalida(archivo):
    assert agenda.agregar_evento("cita", "el martes") == "No entendí la fecha del evento."
    assert not archivo.exists()


def test_listar_proximos_ordenados_sin_pasados():
    agenda.agregar_evento("reunión", "2026-11-12T10:00")
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    agenda.agregar_evento("ayer", "2026-11-03T09:00")
    agenda.agregar_evento("almuerzo", "2026-11-04T13:30")
    assert agenda.listar_eventos() == (
        "Hoy a las 13:30: almuerzo. Mañana a las 15:00: dentista. El 12/11 a las 10:00: reunión."
    )


def test_listar_por_fecha():
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    agenda.agregar_evento("gimnasio", "2026-11-05T07:00")
    agenda.agregar_evento("otro", "2026-11-06T07:00")
    assert agenda.listar_eventos("2026-11-05") == (
        "Mañana a las 07:00: gimnasio. Mañana a las 15:00: dentista."
    )


def test_listar_vacio_y_fecha_invalida():
    assert agenda.listar_eventos() == "No tienes eventos próximos."
    assert agenda.listar_eventos("2026-12-25") == "No tienes eventos ese día."
    assert agenda.listar_eventos("navidad") == "No entendí la fecha."


def test_borrar_evento_sin_importar_mayusculas():
    agenda.agregar_evento("Dentista", "2026-11-05T15:00")
    assert agenda.borrar_evento("dentista") == "Borré dentista."
    assert agenda.listar_eventos() == "No tienes eventos próximos."


def test_borrar_evento_inexistente():
    assert agenda.borrar_evento("nada") == "No encontré ese evento."


def test_hilos_a_la_vez_no_pierden_eventos(archivo):
    def agendar(hilo):
        for numero in range(10):
            agenda.agregar_evento(f"evento {hilo}-{numero}", "2026-11-05T15:00")
            agenda.leer_eventos()

    hilos = [threading.Thread(target=agendar, args=(hilo,)) for hilo in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len(agenda.leer_eventos()) == 80
