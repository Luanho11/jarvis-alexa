import json
import re
from pathlib import Path

import pytest

MODELO = json.loads((Path(__file__).parent.parent / "skill" / "modelo_es.json").read_text(encoding="utf-8"))
IDIOMA = MODELO["interactionModel"]["languageModel"]
MUESTRAS = [muestra for intent in IDIOMA["intents"] for muestra in intent["samples"]]
VALORES = [valor["name"]["value"] for tipo in IDIOMA["types"] for valor in tipo["values"]]


def test_nombre_de_invocacion_valido():
    nombre = IDIOMA["invocationName"]
    assert re.fullmatch(r"[a-záéíóúüñ]+( [a-záéíóúüñ]+)+", nombre)
    assert not re.search(r"\b(alexa|echo|skill|app|amazon)\b", nombre)


def test_sin_duplicados_y_con_caracteres_admitidos():
    assert len(MUESTRAS) == len(set(MUESTRAS))
    assert len(VALORES) == len(set(VALORES))
    assert all(re.fullmatch(r"[a-záéíóúüñ' .{}]{1,200}", muestra) for muestra in MUESTRAS)
    assert all(re.fullmatch(r"[a-z0-9áéíóúüñ' .]{1,140}", valor) for valor in VALORES)


def test_comodin_con_frases_cortas_y_largas():
    # Alexa recorta el comodín a la longitud de los ejemplos que conoce: hacen falta de 1 a más de 15 palabras.
    palabras = {len(valor.split()) for valor in VALORES}
    assert {1, 2, 3, 5, 8, 12} <= palabras and max(palabras) >= 15


def test_fallback_poco_sensible():
    assert IDIOMA["modelConfiguration"]["fallbackIntentSensitivity"]["level"] == "LOW"
    assert "AMAZON.FallbackIntent" in [intent["name"] for intent in IDIOMA["intents"]]


@pytest.mark.parametrize("frase", ["cancela el apagado", "para la música", "y bien"])
def test_frases_que_no_deben_ir_a_los_intents_integrados(frase):
    assert frase in VALORES
