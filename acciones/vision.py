import base64
import io

import openai

import config

# Igual que en cerebro.py: Gemini expone una API compatible con OpenAI.
ANCHO_MAXIMO = 1280


class SinVision(Exception):
    """Su texto es lo que se le dice al usuario."""


def _capturar_jpeg_base64() -> str:
    from PIL import ImageGrab

    imagen = ImageGrab.grab().convert("RGB")
    imagen.thumbnail((ANCHO_MAXIMO, ANCHO_MAXIMO))
    memoria = io.BytesIO()
    imagen.save(memoria, format="JPEG", quality=70)
    return base64.b64encode(memoria.getvalue()).decode()


def mirar_pantalla(instruccion: str, **opciones) -> str:
    """Captura la pantalla principal y devuelve lo que Gemini responde a la instrucción sobre ella."""
    if not config.GEMINI_API_KEY:
        raise SinVision("Para ver la pantalla necesito la clave de Gemini.")
    try:
        imagen = _capturar_jpeg_base64()
    except (ImportError, OSError):
        raise SinVision("No pude capturar la pantalla.")
    cliente = openai.OpenAI(base_url=config.URL_GEMINI, api_key=config.GEMINI_API_KEY, timeout=15, max_retries=0)
    try:
        respuesta = cliente.chat.completions.create(
            model=config.MODELO_GEMINI,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruccion},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen}"}},
                    ],
                }
            ],
            **opciones,
        )
    except openai.OpenAIError:
        raise SinVision("No pude analizar la pantalla ahora.")
    return respuesta.choices[0].message.content or ""


def describir_pantalla(pregunta: str = "") -> str:
    instruccion = (
        "Esta es la pantalla de mi PC. Responde en español, en dos o tres frases cortas y sin formato, "
        + (f"a esta pregunta: {pregunta}" if pregunta else "describiendo lo que se ve.")
    )
    try:
        respuesta = mirar_pantalla(instruccion)
    except SinVision as error:
        return str(error)
    return respuesta.strip() or "No supe qué decir de la pantalla."
