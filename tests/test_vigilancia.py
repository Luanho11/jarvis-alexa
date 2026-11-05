import threading
from types import SimpleNamespace

import pytest

from acciones import vigilancia


@pytest.fixture
def entorno(monkeypatch):
    eventos = []
    terminado = threading.Event()
    preguntas = []

    def emitir(tipo, texto=""):
        eventos.append((tipo, texto))
        if tipo == "aviso":
            terminado.set()

    def mirar(instruccion):
        preguntas.append(instruccion)
        return f"comentario {len(preguntas)}"

    monkeypatch.setattr(vigilancia.config, "GEMINI_API_KEY", "clave")
    monkeypatch.setattr(vigilancia.vision, "mirar_pantalla", mirar)
    monkeypatch.setattr(vigilancia.panel, "emitir", emitir)
    monkeypatch.setattr(vigilancia.panel, "mostrar", lambda: None)
    monkeypatch.setattr(vigilancia.panel, "ocultar_luego", lambda: None)
    monkeypatch.setattr(vigilancia, "INTERVALO_MINIMO", 0)
    yield eventos, terminado, preguntas
    vigilancia.dejar_de_vigilar()


def reloj_que_avanza(monkeypatch, segundos_por_llamada):
    actual = [0.0]

    def monotonic():
        actual[0] += segundos_por_llamada
        return actual[0]

    monkeypatch.setattr(vigilancia, "time", SimpleNamespace(monotonic=monotonic))


def test_comenta_en_el_hud_y_se_detiene_sola_al_acabar_el_tiempo(entorno, monkeypatch):
    eventos, terminado, preguntas = entorno
    reloj_que_avanza(monkeypatch, 25)
    respuesta = vigilancia.vigilar_pantalla(minutos=1, intervalo=0)
    assert respuesta.startswith("Vigilo la pantalla 1 minuto")
    assert terminado.wait(2)
    assert eventos[0] == ("comentario", "comentario 1")
    assert eventos[-1] == ("aviso", "Terminé de vigilar la pantalla.")
    assert 1 <= len(preguntas) <= 3
    assert vigilancia.dejar_de_vigilar() == "No estaba vigilando la pantalla."


def test_dejar_de_vigilar_corta_el_hilo(entorno):
    _, terminado, preguntas = entorno
    vigilancia.vigilar_pantalla(minutos=5, intervalo=0)
    assert vigilancia.dejar_de_vigilar() == "Dejo de vigilar la pantalla."
    cuenta = len(preguntas)
    assert not terminado.wait(0.2)
    assert len(preguntas) <= cuenta + 1


def test_en_voz_avisa_por_el_pc_pero_no_en_el_echo(entorno, monkeypatch):
    dichos = []
    hablado = threading.Event()

    def avisar(texto, en_echo=True):
        dichos.append((texto, en_echo))
        hablado.set()

    monkeypatch.setattr(vigilancia.recordatorios, "avisar", avisar)
    vigilancia.vigilar_pantalla(minutos=5, intervalo=0, en_voz=True)
    assert hablado.wait(2)
    assert dichos[0] == ("comentario 1", False)


def test_respeta_el_intervalo_minimo_de_gemini(entorno, monkeypatch):
    monkeypatch.setattr(vigilancia, "INTERVALO_MINIMO", 15)
    assert "cada 15 segundos" in vigilancia.vigilar_pantalla(minutos=2, intervalo=3)


def test_no_vigila_mas_de_media_hora_para_no_agotar_la_cuota_diaria(entorno):
    assert vigilancia.vigilar_pantalla(minutos=120).startswith("Vigilo la pantalla 30 minutos")


def test_sin_minutos_o_sin_clave_no_arranca(entorno, monkeypatch):
    assert vigilancia.vigilar_pantalla(minutos=0) == "Dime cuántos minutos vigilo la pantalla."
    monkeypatch.setattr(vigilancia.config, "GEMINI_API_KEY", "")
    assert vigilancia.vigilar_pantalla() == "Para vigilar la pantalla necesito la clave de Gemini."


def test_un_fallo_inesperado_termina_la_vigilancia(entorno, monkeypatch):
    def rota(instruccion):
        raise RuntimeError("captura rota")

    monkeypatch.setattr(vigilancia.vision, "mirar_pantalla", rota)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0)
    for _ in range(50):
        if not vigilancia.vigilando():
            break
        threading.Event().wait(0.02)
    assert not vigilancia.vigilando()


def respuestas_fijas(monkeypatch, respuestas):
    preguntas = []
    pendientes = list(respuestas)

    def mirar(instruccion):
        preguntas.append(instruccion)
        respuesta = pendientes.pop(0) if pendientes else "NADA"
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(vigilancia.vision, "mirar_pantalla", mirar)
    return preguntas


def comentarios(eventos):
    return [texto for tipo, texto in eventos if tipo == "comentario"]


def test_el_objetivo_personaliza_la_pregunta(entorno, monkeypatch):
    eventos, terminado, _ = entorno
    preguntas = respuestas_fijas(monkeypatch, ["Cúbrete detrás del muro."])
    reloj_que_avanza(monkeypatch, 25)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0, objetivo="dar consejos tácticos breves del juego")
    assert terminado.wait(2)
    assert "Tu tarea: dar consejos tácticos breves del juego." in preguntas[0]
    assert comentarios(eventos) == ["Cúbrete detrás del muro."]


def test_sin_objetivo_comenta_lo_que_pasa(entorno, monkeypatch):
    _, terminado, preguntas = entorno
    reloj_que_avanza(monkeypatch, 40)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0, objetivo="   ")
    assert terminado.wait(2)
    assert f"Tu tarea: {vigilancia.OBJETIVO}." in preguntas[0]


def test_se_calla_si_no_hay_nada_util_ni_nuevo(entorno, monkeypatch):
    eventos, terminado, _ = entorno
    respuestas = ["NADA", "Usa el escudo.", " nada. ", "Usa el escudo.", "", "Recarga ya."]
    respuestas_fijas(monkeypatch, respuestas)
    reloj_que_avanza(monkeypatch, 5)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0)
    assert terminado.wait(2)
    assert comentarios(eventos) == ["Usa el escudo.", "Recarga ya."]


def test_recuerda_los_ultimos_tres_comentarios_para_no_repetirse(entorno, monkeypatch):
    _, terminado, _ = entorno
    preguntas = respuestas_fijas(monkeypatch, ["uno", "dos", "tres", "cuatro"])
    reloj_que_avanza(monkeypatch, 10)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0)
    assert terminado.wait(2)
    assert "Ya dijiste" not in preguntas[0]
    assert preguntas[4].endswith("no lo repitas: dos | tres | cuatro")


def test_un_fallo_de_gemini_se_avisa_una_vez_y_sigue_mirando(entorno, monkeypatch):
    eventos, terminado, _ = entorno
    cuota = vigilancia.vision.SinVision("No pude analizar la pantalla ahora.")
    respuestas_fijas(monkeypatch, [cuota, cuota, "Ya va bien.", cuota])
    reloj_que_avanza(monkeypatch, 10)
    vigilancia.vigilar_pantalla(minutos=1, intervalo=0)
    assert terminado.wait(2)
    esperado = ["No pude analizar la pantalla ahora.", "Ya va bien.", "No pude analizar la pantalla ahora."]
    assert comentarios(eventos) == esperado
