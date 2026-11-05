import json
import logging
import os
import re
import threading
from pathlib import Path

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "memoria.json"
MAX_DATOS = 50
# El cerebro guarda el nombre como "Se llama Ana"; se aceptan también otras formas habituales.
# Cada turno de cada conversación lee la memoria y varios hilos pueden guardar a la vez.
_candado = threading.Lock()
registro = logging.getLogger(__name__)
NOMBRE = re.compile(r"^(?:el usuario )?(?:se llama|me llamo|mi nombre es|su nombre es|nombre:)\s+([^\W\d_]+)", re.IGNORECASE)


def _archivo() -> Path:
    return Path(os.environ.get("MEMORIA_ARCHIVO", ARCHIVO_POR_DEFECTO))


def _cargar() -> list[str]:
    archivo = _archivo()
    if not archivo.exists():
        return []
    return json.loads(archivo.read_text(encoding="utf-8"))


def datos_guardados() -> list[str]:
    # Se lee en cada frase: un memoria.json editado a mano y roto no debe dejar mudo a Jarvis.
    # Las escrituras sí fallan, para no pisar lo que el usuario estaba editando.
    with _candado:
        try:
            return _cargar()
        except ValueError:
            registro.warning("memoria.json no se puede leer; sigo sin memoria hasta que se arregle")
            return []


def nombre_usuario() -> str:
    # El más reciente manda, por si el usuario corrigió su nombre.
    for dato in reversed(datos_guardados()):
        coincidencia = NOMBRE.match(dato.strip())
        if coincidencia:
            return coincidencia.group(1).capitalize()
    return ""


def _guardar(datos: list[str]) -> None:
    _archivo().write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def recordar(dato: str) -> str:
    dato = dato.strip()
    if not dato:
        return "No me dijiste qué recordar."
    with _candado:
        datos = _cargar()
        if dato.lower() in (guardado.lower() for guardado in datos):
            return "Eso ya lo sabía."
        # Con la memoria llena se pierde el dato más antiguo para no inflar el prompt.
        _guardar([*datos, dato][-MAX_DATOS:])
    return f"Lo recordaré: {dato}."


def olvidar_dato(dato: str) -> str:
    buscado = dato.strip().lower()
    if not buscado:
        return "No me dijiste qué olvidar."
    with _candado:
        datos = _cargar()
        restantes = [guardado for guardado in datos if buscado not in guardado.lower()]
        if len(restantes) == len(datos):
            return "No tenía guardado nada sobre eso."
        _guardar(restantes)
    return "Listo, lo olvidé."
