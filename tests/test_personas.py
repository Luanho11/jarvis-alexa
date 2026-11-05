import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import pytest

from acciones import personas

INCLUIDAS = ["cocinero", "entrenador", "entrevistador", "profesor", "traductor", "xara"]


@pytest.fixture(autouse=True)
def normal():
    yield
    personas.restablecer()


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(personas, "CARPETA", tmp_path)
    return tmp_path


def _etiquetas(ssml: str) -> list[str]:
    return [elemento.tag for elemento in ET.fromstring(f"<speak>{ssml}</speak>").iter()]


def test_personas_incluidas_son_cortas():
    assert personas.disponibles() == INCLUIDAS
    for nombre in INCLUIDAS:
        texto = (personas.CARPETA / f"{nombre}.md").read_text(encoding="utf-8")
        assert 2 <= len(texto.strip().splitlines()) <= 6
        assert len(texto) <= personas.MAX_PERSONA


def test_el_traductor_pide_las_marcas_de_ingles():
    personas.activar("traductor")
    assert "[en]" in personas.persona_activa() and "[/en]" in personas.persona_activa()


@pytest.mark.parametrize("pedido", ["profesor", "Modo Profesor", "  PROFESÓR "])
def test_activar_profesor(pedido):
    assert personas.activar(pedido) == "Modo profesor activado."
    assert personas.persona_activa().startswith(personas.ENCABEZADO + "Eres un profesor paciente.")


def test_nombre_con_tildes_y_espacios(carpeta):
    (carpeta / "Traductor Inglés.md").write_text("Traduce.", encoding="utf-8")
    assert personas.disponibles() == ["traductor ingles"]
    assert personas.activar("traductor inglés") == "Modo traductor ingles activado."


def test_persona_inexistente(carpeta):
    assert personas.activar("pirata") is None
    assert personas.persona_activa() == ""


def test_sin_carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(personas, "CARPETA", tmp_path / "no existe")
    assert personas.disponibles() == []
    assert personas.activar("profesor") is None


def test_restablecer(carpeta):
    (carpeta / "pirata.md").write_text("Habla como pirata.", encoding="utf-8")
    personas.activar("pirata")
    assert personas.persona_activa() == personas.ENCABEZADO + "Habla como pirata."
    personas.restablecer()
    assert personas.persona_activa() == ""


def test_persona_larga_se_recorta(carpeta):
    (carpeta / "larga.md").write_text("palabra " * 1000, encoding="utf-8")
    personas.activar("larga")
    assert len(personas.persona_activa()) == len(personas.ENCABEZADO) + personas.MAX_PERSONA


def test_persona_en_ansi_y_con_saltos(carpeta):
    (carpeta / "abuela.md").write_bytes("Eres cariñosa.\r\n\r\nUsas refranes.".encode("cp1252"))
    personas.activar("abuela")
    assert personas.persona_activa().startswith(personas.ENCABEZADO + "Eres cari")
    assert personas.persona_activa().endswith(" Usas refranes.")


def test_ingles_a_ssml_valido_y_escapado():
    ssml = personas.idiomas_a_ssml(escape("Se dice: [en]Hello & bye <3[/en]."))
    assert ssml == 'Se dice: <lang xml:lang="en-US">Hello &amp; bye &lt;3</lang>.'
    assert _etiquetas(ssml) == ["speak", "lang"]


def test_varios_tramos_mayusculas_y_saltos_de_linea():
    ssml = personas.idiomas_a_ssml("[EN]Good morning[/EN] y [ en ]see\nyou[ / en ]")
    assert ssml == '<lang xml:lang="en-US">Good morning</lang> y <lang xml:lang="en-US">see\nyou</lang>'
    assert _etiquetas(ssml) == ["speak", "lang", "lang"]


@pytest.mark.parametrize(
    "texto, plano",
    [
        ("[en]Hello", "Hello"),
        ("Hello[/en]", "Hello"),
        ("[/en]Hello[en]", "Hello"),
        ("[en][/en]vacío", "vacío"),
        ("[en]   [/en]", ""),
    ],
)
def test_marcas_rotas_o_vacias_quedan_en_texto_plano(texto, plano):
    assert personas.idiomas_a_ssml(texto) == plano
    assert _etiquetas(personas.idiomas_a_ssml(texto)) == ["speak"]


def test_marcas_anidadas_no_rompen_el_xml():
    ssml = personas.idiomas_a_ssml("[en]one [en]two[/en] three[/en]")
    assert ssml == '<lang xml:lang="en-US">one two</lang> three'
    assert _etiquetas(ssml) == ["speak", "lang"]


def test_una_etiqueta_inyectada_no_sale_del_texto():
    ssml = personas.idiomas_a_ssml(escape('[en]</lang><audio src="https://x"/>[/en]'))
    assert _etiquetas(ssml) == ["speak", "lang"]


def test_convive_con_pausas_e_interjecciones():
    ssml = personas.idiomas_a_ssml('[en]Wait<break time="400ms"/>ok[/en] <say-as interpret-as="interjection">ajá</say-as>,')
    assert _etiquetas(ssml) == ["speak", "lang", "break", "say-as"]


def test_quitar_idiomas_para_la_pantalla():
    assert personas.quitar_idiomas("Di [en]Thank you[/en] así") == "Di Thank you así"
