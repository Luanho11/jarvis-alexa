import logging
import os
import re
import threading
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import cerebro_profundo
from acciones import recordatorios
from acciones.memoria import escribir_json, leer_json
from acciones.programas import normalizar

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "programadas.json"
MAX_TAREAS = 20
# Cada encargo gasta varias de las ~20 peticiones diarias gratis de gemini-3.8-flash.
MAX_ENCARGOS_DIA = 3
MAX_LARGO = 500
# Si el PC estuvo apagado a la hora, pasada la ventana ya no se dispara: un aviso una hora tarde estorba.
VENTANA = timedelta(minutes=10)
TIPOS = ("aviso", "resumen", "encargo")
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
GRUPOS = {"todos": range(7), "laborables": range(5), "fines": (5, 6)}
SINONIMOS_DIAS = {
    "todos los dias": "todos", "diario": "todos", "cada dia": "todos", "a diario": "todos",
    "entre semana": "laborables", "de lunes a viernes": "laborables", "dias laborables": "laborables",
    "fin de semana": "fines", "fines de semana": "fines", "los fines de semana": "fines",
}
DESCRIPCION_GRUPOS = {"todos": "todos los días", "laborables": "de lunes a viernes", "fines": "los fines de semana"}
FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
HORA = re.compile(r"(\d{1,2})(?:[:.](\d{2}))?")
ARCHIVO_ROTO = "No puedo leer programadas.json; revísalo o bórralo para empezar de cero."

# El vigilante, las conversaciones y los encargos pueden leer y escribir a la vez.
_candado = threading.Lock()
registro = logging.getLogger(__name__)


def _archivo() -> Path:
    return Path(os.environ.get("PROGRAMADAS_ARCHIVO", ARCHIVO_POR_DEFECTO))


def _ahora() -> datetime:
    return datetime.now()


def _cargar() -> dict:
    """Lanza OSError o ValueError si el archivo no se puede leer: así nunca se sobrescribe lo que había."""
    archivo = _archivo()
    if not archivo.exists():
        return {"tareas": [], "encargos": {}}
    datos = leer_json(archivo)
    if not isinstance(datos, dict) or not isinstance(datos.get("tareas"), list):
        raise ValueError("programadas.json no tiene una lista de tareas")
    if not all(isinstance(tarea, dict) for tarea in datos["tareas"]):
        raise ValueError("programadas.json tiene tareas que no son objetos")
    return datos


def _leer_hora(texto) -> time | None:
    coincidencia = HORA.fullmatch(str(texto).strip())
    if not coincidencia:
        return None
    horas, minutos = int(coincidencia.group(1)), int(coincidencia.group(2) or 0)
    if horas > 23 or minutos > 59:
        return None
    return time(horas, minutos)


def _leer_dias(texto) -> str | None:
    """Forma guardada de los días: "todos", "laborables", "fines", "lunes,miércoles" o "AAAA-MM-DD"."""
    texto = str(texto).strip()
    if FECHA.fullmatch(texto):
        try:
            return date.fromisoformat(texto).isoformat()
        except ValueError:
            return None
    clave = " ".join(re.findall(r"\w+", normalizar(texto))) or "todos"
    clave = SINONIMOS_DIAS.get(clave, clave)
    if clave in GRUPOS:
        return clave
    sin_tildes = {normalizar(dia): dia for dia in DIAS}
    elegidos = set()
    for palabra in clave.split():
        if palabra in ("y", "e", "los", "las", "el", "cada"):
            continue
        # "sábados" y "domingos" en plural; los demás ya terminan en s.
        dia = sin_tildes.get(palabra) or sin_tildes.get(palabra.removesuffix("s"))
        if dia is None:
            return None
        elegidos.add(dia)
    if not elegidos:
        return None
    return ",".join(dia for dia in DIAS if dia in elegidos)


def _toca(dias: str, dia: date) -> bool:
    if FECHA.fullmatch(dias):
        return dias == dia.isoformat()
    if dias in GRUPOS:
        return dia.weekday() in GRUPOS[dias]
    return DIAS[dia.weekday()] in dias.split(",")


def _describir_dias(dias: str) -> str:
    if FECHA.fullmatch(dias):
        return f"el {date.fromisoformat(dias):%d/%m}"
    if dias in DESCRIPCION_GRUPOS:
        return DESCRIPCION_GRUPOS[dias]
    plurales = [dia if dia.endswith("s") else dia + "s" for dia in dias.split(",")]
    return "los " + (plurales[0] if len(plurales) == 1 else ", ".join(plurales[:-1]) + " y " + plurales[-1])


def _nombre(tarea: dict) -> str:
    if tarea.get("tipo") == "aviso":
        return f"el aviso {tarea['que']}"
    if tarea.get("tipo") == "encargo":
        return f"el encargo {tarea['que']}"
    return f"el {tarea['que']}"


def _describir(tarea: dict) -> str:
    return f"{_nombre(tarea)}, {_describir_dias(tarea['dias'])} a las {tarea['hora']}"


def _clave(tarea: dict) -> tuple:
    return normalizar(str(tarea.get("que", ""))), tarea.get("hora"), tarea.get("dias"), tarea.get("tipo")


def programar_tarea(que: str, hora: str, dias: str = "todos", tipo: str = "aviso") -> str:
    que = " ".join(str(que).split())
    tipo = normalizar(str(tipo)) or "aviso"
    if tipo not in TIPOS:
        return "El tipo debe ser aviso, resumen o encargo."
    if tipo == "resumen" and not que:
        que = "resumen del día"
    if not que:
        return "Dime qué quieres que haga."
    if len(que) > MAX_LARGO:
        return "Es demasiado largo; dímelo más corto."
    momento = _leer_hora(hora)
    if momento is None:
        return "Dime la hora como 7:30."
    dias = _leer_dias(dias)
    if dias is None:
        return "No entendí los días. Di todos, laborables, fines, unos días de la semana o una fecha."
    ahora = _ahora()
    inicio_hoy = datetime.combine(ahora.date(), momento)
    if FECHA.fullmatch(dias) and datetime.combine(date.fromisoformat(dias), momento) <= ahora:
        return "Esa fecha y hora ya pasaron."
    tarea = {
        "id": uuid.uuid4().hex[:8], "que": que, "hora": f"{momento:%H:%M}", "dias": dias, "tipo": tipo,
        # Programada a las 7:05 "cada día a las 7": empieza mañana, no al instante.
        "ultima": ahora.date().isoformat() if inicio_hoy <= ahora else None,
    }
    with _candado:
        try:
            datos = _cargar()
        except (OSError, ValueError):
            registro.warning("programadas.json ilegible", exc_info=True)
            return ARCHIVO_ROTO
        if any(_clave(guardada) == _clave(tarea) for guardada in datos["tareas"]):
            return "Eso ya estaba programado."
        if len(datos["tareas"]) >= MAX_TAREAS:
            return f"Ya tienes {MAX_TAREAS} tareas programadas; borra alguna primero."
        datos["tareas"].append(tarea)
        escribir_json(_archivo(), datos)
    aviso = f" Como mucho lanzo {MAX_ENCARGOS_DIA} encargos programados al día." if tipo == "encargo" else ""
    return f"Programado {_describir(tarea)}.{aviso}"


def _validas(tareas: list[dict]) -> list[dict]:
    """Las tareas bien escritas, con hora y días en su forma guardada (el archivo se puede editar a mano)."""
    validas = []
    for tarea in tareas:
        momento, dias = _leer_hora(tarea.get("hora", "")), _leer_dias(tarea.get("dias", ""))
        if momento is None or dias is None or not tarea.get("que"):
            registro.warning("Tarea mal escrita en programadas.json: %s", tarea)
            continue
        validas.append({**tarea, "hora": f"{momento:%H:%M}", "dias": dias})
    return validas


def listar_programadas() -> str:
    try:
        with _candado:
            tareas = _validas(_cargar()["tareas"])
    except (OSError, ValueError):
        return ARCHIVO_ROTO
    if not tareas:
        return "No tienes tareas programadas."
    tareas.sort(key=lambda tarea: tarea["hora"])
    cuantas = "1 tarea programada" if len(tareas) == 1 else f"{len(tareas)} tareas programadas"
    return f"Tienes {cuantas}: " + "; ".join(_describir(tarea) for tarea in tareas) + "."


def borrar_programada(que: str) -> str:
    objetivo = normalizar(str(que))
    if not objetivo:
        return "Dime qué tarea programada borro."
    with _candado:
        try:
            datos = _cargar()
        except (OSError, ValueError):
            return ARCHIVO_ROTO
        tareas = datos["tareas"]
        borradas = [t for t in tareas if normalizar(str(t.get("que", ""))) == objetivo]
        if not borradas:
            # "borra lo de la pastilla" cuando se guardó "tomar la pastilla": vale si solo hay una parecida.
            borradas = [t for t in tareas if objetivo in normalizar(str(t.get("que", "")))]
            if len(borradas) > 1:
                return "Hay varias parecidas; dime cuál exactamente."
        if not borradas:
            return "No encontré esa tarea programada."
        datos["tareas"] = [t for t in tareas if t not in borradas]
        escribir_json(_archivo(), datos)
    return f"Borré {borradas[0]['que']} de las tareas programadas."


def pendientes_de_hoy(ahora: datetime) -> list[dict]:
    """Avisos y encargos que aún tocan hoy (no los resúmenes). Lanza OSError o ValueError si el archivo está roto."""
    with _candado:
        tareas = _validas(_cargar()["tareas"])
    hoy = ahora.date()
    pendientes = []
    for tarea in tareas:
        fin = datetime.combine(hoy, _leer_hora(tarea["hora"])) + VENTANA
        hecha = tarea.get("ultima") == hoy.isoformat() or fin <= ahora
        if tarea.get("tipo") != "resumen" and _toca(tarea["dias"], hoy) and not hecha:
            pendientes.append(tarea)
    return sorted(pendientes, key=lambda tarea: tarea["hora"])


def _ejecutar(tarea: dict, saltada: bool) -> None:
    try:
        if saltada:
            recordatorios.avisar(f"Hoy ya lancé {MAX_ENCARGOS_DIA} encargos programados; me salto {tarea['que']}.")
        elif tarea.get("tipo") == "encargo":
            respuesta = cerebro_profundo.encargar_tarea(tarea["que"])
            if respuesta != cerebro_profundo.EMPEZADA:
                recordatorios.avisar(f"No pude empezar el encargo programado {tarea['que']}. {respuesta}")
        elif tarea.get("tipo") == "resumen":
            # resumen importa este módulo para contar las tareas de hoy: importarlo arriba sería circular.
            from acciones import resumen

            recordatorios.avisar(resumen.resumen_del_dia())
        else:
            recordatorios.avisar(f"Recordatorio: {tarea['que']}")
    except Exception:
        # En un hilo el error se perdería en silencio.
        registro.exception("Falló la tarea programada %s", tarea)


def revisar(ahora: datetime) -> None:
    """Dispara lo que toca en la ventana de 10 minutos. La llama el vigilante de recordatorios cada 30 s."""
    hoy = ahora.date()
    with _candado:
        try:
            datos = _cargar()
        except (OSError, ValueError):
            registro.warning("programadas.json ilegible; no reviso las tareas programadas", exc_info=True)
            return
        quedan, disparar, cambio = [], [], False
        for tarea in datos["tareas"]:
            momento, dias = _leer_hora(tarea.get("hora", "")), _leer_dias(tarea.get("dias", ""))
            if momento is None or dias is None or not tarea.get("que"):
                registro.warning("Tarea mal escrita en programadas.json: %s", tarea)
                quedan.append(tarea)
                continue
            inicio = datetime.combine(hoy, momento)
            unica = FECHA.fullmatch(dias) is not None
            if _toca(dias, hoy) and tarea.get("ultima") != hoy.isoformat() and inicio <= ahora < inicio + VENTANA:
                tarea["ultima"] = hoy.isoformat()
                disparar.append(tarea)
                cambio = True
                if unica:
                    continue
            elif unica and datetime.combine(date.fromisoformat(dias), momento) + VENTANA <= ahora:
                registro.info("Tarea programada vencida sin disparar: %s", tarea)
                cambio = True
                continue
            quedan.append(tarea)
        if not cambio:
            return
        cupo = datos.get("encargos")
        if not isinstance(cupo, dict) or cupo.get("fecha") != hoy.isoformat():
            cupo = {"fecha": hoy.isoformat(), "cuenta": 0}
        lanzar = []
        for tarea in disparar:
            saltada = tarea.get("tipo") == "encargo" and cupo["cuenta"] >= MAX_ENCARGOS_DIA
            if tarea.get("tipo") == "encargo" and not saltada:
                cupo["cuenta"] += 1
            lanzar.append((tarea, saltada))
        datos["tareas"], datos["encargos"] = quedan, cupo
        # Primero se guarda: si falla, no se dispara (se repetiría cada 30 s) ni se repite tras un reinicio.
        try:
            escribir_json(_archivo(), datos)
        except OSError:
            registro.exception("No pude guardar programadas.json; no disparo las tareas")
            return
    for tarea, saltada in lanzar:
        threading.Thread(target=_ejecutar, args=(tarea, saltada), daemon=True).start()
