import json
import threading
from datetime import date, datetime

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


@pytest.fixture
def google_activo(monkeypatch):
    estado = {"eventos": [], "pedidos": [], "creados": []}

    def eventos_google(desde, hasta):
        estado["pedidos"].append((desde, hasta))
        return estado["eventos"]

    monkeypatch.setattr(agenda.google, "agenda_activa", lambda: True)
    monkeypatch.setattr(agenda.google, "eventos_google", eventos_google)
    monkeypatch.setattr(agenda.google, "crear_evento_en_segundo_plano", lambda titulo, momento: estado["creados"].append((titulo, momento)))
    return estado


def test_sin_google_no_lo_llama(monkeypatch):
    monkeypatch.setattr(agenda.google, "eventos_google", lambda *_: pytest.fail("llamó a Google"))
    monkeypatch.setattr(agenda.google, "crear_evento_en_segundo_plano", lambda *_: pytest.fail("llamó a Google"))
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    assert agenda.listar_eventos() == "Mañana a las 15:00: dentista."


def test_agregar_tambien_en_google(google_activo, archivo):
    assert agenda.agregar_evento("dentista", "2026-11-05T15:00") == "Listo, agendé dentista. Mañana a las 15:00."
    assert google_activo["creados"] == [("dentista", datetime(2026, 11, 5, 15, 0))]
    assert json.loads(archivo.read_text(encoding="utf-8")) == [{"titulo": "dentista", "fecha_hora": "2026-11-05T15:00"}]


def test_listar_une_google_sin_duplicados(google_activo):
    agenda.agregar_evento("Dentista", "2026-11-05T15:00")
    google_activo["eventos"] = [
        {"titulo": "dentista ", "fecha_hora": "2026-11-05T15:00"},
        {"titulo": "Cumpleaños de Ana", "fecha_hora": "2026-11-04T00:00", "todo_el_dia": True},
        {"titulo": "Fútbol", "fecha_hora": "2026-11-04T19:00"},
        {"titulo": "Fútbol", "fecha_hora": "2026-11-04T19:00"},
    ]
    assert agenda.listar_eventos() == (
        "Hoy: Cumpleaños de Ana. Hoy a las 19:00: Fútbol. Mañana a las 15:00: Dentista."
    )
    desde, hasta = google_activo["pedidos"][0]
    assert desde == datetime(2026, 11, 4, 9, 59) and (hasta - desde).days == agenda.DIAS_PROXIMOS_GOOGLE


def test_listar_proximos_con_google_respeta_el_maximo(google_activo):
    google_activo["eventos"] = [{"titulo": f"evento {n}", "fecha_hora": f"2026-11-1{n}T10:00"} for n in range(8)]
    assert agenda.listar_eventos().count(".") == agenda.MAX_PROXIMOS


def test_listar_un_dia_pide_ese_dia_a_google(google_activo):
    google_activo["eventos"] = [{"titulo": "Reunión", "fecha_hora": "2026-11-06T09:00"}]
    agenda.agregar_evento("Gimnasio", "2026-11-06T07:00")
    assert agenda.listar_eventos("2026-11-06") == "El 06/11 a las 07:00: Gimnasio. El 06/11 a las 09:00: Reunión."
    assert google_activo["pedidos"] == [(datetime(2026, 11, 6), datetime(2026, 11, 7))]
    assert [e["titulo"] for e in agenda.eventos_de(date(2026, 11, 6))] == ["Gimnasio", "Reunión"]


def test_google_caido_sigue_con_la_agenda_local(google_activo):
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    assert agenda.listar_eventos() == "Mañana a las 15:00: dentista."
    assert agenda.listar_eventos("2026-11-05") == "Mañana a las 15:00: dentista."


def test_eventos_de_un_dia_ordenados_y_sin_los_mal_escritos():
    agenda._guardar([
        {"titulo": "tarde", "fecha_hora": "2026-11-05T19:00"},
        {"titulo": "sin fecha"},
        {"titulo": "fecha rara", "fecha_hora": "mañana"},
        {"titulo": "con zona", "fecha_hora": "2026-11-05T08:00:00+01:00"},
        {"titulo": "otro día", "fecha_hora": "2026-11-06T09:00"},
    ])
    assert agenda.eventos_de(date(2026, 11, 5)) == [
        {"titulo": "con zona", "fecha_hora": "2026-11-05T08:00"},
        {"titulo": "tarde", "fecha_hora": "2026-11-05T19:00"},
    ]
