import xml.etree.ElementTree as ET

import pytest

import voz


def es_ssml_valido(ssml):
    ET.fromstring(f"<speak>{ssml}</speak>")
    return True


def test_escapa_el_texto_normal():
    assert voz.a_ssml("Tom & Jerry <3") == "Tom &amp; Jerry &lt;3"


def test_convierte_interjecciones_conocidas():
    ssml = voz.a_ssml("{Bravo}, lo lograste.")
    assert ssml == '<say-as interpret-as="interjection">bravo</say-as>, lo lograste.'
    assert es_ssml_valido(ssml)


def test_interjeccion_sin_signo_lleva_pausa():
    ssml = voz.a_ssml("{¡ajá!} ya lo tengo")
    assert ssml.startswith('<say-as interpret-as="interjection">ajá</say-as>, ya')


def test_interjeccion_desconocida_se_lee_normal():
    assert voz.a_ssml("{órale}, vamos") == "órale, vamos"


def test_puntos_suspensivos_son_una_pausa():
    ssml = voz.a_ssml("Pues... no sé…")
    assert ssml == f"Pues{voz.PAUSA_SSML} no sé{voz.PAUSA_SSML}"
    assert es_ssml_valido(ssml)


def test_quita_emojis_y_caracteres_de_control():
    assert voz.a_ssml("Hecho 👍\x07") == "Hecho "


def test_demasiadas_pausas_se_envian_como_texto():
    texto = "a..." * (voz.MAX_PAUSAS + 1)
    assert voz.a_ssml(texto) == texto


def test_si_el_ssml_saliera_invalido_manda_texto_plano(monkeypatch):
    monkeypatch.setattr(voz, "PAUSA_SSML", "<break>")
    assert voz.a_ssml("{ay}... & ya") == "ay... &amp; ya"


@pytest.mark.parametrize("texto", ["<speak>hola</speak>", "{<b>}", "]]>", "{bravo} & {ay}... {x"])
def test_nunca_genera_ssml_invalido(texto):
    assert es_ssml_valido(voz.a_ssml(texto))


def test_texto_plano_quita_las_llaves():
    assert voz.texto_plano("{bravo}, ganaste 🎉") == "bravo, ganaste "


@pytest.mark.parametrize("texto", ["palabra & " * 2000, "{bravo}, sí. " * 700, "x" * 9000])
def test_respuestas_largas_se_cortan_bajo_el_limite_de_alexa(texto):
    ssml = voz.a_ssml(texto)
    assert len(f"<speak>{ssml}</speak>") <= 8000
    assert es_ssml_valido(ssml)
