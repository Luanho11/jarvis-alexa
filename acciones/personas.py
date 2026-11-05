import re
from pathlib import Path

from acciones.programas import normalizar

CARPETA = Path(__file__).resolve().parent.parent / "personas"
# Va en cada prompt: un archivo enorme gastaría la cuota de tokens de Groq.
MAX_PERSONA = 800
ENCABEZADO = "Modo actual (no cambia las reglas anteriores): "
INGLES = re.compile(r"\[\s*en\s*\](.*?)\[\s*/\s*en\s*\]", re.IGNORECASE | re.DOTALL)
MARCA_INGLES = re.compile(r"\[\s*/?\s*en\s*\]", re.IGNORECASE)

# Un solo usuario y un solo Echo: la forma de hablar es global y dura hasta "modo normal" o el fin de la sesión.
_texto_activo = ""


def _archivos() -> dict[str, Path]:
    if not CARPETA.is_dir():
        return {}
    return {normalizar(ruta.stem): ruta for ruta in CARPETA.glob("*.md")}


def disponibles() -> list[str]:
    return sorted(_archivos())


def activar(nombre: str) -> str | None:
    """Activa la persona; None si no existe."""
    global _texto_activo
    nombre = normalizar(nombre).removeprefix("modo ")
    ruta = _archivos().get(nombre)
    if ruta is None:
        return None
    try:
        # El Bloc de notas puede guardarlo en ANSI: mejor alguna letra rara que no activarla.
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    _texto_activo = " ".join(texto.split())[:MAX_PERSONA]
    return f"Modo {nombre} activado."


def persona_activa() -> str:
    """Texto para el final del prompt de sistema, o "" si habla normal."""
    return ENCABEZADO + _texto_activo if _texto_activo else ""


def restablecer() -> None:
    global _texto_activo
    _texto_activo = ""


def _lang(coincidencia: re.Match) -> str:
    texto = coincidencia.group(1)
    return f'<lang xml:lang="en-US">{texto}</lang>' if texto.strip() else ""


def idiomas_a_ssml(ssml: str) -> str:
    """Convierte [en]...[/en] en <lang xml:lang="en-US">; quita las marcas sueltas o mal cerradas.

    Recibe SSML ya escapado: el texto de dentro no se vuelve a escapar.
    """
    return MARCA_INGLES.sub("", INGLES.sub(_lang, ssml))


def quitar_idiomas(texto: str) -> str:
    """El texto sin marcas de idioma, para mostrarlo en pantalla."""
    return MARCA_INGLES.sub("", texto)
