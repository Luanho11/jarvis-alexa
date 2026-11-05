import json
import logging
import os
import re
import threading
import time
import unicodedata
from pathlib import Path

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "memoria.json"
VERSION = 2
# Tope de datos (sin contar el nombre): todo el perfil va en cada prompt.
MAX_DATOS = 50
MAX_LARGO = 200
INTENTOS_REEMPLAZO = 5
PAUSA_REEMPLAZO = 0.05
CATEGORIAS = ("personal", "gustos", "personas", "rutinas", "evitar")
TITULOS = {"personal": "Datos", "gustos": "Gustos", "personas": "Personas", "rutinas": "Rutinas", "evitar": "Evitar"}
# Al consolidar se recorta la categoría con más datos por peso: lo que hay que evitar pesa más que un gusto.
PESOS = {"personal": 2, "gustos": 1, "personas": 2, "rutinas": 1, "evitar": 3}
# Orden del prompt: si no cabe todo, lo último es lo que se queda fuera.
ORDEN_CONTEXTO = ("evitar", "personas", "personal", "gustos", "rutinas")
SINONIMOS = {
    "datos": "personal", "datos personales": "personal", "preferencias": "gustos", "gusto": "gustos",
    "persona": "personas", "familia": "personas", "rutina": "rutinas", "horarios": "rutinas",
    "horario": "rutinas", "cosas a evitar": "evitar",
}
# Para los datos sin categoría (los de la memoria antigua y los que el LLM no clasifique). "evitar" va primero
# porque "no le gusta" también contiene "le gusta".
PISTAS = [
    ("evitar", r"\b(no le gusta|no le gustan|odia|detesta|no soporta|evita|evitar|no quiere|nunca|alergic|no le pongas|no menciones)"),
    ("gustos", r"\b(le gusta|le gustan|le encanta|le encantan|prefiere|favorit|disfruta|es fan de|aficion)"),
    ("personas", r"\b(hij[oa]s?|espos[oa]|pareja|novi[oa]|madre|padre|mama|papa|herman[oa]s?|amig[oa]s?|jef[ea]|abuel[oa]|ti[oa]|prim[oa]|companer|perro|gato|mascota)\b"),
    ("rutinas", r"\b(cada|todos los|todas las|lunes|martes|miercoles|jueves|viernes|sabados?|domingos?|fines? de semana|se levanta|se acuesta|horario|a las \d|por las (mananas|tardes|noches)|rutina)\b"),
]
# El cerebro guarda el nombre como "Se llama Ana"; se aceptan también otras formas habituales.
NOMBRE = re.compile(r"^(?:el usuario )?(?:se llama|me llamo|mi nombre es|su nombre es|nombre:)\s+([^\W\d_]+)", re.IGNORECASE)

# Cada turno de cada conversación lee la memoria y varios hilos pueden guardar a la vez.
_candado = threading.Lock()
registro = logging.getLogger(__name__)


def _archivo() -> Path:
    return Path(os.environ.get("MEMORIA_ARCHIVO", ARCHIVO_POR_DEFECTO))


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos: para comparar frases dichas de formas parecidas."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    letras = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(re.findall(r"\w+", letras))


def leer_json(archivo: Path):
    # utf-8-sig: el Bloc de notas puede guardar "UTF-8 con BOM" y json lo rechazaría.
    return json.loads(archivo.read_text(encoding="utf-8-sig"))


def escribir_json(archivo: Path, datos) -> None:
    # Primero a un temporal y luego se reemplaza: un apagado a mitad de escritura no deja el archivo cortado.
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    for intento in range(INTENTOS_REEMPLAZO):
        try:
            os.replace(temporal, archivo)
            return
        except PermissionError:
            # En Windows el antivirus o el indexador abren el archivo un instante y el reemplazo falla.
            if intento == INTENTOS_REEMPLAZO - 1:
                raise
            time.sleep(PAUSA_REEMPLAZO)


def _perfil_vacio() -> dict:
    return {"version": VERSION, "nombre": "", "datos": {categoria: [] for categoria in CATEGORIAS}}


def _categoria(dato: str, pedida: str = "") -> str:
    pedida = pedida.strip().lower()
    pedida = SINONIMOS.get(pedida, pedida)
    if pedida in CATEGORIAS:
        return pedida
    texto = normalizar(dato)
    return next((categoria for categoria, pista in PISTAS if re.search(pista, texto)), "personal")


def _contiene(largo: str, corto: str) -> bool:
    return f" {normalizar(corto)} " in f" {normalizar(largo)} "


def _anadir(perfil: dict, dato: str, categoria: str = "") -> bool:
    """Añade un dato al perfil; False si ya lo sabía. Un dato más completo sustituye al que contiene."""
    nombre_nuevo = False
    coincidencia = NOMBRE.match(dato)
    if coincidencia:
        nombre = coincidencia.group(1).capitalize()
        nombre_nuevo = perfil["nombre"] != nombre
        perfil["nombre"] = nombre
        # "Se llama Ana y vive en Lima": el resto de la frase también es un dato ("José Luis" no).
        if not re.match(r"\s*(,|\.|;|y\s)\s*\w", dato[coincidencia.end():]):
            return nombre_nuevo
    lista = perfil["datos"][_categoria(dato, categoria)]
    for categoria_guardada in perfil["datos"].values():
        if any(_contiene(guardado, dato) for guardado in categoria_guardada):
            return nombre_nuevo
        categoria_guardada[:] = [guardado for guardado in categoria_guardada if not _contiene(dato, guardado)]
    lista.append(dato)
    return True


def _consolidar(perfil: dict) -> None:
    # Sin LLM: se descarta lo más antiguo de la categoría más cargada según su peso. El nombre nunca.
    datos = perfil["datos"]
    while sum(len(lista) for lista in datos.values()) > MAX_DATOS:
        # A igual carga, cae la de menos peso.
        mas_cargada = max(CATEGORIAS, key=lambda categoria: (len(datos[categoria]) / PESOS[categoria], -PESOS[categoria]))
        datos[mas_cargada].pop(0)


def _migrar(lista: list) -> dict:
    perfil = _perfil_vacio()
    for dato in lista:
        if isinstance(dato, str) and dato.strip():
            _anadir(perfil, dato.strip()[:MAX_LARGO])
    _consolidar(perfil)
    return perfil


def _validar(contenido) -> dict:
    if isinstance(contenido, list):
        return _migrar(contenido)
    if not isinstance(contenido, dict) or not isinstance(contenido.get("datos", {}), dict):
        raise ValueError("memoria.json no tiene el formato esperado")
    perfil = _perfil_vacio()
    perfil["nombre"] = str(contenido.get("nombre") or "").strip()
    for categoria, lista in contenido.get("datos", {}).items():
        if not isinstance(lista, list) or not all(isinstance(dato, str) for dato in lista):
            raise ValueError(f"memoria.json: la categoría {categoria} no es una lista de frases")
        # Una categoría inventada al editar a mano se conserva como dato personal.
        destino = categoria if categoria in CATEGORIAS else "personal"
        perfil["datos"][destino].extend(dato.strip() for dato in lista if dato.strip())
    return perfil


def _cargar() -> dict:
    """El perfil; la memoria antigua (una lista de frases) se convierte al leerla y se guarda así al escribir."""
    archivo = _archivo()
    if not archivo.exists():
        return _perfil_vacio()
    return _validar(leer_json(archivo))


def _leer() -> dict:
    # Se lee en cada frase: un memoria.json editado a mano y roto no debe dejar mudo a Jarvis.
    # Las escrituras sí fallan, para no pisar lo que el usuario estaba editando.
    with _candado:
        try:
            return _cargar()
        except ValueError:
            registro.warning("memoria.json no se puede leer; sigo sin memoria hasta que se arregle")
            return _perfil_vacio()


def perfil() -> dict:
    """Copia del perfil: {"nombre": str, "datos": {categoría: [frases, de la más antigua a la más nueva]}}."""
    return _leer()


def datos_guardados() -> list[str]:
    actual = _leer()
    nombre = [f"Se llama {actual['nombre']}"] if actual["nombre"] else []
    return nombre + [dato for categoria in CATEGORIAS for dato in actual["datos"][categoria]]


def nombre_usuario() -> str:
    return _leer()["nombre"]


def contexto_usuario(max_caracteres: int = 1200) -> str:
    """Perfil compacto para el prompt; si no cabe, quedan fuera los datos más antiguos de lo menos importante."""
    actual = _leer()
    partes = [f"Se llama {actual['nombre']}."] if actual["nombre"] else []
    largo = sum(len(parte) + 1 for parte in partes)
    for categoria in ORDEN_CONTEXTO:
        cabecera = f"{TITULOS[categoria]}: "
        elegidos = []
        for dato in reversed(actual["datos"][categoria]):
            extra = len(dato) + 2 + (len(cabecera) if not elegidos else 0)
            if largo + extra > max_caracteres:
                break
            elegidos.append(dato.rstrip("."))
            largo += extra
        if elegidos:
            partes.append(cabecera + "; ".join(elegidos) + ".")
    return " ".join(partes)


def recordar(dato: str, categoria: str = "") -> str:
    dato = dato.strip()[:MAX_LARGO]
    if not normalizar(dato):
        return "No me dijiste qué recordar."
    with _candado:
        actual = _cargar()
        if not _anadir(actual, dato, categoria):
            return "Eso ya lo sabía."
        _consolidar(actual)
        escribir_json(_archivo(), actual)
    return f"Lo recordaré: {dato}."


def olvidar_dato(dato: str) -> str:
    buscado = normalizar(dato)
    if not buscado:
        return "No me dijiste qué olvidar."
    with _candado:
        actual = _cargar()
        borrados = 0
        if actual["nombre"] and buscado in normalizar(f"se llama {actual['nombre']}"):
            actual["nombre"] = ""
            borrados += 1
        for lista in actual["datos"].values():
            restantes = [guardado for guardado in lista if buscado not in normalizar(guardado)]
            borrados += len(lista) - len(restantes)
            lista[:] = restantes
        if not borrados:
            return "No tenía guardado nada sobre eso."
        escribir_json(_archivo(), actual)
    return "Listo, lo olvidé."


def borrar_todo() -> None:
    with _candado:
        _archivo().unlink(missing_ok=True)
