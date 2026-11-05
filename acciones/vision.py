import base64
import io

import openai

import config

# Igual que en cerebro.py: Gemini expone una API compatible con OpenAI.
ANCHO_MAXIMO = 1280


def _capturar_jpeg_base64() -> str:
    from PIL import ImageGrab

    imagen = ImageGrab.grab().convert("RGB")
    imagen.thumbnail((ANCHO_MAXIMO, ANCHO_MAXIMO))
    memoria = io.BytesIO()
    imagen.save(memoria, format="JPEG", quality=70)
    return base64.b64encode(memoria.getvalue()).decode()


def describir_pantalla(pregunta: str = "") -> str:
    if not config.GEMINI_API_KEY:
        return "Para ver la pantalla necesito la clave de Gemini."
    try:
        imagen = _capturar_jpeg_base64()
    except (ImportError, OSError):
        return "No pude capturar la pantalla."
    instruccion = (
        "Esta es la pantalla de mi PC. Responde en español, en dos o tres frases cortas y sin formato, "
        + (f"a esta pregunta: {pregunta}" if pregunta else "describiendo lo que se ve.")
    )
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
        )
    except openai.OpenAIError:
        return "No pude analizar la pantalla ahora."
    return (respuesta.choices[0].message.content or "No supe qué decir de la pantalla.").strip()
