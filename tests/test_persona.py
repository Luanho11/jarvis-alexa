from datetime import datetime

import pytest

import cerebro
import servidor


@pytest.fixture
def persona(tmp_path, monkeypatch):
    propia = tmp_path / "persona.md"
    monkeypatch.setattr(cerebro, "PERSONA", propia)
    return propia


def test_sin_persona_propia_usa_la_de_ejemplo(persona):
    assert cerebro.leer_persona() == cerebro.PERSONA_EJEMPLO.read_text(encoding="utf-8").strip()
    assert "Jarvis" in cerebro.leer_persona()


def test_persona_propia_va_en_el_prompt(persona):
    persona.write_text("Eres Viernes, seca y directa.\n", encoding="utf-8")
    texto = cerebro.prompt_sistema()
    assert texto.startswith("Eres Viernes, seca y directa.\n")
    assert "una a tres frases cortas" in texto


def test_prompt_explica_las_interjecciones_y_como_guardar_el_nombre(persona):
    texto = cerebro.prompt_sistema()
    assert "{bravo}" in texto and "'...'" in texto
    assert "'Se llama <nombre>'" in texto


@pytest.mark.parametrize(
    "hora, inicio",
    [(7, "Buenos días"), (11, "Buenos días"), (12, "Buenas tardes"), (19, "Buenas tardes"), (20, "Buenas noches"), (3, "Buenas noches")],
)
def test_saludo_segun_la_hora(hora, inicio):
    texto = servidor.saludo(datetime(2026, 11, 5, hora), "")
    assert texto.startswith(f"{inicio}. ")
    assert texto.split(". ", 1)[1] in servidor.INVITACIONES


def test_saludo_con_nombre():
    assert servidor.saludo(datetime(2026, 11, 5, 9), "Ana").startswith("Buenos días, Ana. ")


def test_las_repreguntas_varian_y_no_son_algo_mas():
    assert len(set(servidor.REPREGUNTAS)) > 2
    assert "¿Algo más?" not in servidor.REPREGUNTAS
    assert servidor.repregunta() in servidor.REPREGUNTAS


def test_persona_guardada_en_ansi_no_rompe_el_prompt(persona):
    persona.write_bytes("Eres Jarvis, simpático.".encode("cp1252"))
    assert cerebro.leer_persona().startswith("Eres Jarvis, simp")
