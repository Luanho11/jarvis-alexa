import json
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from acciones import google

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "agenda.json"
MAX_PROXIMOS = 5
DIAS_PROXIMOS_GOOGLE = 60
# La agenda se lee y escribe desde varios hilos (conversaciones, encargos largos y el vigilante de avisos):
# sin candado, dos escrituras a la vez pierden eventos y una lectura a medias rompe el JSON.
_candado = threading.Lock()


def _archivo() -> Path:
    return Path(os.environ.get("AGENDA_ARCHIVO", ARCHIVO_POR_DEFECTO))


def _ahora() -> datetime:
    return datetime.now()


def _cargar() -> list[dict]:
    archivo = _archivo()
    if not archivo.exists():
        return []
    return json.loads(archivo.read_text(encoding="utf-8"))


def leer_eventos() -> list[dict]:
    with _candado:
        return _cargar()


def _guardar(eventos: list[dict]) -> None:
    _archivo().write_text(json.dumps(eventos, ensure_ascii=False, indent=2), encoding="utf-8")


def _dia(momento: datetime) -> str:
    dias = (momento.date() - _ahora().date()).days
    if dias == 0:
        return "Hoy"
    if dias == 1:
        return "Mañana"
    return f"El {momento:%d/%m}"


def _describir(momento: datetime) -> str:
    return f"{_dia(momento)} a las {momento:%H:%M}"


def _frase(evento: dict) -> str:
    momento = datetime.fromisoformat(evento["fecha_hora"])
    cuando = _dia(momento) if evento.get("todo_el_dia") else _describir(momento)
    return f"{cuando}: {evento['titulo']}."


def _con_google(locales: list[dict], desde: datetime, hasta: datetime) -> list[dict]:
    """Une los eventos de Google Calendar a los locales, sin repetir los que están en los dos."""
    if not google.agenda_activa():
        return locales
    eventos = list(locales)
    vistos = {(e["titulo"].strip().lower(), e["fecha_hora"]) for e in locales}
    for evento in google.eventos_google(desde, hasta):
        clave = (evento["titulo"].strip().lower(), evento["fecha_hora"])
        if clave not in vistos:
            vistos.add(clave)
            eventos.append(evento)
    return sorted(eventos, key=lambda evento: evento["fecha_hora"])


def agregar_evento(titulo: str, fecha_hora: str) -> str:
    try:
        # Se guarda en hora local sin zona: con zona ("...Z") fallaría al compararla con la hora local.
        momento = datetime.fromisoformat(fecha_hora).replace(tzinfo=None)
    except ValueError:
        return "No entendí la fecha del evento."
    with _candado:
        eventos = _cargar()
        eventos.append({"titulo": titulo, "fecha_hora": momento.isoformat(timespec="minutes")})
        _guardar(eventos)
    if google.agenda_activa():
        google.crear_evento_en_segundo_plano(titulo, momento)
    return f"Listo, agendé {titulo}. {_describir(momento)}."


def eventos_de(dia: date) -> list[dict]:
    """Eventos de un día ordenados por hora, con los de Google si está; se saltan los mal escritos a mano."""
    elegidos = []
    for evento in leer_eventos():
        try:
            momento = datetime.fromisoformat(evento["fecha_hora"]).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError):
            continue
        if momento.date() == dia:
            elegidos.append({**evento, "fecha_hora": momento.isoformat(timespec="minutes")})
    inicio = datetime.combine(dia, datetime.min.time())
    return _con_google(sorted(elegidos, key=lambda evento: evento["fecha_hora"]), inicio, inicio + timedelta(days=1))


def listar_eventos(fecha: str = "") -> str:
    if fecha:
        try:
            dia = date.fromisoformat(fecha)
        except ValueError:
            return "No entendí la fecha."
        elegidos = eventos_de(dia)
        vacio = "No tienes eventos ese día."
    else:
        eventos = sorted(leer_eventos(), key=lambda evento: evento["fecha_hora"])
        desde = _ahora() - timedelta(minutes=1)
        locales = [e for e in eventos if datetime.fromisoformat(e["fecha_hora"]) >= desde]
        elegidos = _con_google(locales, desde, desde + timedelta(days=DIAS_PROXIMOS_GOOGLE))[:MAX_PROXIMOS]
        vacio = "No tienes eventos próximos."
    if not elegidos:
        return vacio
    return " ".join(_frase(evento) for evento in elegidos)


def borrar_evento(titulo: str) -> str:
    with _candado:
        eventos = _cargar()
        restantes = [e for e in eventos if e["titulo"].lower() != titulo.strip().lower()]
        if len(restantes) == len(eventos):
            return "No encontré ese evento."
        _guardar(restantes)
    return f"Borré {titulo}."
