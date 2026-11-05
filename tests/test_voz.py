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


def test_partir_deja_entera_una_respuesta_normal():
    texto = "Claro. " * 40
    assert voz.partir(texto) == (texto.strip(), "")


def test_partir_corta_al_final_de_una_frase_sin_perder_nada():
    frases = [f"Esta es la frase {i} de la explicación." for i in range(1, 15)]
    dicho, resto = voz.partir(" ".join(frases))
    assert dicho.endswith(".") and resto[0].isupper()
    assert len(dicho.split()) <= voz.PALABRAS_POR_TURNO
    assert f"{dicho} {resto}" == " ".join(frases)


def test_partir_una_frase_enorme_corta_en_una_coma_o_entre_palabras():
    con_comas = ", ".join(f"punto {i} importante" for i in range(40)) + "."
    dicho, resto = voz.partir(con_comas)
    assert dicho.endswith(",") and f"{dicho} {resto}" == con_comas
    sin_pausas = " ".join(f"palabra{i}" for i in range(100))
    dicho, resto = voz.partir(sin_pausas)
    assert len(dicho.split()) == voz.PALABRAS_POR_TURNO and f"{dicho} {resto}" == sin_pausas


def test_partir_no_corta_dentro_de_una_interjeccion():
    texto = " ".join(["uno"] * 54) + " {ay ay ay} " + " ".join(["dos"] * 30)
    dicho, _ = voz.partir(texto)
    assert dicho.count("{") == dicho.count("}")


def test_frases_en_ingles_con_su_voz_y_limpias_en_pantalla():
    ssml = voz.a_ssml("Se dice [en]good morning[/en], ¿vale?")
    assert '<lang xml:lang="en-US">good morning</lang>' in ssml
    assert es_ssml_valido(ssml)
    assert voz.texto_plano("Se dice [en]good morning[/en].") == "Se dice good morning."


def test_marca_de_idioma_suelta_no_rompe_el_ssml():
    ssml = voz.a_ssml("hola [en]sin cerrar & más")
    assert "[en]" not in ssml and es_ssml_valido(ssml)
