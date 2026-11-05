import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

# Speechcons que existen igual en es-ES, es-MX y es-US (referencia de speechcons de Alexa):
# así suenan bien sea cual sea el idioma del Echo. Otra palabra entre llaves se lee normal.
INTERJECCIONES = (
    "ajá", "ay", "ay ay ay", "auch", "bravo", "buena suerte", "buen viaje",
    "buenas noches", "buenas tardes", "abracadabra", "bla bla bla",
)
INTERJECCION = re.compile(r"\{([^{}]*)\}([,.;:!?]?)")
PAUSA = re.compile(r"(?:\.{3}|…)+")
PAUSA_SSML = '<break time="400ms"/>'
# Alexa no admite más de 10 s de silencio por respuesta.
MAX_PAUSAS = 20
ETIQUETAS = {"speak", "say-as", "break"}
# Alexa rechaza la respuesta entera si el SSML pasa de 8000 caracteres, contando <speak></speak>.
MAX_SSML = 8000 - len("<speak></speak>")
# Caracteres de control y emojis: Alexa rechaza la respuesta si no puede pronunciarlos.
NO_PRONUNCIABLE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f️☀-➿\U0001f000-\U0001faff]")


def texto_plano(texto: str) -> str:
    """El texto sin marcas de voz, para mostrarlo en pantalla."""
    return INTERJECCION.sub(r"\1\2", NO_PRONUNCIABLE.sub("", texto))


def _interjeccion(coincidencia: re.Match) -> str:
    palabra = coincidencia.group(1).strip(" ¡!¿?").lower()
    if palabra not in INTERJECCIONES:
        return coincidencia.group(1) + coincidencia.group(2)
    # Alexa pide una pausa tras cada speechcon para pronunciarlo con expresión.
    return f'<say-as interpret-as="interjection">{palabra}</say-as>{coincidencia.group(2) or ","}'


def _es_valido(ssml: str) -> bool:
    try:
        raiz = ET.fromstring(f"<speak>{ssml}</speak>")
    except ET.ParseError:
        return False
    etiquetas = [elemento.tag for elemento in raiz.iter()]
    return set(etiquetas) <= ETIQUETAS and etiquetas.count("break") <= MAX_PAUSAS


def _convertir(texto: str) -> str:
    ssml = PAUSA.sub(PAUSA_SSML, escape(NO_PRONUNCIABLE.sub("", texto)))
    ssml = INTERJECCION.sub(_interjeccion, ssml)
    return ssml if _es_valido(ssml) else escape(texto_plano(texto))


def a_ssml(texto: str) -> str:
    """Contenido SSML (sin <speak>) para Alexa; si no fuera válido, el texto plano escapado."""
    ssml = _convertir(texto)
    largo = len(texto)
    while len(ssml) > MAX_SSML:
        largo = largo * MAX_SSML // len(ssml)
        ssml = _convertir(texto[:largo].rsplit(" ", 1)[0] + "...")
    return ssml
