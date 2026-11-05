import copy
import difflib
import functools
import json
import logging
import os
import re
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "memoria.json"
VERSION = 3
MAX_LARGO = 200
INTENTOS_REEMPLAZO = 5
PAUSA_REEMPLAZO = 0.05
CATEGORIAS = ("personal", "gustos", "personas", "rutinas", "evitar")
TITULOS = {"personal": "Datos", "gustos": "Gustos", "personas": "Personas", "rutinas": "Rutinas", "evitar": "Evitar"}
# Para elegir qué datos van al prompt: lo que hay que evitar va siempre; entre el resto pesa más quién es y su gente.
PESOS = {"personal": 2, "gustos": 1, "personas": 2, "rutinas": 1, "evitar": 3}
ORDEN_CONTEXTO = ("evitar", "personas", "personal", "gustos", "rutinas")
PUNTOS_POR_COINCIDENCIA = 4
# Confirmar un dato dos veces en la misma charla (la frase, la herramienta y el resumen) no lo hace más cierto.
HORAS_ENTRE_CONFIRMACIONES = 1
SIMILITUD_PARA_OLVIDAR = 0.85
SINONIMOS = {
    "datos": "personal", "datos personales": "personal", "preferencias": "gustos", "gusto": "gustos",
    "persona": "personas", "familia": "personas", "rutina": "rutinas", "horarios": "rutinas",
    "horario": "rutinas", "cosas a evitar": "evitar",
}
# Para los datos sin categoría. "evitar" va primero porque "no le gusta" también contiene "le gusta".
PISTAS = [
    ("evitar", r"\b(no le gusta|no le gustan|odia|detesta|no soporta|evita|evitar|no quiere|nunca|alergic|no le pongas|no menciones)"),
    ("gustos", r"\b(le gusta|le gustan|le encanta|le encantan|prefiere|favorit|disfruta|es fan de|aficion)"),
    ("personas", r"\b(hij[oa]s?|espos[oa]|pareja|novi[oa]|madre|padre|mama|papa|herman[oa]s?|amig[oa]s?|jef[ea]|abuel[oa]|ti[oa]|prim[oa]|companer|perro|gato|mascota)\b"),
    ("rutinas", r"\b(cada|todos los|todas las|lunes|martes|miercoles|jueves|viernes|sabados?|domingos?|fines? de semana|se levanta|se acuesta|horario|a las \d|por las (mananas|tardes|noches)|rutina)\b"),
]
# Datos que solo pueden tener un valor: "Vive en Cusco" sustituye a "Vive en Lima".
UNICOS = re.compile(
    r"^(vive en|es de|trabaja en|trabaja como|trabaja de|estudia|tiene \d+ anos|cumple anos|su cumpleanos es"
    r"|su [a-z ]{1,30}? favorit[oa]s? es)\b"
)
# Las de 3 letras o menos ya se descartan por su largo.
VACIAS = {
    "unos", "unas", "para", "sobre", "como", "cual", "pero", "esta", "este", "esto", "algo", "tiene", "hace",
    "dime", "quiero", "puedes", "jarvis", "favor", "ahora",
}
# El cerebro guarda el nombre como "Se llama Ana"; se aceptan también otras formas habituales.
NOMBRE = re.compile(r"^(?:el usuario )?(?:se llama|me llamo|mi nombre es|su nombre es|nombre:)\s+([^\W\d_]+)", re.IGNORECASE)

# Cada turno de cada conversación lee la memoria y varios hilos pueden guardar a la vez.
_candado = threading.Lock()
# Leer y validar el archivo en cada frase cuesta más que mirar si cambió.
_cache: dict = {"clave": None, "perfil": None}
registro = logging.getLogger(__name__)


def _archivo() -> Path:
    return Path(os.environ.get("MEMORIA_ARCHIVO", ARCHIVO_POR_DEFECTO))


# Cada frase compara el pedido con todos los datos: sin memorizar, con miles de datos se notaría.
@functools.lru_cache(maxsize=20000)
def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos: para comparar frases dichas de formas parecidas."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    letras = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(re.findall(r"\w+", letras))


@functools.lru_cache(maxsize=20000)
def raices(texto: str) -> frozenset[str]:
    """Palabras con significado recortadas a 5 letras: "hermana" encuentra "hermano" y "trabajo", "trabaja"."""
    return frozenset(palabra[:5] for palabra in normalizar(texto).split() if len(palabra) > 3 and palabra not in VACIAS)


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


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def _fecha(texto: str) -> datetime:
    try:
        return datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        return datetime(2000, 1, 1)


def _perfil_vacio() -> dict:
    return {"version": VERSION, "nombre": "", "datos": []}


def _categoria(dato: str, pedida: str = "") -> str:
    pedida = pedida.strip().lower()
    pedida = SINONIMOS.get(pedida, pedida)
    if pedida in CATEGORIAS:
        return pedida
    texto = normalizar(dato)
    return next((categoria for categoria, pista in PISTAS if re.search(pista, texto)), "personal")


def _contiene(largo: str, corto: str) -> bool:
    return f" {normalizar(corto)} " in f" {normalizar(largo)} "


def _nuevo(texto: str, categoria: str, origen: str, creado: str = "") -> dict:
    fecha = creado or _ahora()
    return {"texto": texto, "categoria": categoria, "creado": fecha, "visto": fecha, "veces": 1, "origen": origen}


def _confirmar(dato: dict) -> None:
    ahora = datetime.now()
    if (ahora - _fecha(dato["visto"])).total_seconds() >= HORAS_ENTRE_CONFIRMACIONES * 3600:
        dato["veces"] += 1
    dato["visto"] = ahora.strftime("%Y-%m-%dT%H:%M")


def _clave_unica(normal: str) -> str:
    # "tiene 30 anos" y "tiene 31 anos" son el mismo dato con otro valor.
    coincidencia = UNICOS.match(normal)
    return re.sub(r"\d+", "#", coincidencia.group(1)) if coincidencia else ""


def _anadir(perfil: dict, texto: str, categoria: str = "", origen: str = "usuario") -> str:
    """Mete un dato en el perfil y dice qué pasó: nuevo, actualizado, sabido, borrado o nada."""
    normal = normalizar(texto)
    if normal.startswith("ya no "):
        # "Ya no vive en Lima": se borra lo que deja de ser cierto y no se guarda la negación.
        objetivo = normal.removeprefix("ya no ")
        antes = len(perfil["datos"])
        perfil["datos"] = [dato for dato in perfil["datos"] if not _contiene(dato["texto"], objetivo)]
        return "borrado" if len(perfil["datos"]) < antes else "nada"
    estado = "nada"
    coincidencia = NOMBRE.match(texto)
    if coincidencia:
        nombre = coincidencia.group(1).capitalize()
        estado = "actualizado" if perfil["nombre"] != nombre else "sabido"
        perfil["nombre"] = nombre
        # "Se llama Ana y vive en Lima": el resto de la frase también es un dato ("José Luis" no).
        if not re.match(r"\s*(,|\.|;|y\s)\s*\w", texto[coincidencia.end():]):
            return estado
    categoria = _categoria(texto, categoria)
    unico = _clave_unica(normal)
    for dato in list(perfil["datos"]):
        guardado = normalizar(dato["texto"])
        contradice = f" no {normal} " in f" {guardado} " or f" no {guardado} " in f" {normal} "
        if not contradice and _contiene(dato["texto"], texto):
            _confirmar(dato)
            return "sabido" if estado in ("nada", "sabido") else estado
        mismo_dato = unico and _clave_unica(guardado) == unico
        if contradice or mismo_dato or _contiene(texto, dato["texto"]):
            # Lo nuevo corrige o completa lo viejo: se queda en su sitio con la fecha en que se supo por primera vez.
            dato.update(texto=texto, categoria=categoria)
            _confirmar(dato)
            perfil["datos"] = [otro for otro in perfil["datos"] if otro is dato or not _contiene(texto, otro["texto"])]
            return "actualizado"
    perfil["datos"].append(_nuevo(texto, categoria, origen))
    return "nuevo"


def _migrar(lista: list) -> dict:
    perfil = _perfil_vacio()
    for dato in lista:
        if isinstance(dato, str) and dato.strip():
            _anadir(perfil, dato.strip()[:MAX_LARGO], origen="antigua")
    return perfil


def _validar(contenido) -> dict:
    if isinstance(contenido, list):
        return _migrar(contenido)
    if not isinstance(contenido, dict):
        raise ValueError("memoria.json no tiene el formato esperado")
    perfil = _perfil_vacio()
    perfil["nombre"] = str(contenido.get("nombre") or "").strip()
    datos = contenido.get("datos", [])
    if isinstance(datos, dict):
        # Versión 2: una lista de frases por categoría. Una categoría inventada a mano se conserva como dato personal.
        for categoria, lista in datos.items():
            if not isinstance(lista, list) or not all(isinstance(texto, str) for texto in lista):
                raise ValueError(f"memoria.json: la categoría {categoria} no es una lista de frases")
            destino = categoria if categoria in CATEGORIAS else "personal"
            perfil["datos"] += [_nuevo(texto.strip(), destino, "antigua", "2000-01-01T00:00") for texto in lista if texto.strip()]
        return perfil
    if not isinstance(datos, list):
        raise ValueError("memoria.json: datos no es una lista")
    for dato in datos:
        if not isinstance(dato, dict) or not isinstance(dato.get("texto"), str):
            raise ValueError("memoria.json: cada dato necesita un texto")
        if not dato["texto"].strip():
            continue
        veces = dato.get("veces")
        perfil["datos"].append({
            **dato,
            "texto": dato["texto"].strip(),
            "categoria": _categoria(dato["texto"], str(dato.get("categoria") or "")),
            "creado": str(dato.get("creado") or ""),
            "visto": str(dato.get("visto") or dato.get("creado") or ""),
            "veces": veces if isinstance(veces, int) and veces > 0 else 1,
            "origen": str(dato.get("origen") or "usuario"),
        })
    return perfil


def _cargar() -> dict:
    """El perfil, nuevo en cada llamada; los formatos antiguos se convierten al leer y se guardan así al escribir."""
    archivo = _archivo()
    if not archivo.exists():
        return _perfil_vacio()
    return _validar(leer_json(archivo))


def _guardar(perfil: dict) -> None:
    escribir_json(_archivo(), perfil)
    _cache["clave"] = None


def _leer() -> dict:
    """Solo para leer: puede ser el mismo objeto en varias llamadas, no se modifica."""
    # Se lee en cada frase: un memoria.json editado a mano y roto no debe dejar mudo a Jarvis.
    # Las escrituras sí fallan, para no pisar lo que el usuario estaba editando.
    with _candado:
        archivo = _archivo()
        try:
            estado = archivo.stat()
        except OSError:
            return _perfil_vacio()
        clave = (str(archivo), estado.st_mtime_ns, estado.st_size)
        if _cache["clave"] != clave:
            try:
                _cache["perfil"] = _validar(leer_json(archivo))
            except (OSError, ValueError):
                registro.warning("memoria.json no se puede leer; sigo sin memoria hasta que se arregle")
                return _perfil_vacio()
            _cache["clave"] = clave
        return _cache["perfil"]


def perfil() -> dict:
    """Copia del perfil: {"nombre": str, "datos": [{"texto", "categoria", "creado", "visto", "veces", "origen"}]}."""
    return copy.deepcopy(_leer())


def cantidad() -> int:
    return len(_leer()["datos"])


def datos_guardados() -> list[str]:
    actual = _leer()
    nombre = [f"Se llama {actual['nombre']}"] if actual["nombre"] else []
    return nombre + [dato["texto"] for dato in actual["datos"]]


def nombre_usuario() -> str:
    return _leer()["nombre"]


def _puntos(dato: dict, buscadas: frozenset[str], ahora: datetime) -> tuple[float, int]:
    coincidencias = len(buscadas & raices(dato["texto"]))
    reciente = max(_fecha(dato["visto"]), _fecha(dato.get("usado", "")))
    dias = max((ahora - reciente).days, 0)
    puntos = PUNTOS_POR_COINCIDENCIA * coincidencias + PESOS[dato["categoria"]] + min(dato["veces"] - 1, 4) + 2 / (1 + dias / 30)
    return puntos, coincidencias


def _marcar_usados(textos: set[str]) -> None:
    # Una vez al día como mucho por dato: guardar en cada frase escribiría el archivo sin parar.
    hoy = _ahora()[:10]
    with _candado:
        try:
            actual = _cargar()
            cambiados = [d for d in actual["datos"] if d["texto"] in textos and d.get("usado", "")[:10] != hoy]
            for dato in cambiados:
                dato["usado"] = _ahora()
            if cambiados:
                _guardar(actual)
        except (OSError, ValueError):
            registro.warning("No pude anotar qué datos de la memoria se usaron", exc_info=True)


def contexto_usuario(max_caracteres: int = 1200, pedido: str = "") -> str:
    """Los datos más útiles para este pedido en poco texto: el nombre y lo que hay que evitar primero, y luego
    los que comparten palabras con el pedido, los importantes, los confirmados varias veces y los recientes."""
    actual = _leer()
    partes = [f"Se llama {actual['nombre']}."] if actual["nombre"] else []
    largo = sum(len(parte) + 1 for parte in partes)
    buscadas = raices(pedido)
    ahora = datetime.now()
    puntuados = sorted(
        ((*_puntos(dato, buscadas, ahora), indice, dato) for indice, dato in enumerate(actual["datos"])),
        key=lambda fila: (fila[3]["categoria"] != "evitar", -fila[0], -fila[2]),
    )
    elegidos = {categoria: [] for categoria in CATEGORIAS}
    usados = set()
    for _, coincidencias, _, dato in puntuados:
        texto = dato["texto"].rstrip(".")
        coste = len(texto) + 2 + (0 if elegidos[dato["categoria"]] else len(TITULOS[dato["categoria"]]) + 2)
        if largo + coste > max_caracteres:
            continue
        elegidos[dato["categoria"]].append(texto)
        largo += coste
        if coincidencias:
            usados.add(dato["texto"])
    partes += [f"{TITULOS[c]}: {'; '.join(elegidos[c])}." for c in ORDEN_CONTEXTO if elegidos[c]]
    if usados:
        _marcar_usados(usados)
    return " ".join(partes)


def guardar(dato: str, categoria: str = "", origen: str = "usuario") -> str:
    """Como recordar, pero devuelve el estado (nuevo, actualizado, sabido, borrado o nada) para quien aprende solo."""
    dato = dato.strip()[:MAX_LARGO]
    if not normalizar(dato):
        return "nada"
    with _candado:
        actual = _cargar()
        estado = _anadir(actual, dato, categoria, origen)
        # "sabido" también se guarda: cuenta como una confirmación más del dato.
        if estado != "nada":
            _guardar(actual)
    return estado


def recordar(dato: str, categoria: str = "") -> str:
    if not normalizar(dato):
        return "No me dijiste qué recordar."
    estado = guardar(dato, categoria)
    if estado == "sabido":
        return "Eso ya lo sabía."
    if estado == "borrado":
        return "Entendido, lo actualicé."
    if estado == "nada":
        return "Entendido."
    return f"Lo recordaré: {dato.strip()[:MAX_LARGO]}."


def olvidar_dato(dato: str) -> str:
    buscado = normalizar(dato)
    if not buscado:
        return "No me dijiste qué olvidar."
    with _candado:
        actual = _cargar()
        antes = len(actual["datos"]) + bool(actual["nombre"])
        if actual["nombre"] and buscado in normalizar(f"se llama {actual['nombre']}"):
            actual["nombre"] = ""
        actual["datos"] = [d for d in actual["datos"] if buscado not in normalizar(d["texto"])]
        if len(actual["datos"]) + bool(actual["nombre"]) == antes:
            return "No tenía guardado nada sobre eso."
        _guardar(actual)
    return "Listo, lo olvidé."


def olvidar_parecido(texto: str) -> bool:
    """Borra solo el dato casi idéntico a texto: para correcciones que propone el LLM, que no deben borrar de más."""
    buscado = normalizar(texto)
    if not buscado:
        return False
    with _candado:
        actual = _cargar()
        restantes = [
            d for d in actual["datos"]
            if difflib.SequenceMatcher(None, normalizar(d["texto"]), buscado).ratio() < SIMILITUD_PARA_OLVIDAR
        ]
        if len(restantes) == len(actual["datos"]):
            return False
        actual["datos"] = restantes
        _guardar(actual)
    return True


def borrar_todo() -> None:
    with _candado:
        _archivo().unlink(missing_ok=True)
        _cache["clave"] = None
