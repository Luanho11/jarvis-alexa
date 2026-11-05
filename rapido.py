"""Órdenes frecuentes resueltas sin LLM: solo frases que encajan enteras en una regla; ante la duda, el LLM."""
import re
from datetime import datetime

from acciones.programas import ALIAS, PROCESOS, normalizar

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

CORTESIA = {"jarvis", "oye", "porfa", "porfavor"}
PUNTUACION = "¿?¡!.,;:\"'«»“”"
# Una frase con dos órdenes, condiciones o matices la entiende mejor el LLM.
CONECTORES = re.compile(r"\b(y|e|o|u|ni|luego|despues|tambien|ademas|pero|cuando|si|mientras|antes|porque|que|no)\b")

UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
            "seis": 6, "siete": 7, "ocho": 8, "nueve": 9}
ESPECIALES = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
              "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
              "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
              "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "cien": 100}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
VOLUMENES_FIJOS = {"maximo": 100, "tope": 100, "minimo": 0, "la mitad": 50}

WEBS = {
    "google": "google.com", "gmail": "mail.google.com", "correo": "mail.google.com", "facebook": "facebook.com",
    "instagram": "instagram.com", "twitter": "x.com", "netflix": "netflix.com", "amazon": "amazon.com",
    "wikipedia": "es.wikipedia.org", "chatgpt": "chatgpt.com", "github": "github.com", "linkedin": "linkedin.com",
    "tiktok": "tiktok.com", "twitch": "twitch.tv", "google maps": "maps.google.com", "maps": "maps.google.com",
    "mercado libre": "mercadolibre.com", "whatsapp web": "web.whatsapp.com", "youtube music": "music.youtube.com",
}
# "Abre mis notas" puede ser el bloc de notas o las notas de Jarvis.
PROGRAMAS_DUDOSOS = {"notas"}
CARPETAS = {"documentos", "descargas", "escritorio", "imagenes", "musica", "videos"}
CARPETAS_SIN_DECIR_CARPETA = {"documentos", "descargas"}
# En "pon X", estas palabras dicen que X no es una canción.
NO_ES_MUSICA = {
    "temporizador", "alarma", "alarmas", "recordatorio", "volumen", "sonido", "pausa", "modo", "pantalla", "mouse",
    "raton", "cursor", "nota", "notas", "evento", "agenda", "cita", "brillo", "wifi", "luz", "luces", "tele",
    "television", "aire", "documento", "word", "excel", "carpeta", "archivo", "ventana", "captura", "minuto",
    "minutos", "segundo", "segundos", "hora", "horas", "spotify", "netflix", "youtube", "pc", "computadora", "clic",
    "noticias", "clima", "atencion", "cuidado", "orden", "contrasena", "recordatorios", "tarea", "tareas",
}
GENERICOS = {"musica", "algo", "cancion", "canciones", "video", "videos", "tema", "temas"}
# Determinantes y pronombres: "pon la de ayer", "pon un temporizador", "ponme de buen humor".
INICIOS_DUDOSOS = {"un", "una", "unos", "unas", "el", "la", "los", "las", "lo", "le", "les", "me", "te", "se", "mas",
                   "menos", "en", "al", "del", "de", "esa", "ese", "eso", "esta", "este", "esto", "otra", "otro", "mi",
                   "mis", "tu", "su", "algo"}
MAX_PALABRAS_BUSQUEDA = 8
MAX_PALABRAS_CLIC = 6

NUMERO = r"\d{1,3}|[a-z]+(?: y [a-z]+)?"
ARTICULO = r"(?:(?:el|la|los|las|mi|mis) )?"
PC = r"(?:(?:el|la|mi) )?(?:pc|computadora|computador|ordenador|compu|equipo|laptop|portatil)"
MEDIA = r"(?:la musica|la cancion|el video|el audio|youtube|spotify|la reproduccion)"
VOLUMEN = r"(?:el )?(?:volumen|sonido)"
PORCENTAJE = r"(?: ?%| por ciento)?"
CUANTO = r"(?P<cuanto> un poco| un poquito| mas| bastante| mucho)?"
# "medio minuto" antes que el número: si no, "medio" se tomaría por un número y la regla fallaría.
DURACION_EXACTA = rf" (?:(?P<fijo>un minuto|medio minuto)|(?P<n>{NUMERO}) (?P<unidad>segundos?|minutos?))"
DURACION = rf"(?:{DURACION_EXACTA})?"
MINUTOS = rf"(?: en (?P<n>{NUMERO}) minutos?)?"
CLIC = r"(?:(?:haz|has|dale|da) )?(?:un )?(?P<doble>doble )?(?:clic|click|clik)"
RATON = r"(?:mouse|raton|cursor)"
BOTON = r"(?: (?:con el )?(?:boton )?(?P<boton>derecho|izquierdo|central|del medio))?"


def numero(texto: str) -> int | None:
    """Un número de 0 a 100 en cifras o en palabras ("treinta y cinco")."""
    if texto.isdigit():
        return int(texto)
    if texto in UNIDADES:
        return UNIDADES[texto]
    if texto in ESPECIALES:
        return ESPECIALES[texto]
    decena, _, unidad = texto.partition(" y ")
    if decena in DECENAS and (not unidad or unidad in UNIDADES):
        return DECENAS[decena] + UNIDADES.get(unidad, 0)
    return None


def fecha_hablada(ahora: datetime) -> str:
    return f"{DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}"


def decir_hora(ahora: datetime) -> str:
    hora = ahora.hour % 12 or 12
    minutos = " en punto" if ahora.minute == 0 else f" y {ahora.minute}"
    if ahora.hour < 6:
        parte = "de la madrugada"
    elif ahora.hour < 12:
        parte = "de la mañana"
    elif ahora.hour < 20:
        parte = "de la tarde"
    else:
        parte = "de la noche"
    inicio = "Es la 1" if hora == 1 else f"Son las {hora}"
    return f"{inicio}{minutos} {parte}."


def decir_fecha(ahora: datetime) -> str:
    return f"Hoy es {fecha_hablada(ahora)}."


# Respuestas de la ruta rápida que no son herramientas.
CAPACIDADES = (
    "Puedo con seis cosas: música y vídeos; tu PC, como programas, ventanas, volumen, mouse y apagado; "
    "agenda, recordatorios y notas; buscar en internet, noticias y clima; mirar tu pantalla y aconsejarte; "
    "y conversar, enseñarte o leerte documentos y correos. ¿Con cuál empezamos?"
)


def que_puedo_hacer(ahora: datetime) -> str:
    return CAPACIDADES


LOCALES = {"decir_hora": decir_hora, "decir_fecha": decir_fecha, "que_puedo_hacer": que_puedo_hacer}


def _cantidad(cuanto: str | None, poco: int, normal: int, mucho: int) -> int:
    cuanto = (cuanto or "").strip()
    if cuanto in ("un poco", "un poquito"):
        return poco
    if cuanto in ("bastante", "mucho"):
        return mucho
    return normal


def _fija(nombre: str, argumentos: dict | None = None):
    return lambda m: (nombre, argumentos or {})


def _volumen(nombre: str):
    return lambda m: (nombre, {"pasos": _cantidad(m["cuanto"], 2, 5, 10)})


def _volumen_exacto(m: re.Match):
    valor = m["valor"]
    porcentaje = VOLUMENES_FIJOS[valor] if valor in VOLUMENES_FIJOS else numero(valor)
    if porcentaje is None or porcentaje > 100:
        return None
    return "fijar_volumen", {"porcentaje": porcentaje}


def _con_segundos(nombre: str):
    def regla(m: re.Match):
        if m["fijo"]:
            return nombre, {"segundos": 60 if m["fijo"] == "un minuto" else 30}
        if not m["n"]:
            return nombre, {"segundos": 10}
        cantidad = numero(m["n"])
        if not cantidad:
            return None
        return nombre, {"segundos": cantidad * 60 if m["unidad"].startswith("minuto") else cantidad}
    return regla


def _con_minutos(nombre: str):
    def regla(m: re.Match):
        if not m["n"]:
            return nombre, {}
        minutos = numero(m["n"])
        return (nombre, {"minutos": minutos}) if minutos else None
    return regla


def _reproducir(m: re.Match):
    busqueda = m["busqueda"].removeprefix("a ")
    palabras = busqueda.split()
    if (
        len(palabras) > MAX_PALABRAS_BUSQUEDA
        or busqueda in GENERICOS
        or palabras[0] in INICIOS_DUDOSOS
        or NO_ES_MUSICA & set(palabras)
        or CONECTORES.search(busqueda)
    ):
        return None
    return "reproducir_en_youtube", {"busqueda": busqueda}


def _abrir(m: re.Match):
    destino = m["destino"]
    if destino == "youtube":
        return "abrir_youtube", {}
    if destino in WEBS:
        return "abrir_web", {"url": WEBS[destino]}
    if (destino in ALIAS or destino in PROCESOS) and destino not in PROGRAMAS_DUDOSOS:
        return "abrir_programa", {"nombre": destino}
    carpeta = destino.removeprefix("carpeta ").removeprefix("de ").removeprefix("mis ")
    if carpeta in CARPETAS and (destino.startswith("carpeta") or carpeta in CARPETAS_SIN_DECIR_CARPETA):
        return "abrir_carpeta", {"nombre": carpeta}
    return None


def _cerrar(m: re.Match):
    destino = m["destino"]
    if destino in ("ventana", "esta ventana"):
        return "cerrar_ventana", {}
    if destino in PROCESOS:
        return "cerrar_programa", {"nombre": destino}
    return None


def _clic(m: re.Match):
    boton = {"derecho": "derecho", "central": "medio", "del medio": "medio"}.get(m["boton"] or "", "izquierdo")
    argumentos = {"boton": boton, "veces": 2 if m["doble"] else 1}
    if "descripcion" not in m.groupdict():
        return "hacer_clic", argumentos
    descripcion = m["descripcion"]
    if len(descripcion.split()) > MAX_PALABRAS_CLIC or CONECTORES.search(descripcion):
        return None
    return "clic_en", {"descripcion": descripcion, **argumentos}


def _mover(m: re.Match):
    return "mover_mouse", {"direccion": m["direccion"], "pixeles": _cantidad(m["cuanto"], 50, 100, 300)}


def _desplazar(m: re.Match):
    direccion = {"baja": "abajo", "sube": "arriba"}.get(m["direccion"], m["direccion"])
    return "desplazar", {"direccion": direccion, "cantidad": _cantidad(m["cuanto"], 3, 5, 10)}


REGLAS = [(re.compile(patron), regla) for patron, regla in [
    (r"(?:que hora es|que horas son|dime la hora|la hora|me dices la hora)(?: ahora)?", _fija("decir_hora")),
    (r"que (?:dia|fecha) es(?: hoy)?|a que (?:dia|fecha) estamos(?: hoy)?|a cuanto estamos(?: hoy)?"
     r"|dime la fecha|la fecha de hoy|que dia de la semana es(?: hoy)?", _fija("decir_fecha")),
    (r"(?:que|cuales) (?:cosas )?(?:puedes|sabes) hacer|que haces|para que sirves|en que me (?:puedes )?ayudar"
     r"|ayuda|ayudame|como te uso|que te puedo pedir", _fija("que_puedo_hacer")),
    (r"buenos dias|(?:dame |dime )?(?:mi resumen|(?:el |mi )?resumen (?:del dia|de hoy))(?: del dia)?|que hay (?:para )?hoy",
     _fija("resumen_del_dia")),
    (rf"pausa|pausalo|pausala|pon pausa|ponle pausa|(?:pausa|para|deten) {MEDIA}", _fija("pausar_reanudar")),
    (rf"reanuda|reanudalo|reanudala|play|dale play|dale a play|quita la pausa|quitale la pausa"
     rf"|(?:reanuda|continua|sigue con) {MEDIA}", _fija("pausar_reanudar")),
    (r"(?:(?:pon|pasa a|pasa al|ve a|ve al) )?(?:el )?(?:siguiente|proximo) video|(?:el )?video siguiente",
     _fija("siguiente_video")),
    (r"(?:(?:pon|pasa a|salta a|ve a) )?(?:la |el )?(?:siguiente|proxima)(?: cancion| tema| pista)?"
     r"|(?:pasa|cambia|salta)(?:le)? de (?:cancion|tema)|saltala|salta esta(?: cancion)?|otra cancion",
     _fija("siguiente")),
    (r"(?:(?:pon|vuelve a|regresa a|ve a) )?(?:la |el )?(?:anterior(?: cancion| tema| pista| video)?"
     r"|(?:cancion|tema|pista|video) anterior)", _fija("anterior")),
    (rf"(?:(?:pon|sube|baja|deja|ajusta|cambia|fija) )?{VOLUMEN} (?:al|a|en|hasta el|hasta)"
     rf" (?P<valor>maximo|tope|minimo|la mitad|{NUMERO}){PORCENTAJE}", _volumen_exacto),
    (rf"volumen (?P<valor>{NUMERO}){PORCENTAJE}", _volumen_exacto),
    (rf"(?:sube {VOLUMEN}|subele(?: al? {VOLUMEN})?|mas volumen){CUANTO}", _volumen("subir_volumen")),
    (rf"(?:baja {VOLUMEN}|bajale(?: al? {VOLUMEN})?|menos volumen){CUANTO}", _volumen("bajar_volumen")),
    (r"silencia(?:lo)?|mutea(?:lo)?|mute|quita(?:le)? el (?:sonido|audio)|quita(?:le)? el silencio|activa el sonido"
     rf"|silencia (?:(?:el |la )?(?:volumen|sonido|todo|musica)|{PC})|apaga el sonido(?: del? {PC})?", _fija("silenciar")),
    (r"(?:(?:pon|ponlo|ponla|ponle|activa|quita|quitale|sal de|desactiva)(?: el video)?(?: en)? )?(?:la )?pantalla completa",
     _fija("pantalla_completa")),
    (rf"(?:adelanta|adelantalo|adelantala|adelantale|avanza|avanzalo|avanzala)(?: el video| la cancion)?{DURACION}",
     _con_segundos("adelantar")),
    (rf"(?:retrocede|retrocedelo|atrasa|atrasalo|rebobina)(?: el video| la cancion)?{DURACION}",
     _con_segundos("retroceder")),
    # "regresa" a secas puede ser volver atrás en el navegador.
    (rf"regresa (?:el video|la cancion){DURACION}", _con_segundos("retroceder")),
    (rf"regresa{DURACION_EXACTA}", _con_segundos("retroceder")),
    (r"(?:pon|ponme|reproduce|reproduceme|quiero escuchar)"
     r"(?: (?:(?:la |una )?(?:musica|cancion|canciones|tema|temas|video|videos|algo) de|la cancion|el video de))?"
     r" (?P<busqueda>.+?)(?: en youtube)?", _reproducir),
    (rf"abre(?:me)? {ARTICULO}(?P<destino>.+)", _abrir),
    (rf"cierra(?:me)? {ARTICULO}(?P<destino>.+)", _cerrar),
    (rf"{CLIC}{BOTON}(?: aqui| ahi)?", _clic),
    (rf"{CLIC}{BOTON} (?:en|sobre) (?:(?:el|la|los|las) )?(?P<descripcion>.+)", _clic),
    (rf"(?P<direccion>baja|sube) (?:la )?(?:pagina|web){CUANTO}", _desplazar),
    (rf"(?:haz scroll|scroll|desplazate|desplaza la pagina)(?: hacia)? (?P<direccion>abajo|arriba){CUANTO}", _desplazar),
    (rf"(?:apaga|apagame) {PC}{MINUTOS}", _con_minutos("apagar")),
    (rf"(?:reinicia|reiniciame) {PC}{MINUTOS}", _con_minutos("reiniciar")),
    (rf"(?:cancela|anula|deten|para) (?:el )?(?:apagado|reinicio)|no (?:lo )?(?:apagues|reinicies)(?: {PC})?",
     _fija("cancelar_apagado")),
    (r"minimiza todo|muestra el escritorio|ensename el escritorio", _fija("minimizar_todo")),
    (r"(?:haz|toma|saca) una captura(?: de pantalla)?|captura (?:la )?pantalla", _fija("captura_pantalla")),
    (r"maximiza(?:la)?(?: la ventana| esta ventana)?", _fija("maximizar_ventana")),
    (rf"bloquea {PC}", _fija("bloquear")),
    (rf"suspende {PC}", _fija("suspender")),
    (rf"(?:mueve|lleva|pon) el {RATON} (?:a la |hacia la |hacia |para la |a )?(?P<direccion>derecha|izquierda|arriba|abajo)"
     rf"{CUANTO}", _mover),
    (rf"(?:mueve|lleva|pon) el {RATON} (?:al|en el) centro(?: de la pantalla)?", _fija("mover_mouse", {"posicion": "centro"})),
]]


def _palabras(texto: str) -> tuple[list[str], list[str]] | None:
    """Palabras tal como llegaron y normalizadas, sin "jarvis" ni "por favor" en los extremos.

    None si quedan comas o cortesías entre medias: "pausa, sube el volumen" son dos órdenes.
    """
    crudas, limpias = [], []
    for palabra in texto.replace("%", " % ").split():
        limpia = normalizar(palabra.strip(PUNTUACION))
        if limpias and limpias[-1] == "por" and limpia == "favor":
            crudas[-1], limpias[-1] = f"{crudas[-1]} {palabra}", "porfavor"
        elif limpia:
            crudas.append(palabra)
            limpias.append(limpia)
    while limpias and limpias[0] in CORTESIA:
        del crudas[0], limpias[0]
    while limpias and limpias[-1] in CORTESIA:
        del crudas[-1], limpias[-1]
    if CORTESIA & set(limpias) or any(palabra.rstrip(".!?").endswith((",", ";")) for palabra in crudas[:-1]):
        return None
    return [palabra.strip(PUNTUACION) for palabra in crudas], limpias


def _como_se_dijo(valor, originales: list[str], limpias: list[str]):
    """El trozo de la frase con sus tildes y mayúsculas ("Ñengo Flow", no "nengo flow")."""
    if not isinstance(valor, str):
        return valor
    trozo = valor.split()
    for inicio in range(len(limpias) - len(trozo) + 1):
        if limpias[inicio:inicio + len(trozo)] == trozo:
            return " ".join(originales[inicio:inicio + len(trozo)])
    return valor


def interpretar(texto: str) -> tuple[str, dict] | None:
    """(herramienta, argumentos) si la frase es una orden frecuente sin ambigüedad; si no, None."""
    palabras = _palabras(texto)
    if not palabras or not palabras[1]:
        return None
    originales, limpias = palabras
    frase = " ".join(limpias)
    for patron, regla in REGLAS:
        coincidencia = patron.fullmatch(frase)
        orden = regla(coincidencia) if coincidencia else None
        if orden:
            nombre, argumentos = orden
            return nombre, {clave: _como_se_dijo(valor, originales, limpias) for clave, valor in argumentos.items()}
    return None


def es_simple(texto: str) -> bool:
    """Una sola orden, sin "y", "luego", condiciones ni comas: el texto de su herramienta basta como respuesta."""
    frase = normalizar(texto)
    return not re.search(r"[,;]", frase) and not CONECTORES.search(frase)
