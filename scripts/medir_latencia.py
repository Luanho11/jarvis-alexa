"""Mide cuánto tarda Jarvis en responder, de la petición de Alexa a la respuesta, con tus claves del .env.

Las acciones se simulan (no toca tu volumen ni abre nada) y el HUD no se abre. No incluye lo que pone Alexa:
reconocer tu voz, el viaje por ngrok y leer la respuesta en voz alta.

Uso (en la carpeta de Jarvis):  .venv\\Scripts\\python scripts\\medir_latencia.py [-n 5] [--pausa 10] [--falso]
"""
import argparse
import math
import statistics
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai.types.chat import ChatCompletionMessage  # noqa: E402

import cerebro  # noqa: E402
import config  # noqa: E402
import herramientas  # noqa: E402
import servidor  # noqa: E402

ESCENARIOS = [
    ("Orden directa (ruta rápida)", "sube el volumen"),
    ("Orden con acción vía LLM", "ponme un temporizador de cinco minutos para la pasta"),
    ("Pregunta de conversación", "¿cuántos planetas tiene el sistema solar?"),
]
SIMULADA = "Hecho."


class ClienteFalso:
    """LLM instantáneo: mide solo lo que tarda nuestro código."""

    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **peticion):
        ultimo = peticion["messages"][-1]
        if ultimo["role"] == "user" and "temporizador" in ultimo["content"]:
            llamada = {"id": "t0", "type": "function",
                       "function": {"name": "poner_temporizador", "arguments": '{"minutos": 5}'}}
            mensaje = ChatCompletionMessage.model_validate({"role": "assistant", "tool_calls": [llamada]})
        else:
            mensaje = ChatCompletionMessage.model_validate({"role": "assistant", "content": "Ocho planetas."})
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def percentil(valores: list[float], porcentaje: int) -> float:
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(porcentaje / 100 * len(ordenados)) - 1)]


def peticion_alexa(texto: str) -> dict:
    aplicacion = {"applicationId": servidor.ALEXA_SKILL_ID}
    usuario = {"userId": "medicion"}
    return {
        "version": "1.0",
        "session": {"new": False, "sessionId": str(uuid.uuid4()), "application": aplicacion, "user": usuario},
        "context": {"System": {"application": aplicacion, "user": usuario,
                               "device": {"deviceId": "medicion", "supportedInterfaces": {}},
                               "apiEndpoint": "https://api.amazonalexa.com"}},
        "request": {"type": "IntentRequest", "requestId": "medicion", "timestamp": "2026-01-01T00:00:00Z",
                    "locale": "es-MX",
                    "intent": {"name": "ConversarIntent", "slots": {"texto": {"name": "texto", "value": texto}}}},
    }


def medir(n: int, pausa: float, falso: bool) -> str:
    config.HUD_ACTIVO = False
    herramientas.ejecutar = lambda nombre, argumentos: SIMULADA
    jarvis = cerebro.Cerebro([(ClienteFalso(), "falso")] if falso else None)
    if not jarvis.clientes:
        print("No hay GROQ_API_KEY ni GEMINI_API_KEY en el .env: mido con un LLM falso (solo nuestro código).\n")
        jarvis = cerebro.Cerebro([(ClienteFalso(), "falso")])
        falso = True
    cliente = servidor.crear_app(jarvis, verificar=False).test_client()
    lineas = []
    for nombre, texto in ESCENARIOS:
        tiempos, llamadas, hechas = [], [], []
        for vez in range(n):
            if llamadas and llamadas[-1] and not falso and pausa:
                # El plan gratis de Groq da 8.000 tokens por minuto: sin pausa saltaría a Gemini y mediría otra cosa.
                time.sleep(pausa)
            inicio = time.perf_counter()
            respuesta = cliente.post("/alexa", json=peticion_alexa(texto))
            tiempos.append((time.perf_counter() - inicio) * 1000)
            if respuesta.status_code != 200:
                raise SystemExit(f"El servidor respondió {respuesta.status_code} a '{texto}'")
            medicion = jarvis.ultima_medicion
            llamadas.append(len(medicion.llamadas))
            hechas += medicion.llamadas
        usados = ", ".join(sorted({llamada.modelo for llamada in hechas})) or "ninguno"
        lineas.append(
            f"{nombre} — \"{texto}\"\n"
            f"  mediana {statistics.median(tiempos):.0f} ms · p90 {percentil(tiempos, 90):.0f} ms · "
            f"mín {min(tiempos):.0f} · máx {max(tiempos):.0f} · "
            f"llamadas al LLM por petición {statistics.mean(llamadas):.1f} · modelos: {usados}"
        )
        if hechas and not falso:
            # Lo que cuenta en el límite de Groq es la entrada fuera de la caché más la salida.
            entrada = statistics.mean(llamada.entrada for llamada in hechas)
            cache = statistics.mean(llamada.cache for llamada in hechas)
            salida = statistics.mean(llamada.salida for llamada in hechas)
            lineas.append(
                f"  tokens por llamada: {entrada:.0f} de entrada ({cache:.0f} en caché), {salida:.0f} de salida"
                f" → cuentan para el límite unos {entrada - cache + salida:.0f}"
            )
    return "\n".join(lineas)


def main(argumentos: list[str] | None = None) -> None:
    lector = argparse.ArgumentParser(description="Mide la latencia de Jarvis (acciones simuladas).")
    lector.add_argument("-n", type=int, default=5, help="veces por escenario (por defecto 5)")
    lector.add_argument("--pausa", type=float, default=10, help="segundos entre peticiones al LLM (por defecto 10)")
    lector.add_argument("--falso", action="store_true", help="LLM falso instantáneo: mide solo el servidor")
    opciones = lector.parse_args(argumentos)
    print(medir(max(1, opciones.n), opciones.pausa, opciones.falso))
    print("\nA esto súmale lo de Alexa: reconocer tu voz y leer la respuesta (~1-2 s, fuera de nuestro control).")


if __name__ == "__main__":
    main()
