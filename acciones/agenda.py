import json
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "agenda.json"
MAX_PROXIMOS = 5
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


def _describir(momento: datetime) -> str:
    dias = (momento.date() - _ahora().date()).days
    if dias == 0:
        dia = "Hoy"
    elif dias == 1:
        dia = "Mañana"
    else:
        dia = f"El {momento:%d/%m}"
    return f"{dia} a las {momento:%H:%M}"


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
    return f"Listo, agendé {titulo}. {_describir(momento)}."


def listar_eventos(fecha: str = "") -> str:
    eventos = sorted(leer_eventos(), key=lambda evento: evento["fecha_hora"])
    if fecha:
        try:
            dia = date.fromisoformat(fecha)
        except ValueError:
            return "No entendí la fecha."
        elegidos = [e for e in eventos if datetime.fromisoformat(e["fecha_hora"]).date() == dia]
        vacio = "No tienes eventos ese día."
    else:
        desde = _ahora() - timedelta(minutes=1)
        elegidos = [e for e in eventos if datetime.fromisoformat(e["fecha_hora"]) >= desde]
        elegidos = elegidos[:MAX_PROXIMOS]
        vacio = "No tienes eventos próximos."
    if not elegidos:
        return vacio
    return " ".join(
        f"{_describir(datetime.fromisoformat(e['fecha_hora']))}: {e['titulo']}." for e in elegidos
    )


def borrar_evento(titulo: str) -> str:
    with _candado:
        eventos = _cargar()
        restantes = [e for e in eventos if e["titulo"].lower() != titulo.strip().lower()]
        if len(restantes) == len(eventos):
            return "No encontré ese evento."
        _guardar(restantes)
    return f"Borré {titulo}."
