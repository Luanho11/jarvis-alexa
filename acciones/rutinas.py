import json
from pathlib import Path

from acciones.pc import abrir_web, fijar_volumen, reproducir_en_youtube
from acciones.programas import abrir_programa, cerrar_programa, normalizar

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
RUTINAS = CARPETA_PROYECTO / "rutinas.json"
RUTINAS_EJEMPLO = CARPETA_PROYECTO / "rutinas.ejemplo.json"

ACCIONES = {
    "abrir_programa": abrir_programa,
    "cerrar_programa": cerrar_programa,
    "abrir_web": abrir_web,
    "reproducir_en_youtube": reproducir_en_youtube,
    "fijar_volumen": fijar_volumen,
}


def _cargar() -> dict | None:
    archivo = RUTINAS if RUTINAS.exists() else RUTINAS_EJEMPLO
    try:
        modos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {normalizar(nombre): pasos for nombre, pasos in modos.items()}


def listar_modos() -> str:
    modos = _cargar()
    if modos is None:
        return "No pude leer rutinas.json, revisa que esté bien escrito."
    if not modos:
        return "No tienes modos definidos."
    return "Tus modos son: " + ", ".join(modos) + "."


def _ejecutar_paso(paso: dict) -> bool:
    if not isinstance(paso, dict) or paso.get("accion") not in ACCIONES:
        return False
    try:
        ACCIONES[paso["accion"]](**paso.get("argumentos", {}))
    except TypeError:
        return False
    return True


def activar_modo(nombre: str) -> str:
    modos = _cargar()
    if modos is None:
        return "No pude leer rutinas.json, revisa que esté bien escrito."
    nombre = normalizar(nombre).removeprefix("modo ")
    if nombre not in modos:
        return f"No tengo el modo {nombre}. " + listar_modos()
    fallidos = sum(not _ejecutar_paso(paso) for paso in modos[nombre])
    if fallidos:
        return f"Modo {nombre} activado, pero hubo problemas en {fallidos} de sus pasos."
    return f"Modo {nombre} activado."
