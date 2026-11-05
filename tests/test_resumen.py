import time
from datetime import datetime

import pytest

import cerebro_profundo
from acciones import agenda, programadas, resumen


class FechaFija(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 5, 8, 0)


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENDA_ARCHIVO", str(tmp_path / "agenda.json"))
    monkeypatch.setenv("PROGRAMADAS_ARCHIVO", str(tmp_path / "programadas.json"))
    monkeypatch.setattr(resumen, "datetime", FechaFija)
    monkeypatch.setattr(cerebro_profundo, "_pendientes", [])
    monkeypatch.setattr(resumen.web, "pronostico_hoy", lambda: "En Monterrey 24 grados, máxima 29, mínima 18 y 10 % de lluvia.")
    monkeypatch.setattr(resumen.info, "titulares", lambda cantidad: ["Sube el dólar", "Gana el Cruz Azul", "Llueve en Lima"][:cantidad])


def test_resumen_con_todas_las_fuentes():
    agenda.agregar_evento("fútbol", "2026-11-05T19:00")
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    agenda.agregar_evento("mañana no", "2026-11-06T09:00")
    assert resumen.resumen_del_dia() == (
        "Hoy es jueves 5 de noviembre. En Monterrey 24 grados, máxima 29, mínima 18 y 10 % de lluvia. "
        "Tienes 2 citas: dentista a las 15:00 y fútbol a las 19:00. "
        "Titulares: Sube el dólar. Gana el Cruz Azul. Llueve en Lima."
    )


def test_sin_citas():
    assert "No tienes citas hoy." in resumen.resumen_del_dia()


def test_una_cita_y_tareas_programadas_de_hoy(monkeypatch):
    monkeypatch.setattr(programadas, "_ahora", FechaFija.now)
    agenda.agregar_evento("dentista", "2026-11-05T15:00")
    programadas.programar_tarea("tomar la pastilla", "20:00")
    texto = resumen.resumen_del_dia()
    assert "Tienes 1 cita: dentista a las 15:00." in texto
    assert "Programado para hoy: tomar la pastilla a las 20:00." in texto


def test_una_fuente_que_falla_no_impide_las_demas(monkeypatch):
    def sin_red():
        raise OSError("sin red")

    monkeypatch.setattr(resumen.web, "pronostico_hoy", sin_red)
    texto = resumen.resumen_del_dia()
    assert "grados" not in texto
    assert "No tienes citas hoy." in texto
    assert "Titulares: Sube el dólar" in texto


def test_agenda_rota_se_omite(tmp_path):
    (tmp_path / "agenda.json").write_text("{roto", encoding="utf-8")
    texto = resumen.resumen_del_dia()
    assert "citas" not in texto
    assert "grados" in texto


def test_una_fuente_lenta_se_omite_a_tiempo(monkeypatch):
    monkeypatch.setattr(resumen, "TIEMPO_LIMITE", 0.3)

    def lenta(cantidad):
        time.sleep(1.5)
        return ["tarde"]

    monkeypatch.setattr(resumen.info, "titulares", lenta)
    inicio = time.monotonic()
    texto = resumen.resumen_del_dia()
    assert time.monotonic() - inicio < 0.8
    assert "Titulares" not in texto
    assert "grados" in texto


def test_encargos_terminados_no_se_consumen():
    cerebro_profundo._pendientes.extend(["Comparé las teles.", "Busqué vuelos."])
    assert "Terminé 2 encargos; pregúntame por ellos." in resumen.resumen_del_dia()
    assert cerebro_profundo.resultados_pendientes() == ["Comparé las teles.", "Busqué vuelos."]
    cerebro_profundo._pendientes.append("Uno.")
    assert "Terminé 1 encargo; pregúntame por él." in resumen.resumen_del_dia()


def test_sin_titulares_no_dice_titulares(monkeypatch):
    monkeypatch.setattr(resumen.info, "titulares", lambda cantidad: [])
    assert "Titulares" not in resumen.resumen_del_dia()


def test_no_pasa_de_600_caracteres(monkeypatch):
    monkeypatch.setattr(resumen.info, "titulares", lambda cantidad: ["Un titular larguísimo " * 20] * cantidad)
    for hora in range(8, 14):
        agenda.agregar_evento(f"reunión importante número {hora}", f"2026-11-05T{hora + 6}:00")
    texto = resumen.resumen_del_dia()
    assert len(texto) <= resumen.MAX_LARGO
    assert texto.endswith("...")
    assert "Tienes 6 citas" in texto
