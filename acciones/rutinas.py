import json
from pathlib import Path

from acciones import personas
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
ERROR_RUTINAS = "No pude leer rutinas.json, revisa que esté bien escrito."


def _cargar() -> dict | None:
    archivo = RUTINAS if RUTINAS.exists() else RUTINAS_EJEMPLO
    try:
        modos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {normalizar(nombre): pasos for nombre, pasos in modos.items()}


def listar_modos() -> str:
    modos = _cargar()
    partes = []
    if modos is None:
        partes.append(ERROR_RUTINAS)
    elif modos:
        partes.append("Tus modos son: " + ", ".join(modos) + ".")
    formas = personas.disponibles()
    if formas:
        partes.append("Formas de hablar: " + ", ".join(formas) + ".")
    return " ".join(partes) or "No tienes modos definidos."


def _ejecutar_paso(paso: dict) -> bool:
    if not isinstance(paso, dict) or paso.get("accion") not in ACCIONES:
        return False
    try:
        ACCIONES[paso["accion"]](**paso.get("argumentos", {}))
    except TypeError:
        return False
    return True


def activar_modo(nombre: str) -> str:
    nombre = normalizar(nombre).removeprefix("modo ")
    if nombre == "normal":
        personas.restablecer()
        return "Listo, vuelvo a hablar normal."
    modos = _cargar()
    # Si una rutina y una persona se llaman igual, gana la rutina.
    if not modos or nombre not in modos:
        activada = personas.activar(nombre)
        if activada:
            return activada
        if modos is None:
            return ERROR_RUTINAS
        return f"No tengo el modo {nombre}. " + listar_modos()
    fallidos = sum(not _ejecutar_paso(paso) for paso in modos[nombre])
    if fallidos:
        return f"Modo {nombre} activado, pero hubo problemas en {fallidos} de sus pasos."
    return f"Modo {nombre} activado."
