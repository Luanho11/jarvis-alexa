import html
import logging
import os
import threading
from datetime import datetime, timedelta

import requests

TIEMPO_LIMITE = 5
MAX_CORREOS = 10
MAX_FRAGMENTO = 200
MAX_ASUNTO = 120
DURACION_EVENTO = timedelta(hours=1)
# Evita mandar la clave a otro sitio si GOOGLE_SCRIPT_URL está mal copiada.
PREFIJO_URL = "https://script.google.com/macros/s/"
SIN_CONFIGURAR = "Para leer tu correo sigue la sección Google del README."

registro = logging.getLogger(__name__)


class GoogleNoDisponible(Exception):
    pass


def configurado() -> bool:
    return bool(os.getenv("GOOGLE_SCRIPT_URL") and os.getenv("GOOGLE_SCRIPT_CLAVE"))


def agenda_activa() -> bool:
    return configurado() and os.getenv("GOOGLE_AGENDA", "si").strip().lower() != "no"


def _llamar(accion: str, **datos) -> dict:
    url = os.getenv("GOOGLE_SCRIPT_URL", "").strip()
    clave = os.getenv("GOOGLE_SCRIPT_CLAVE", "").strip()
    if not (url and clave):
        raise GoogleNoDisponible(SIN_CONFIGURAR)
    if not url.startswith(PREFIJO_URL):
        raise GoogleNoDisponible("GOOGLE_SCRIPT_URL debe empezar por " + PREFIJO_URL)
    try:
        # POST para que la clave no quede en ninguna URL. Apps Script responde con una redirección 302
        # a googleusercontent que requests sigue con GET, que es lo que Google espera.
        respuesta = requests.post(url, json={"clave": clave, "accion": accion, **datos}, timeout=TIEMPO_LIMITE)
        respuesta.raise_for_status()
        resultado = respuesta.json()
    except requests.Timeout:
        raise GoogleNoDisponible("Google no respondió.") from None
    except requests.RequestException:
        raise GoogleNoDisponible("No pude conectar con Google.") from None
    except ValueError:
        # Si el script no se implementó con acceso "Cualquier usuario", Google devuelve su página de inicio de sesión.
        raise GoogleNoDisponible("Google no devolvió datos: revisa el acceso del Apps Script en el README.") from None
    if not isinstance(resultado, dict):
        raise GoogleNoDisponible("Google no devolvió datos: revisa el acceso del Apps Script en el README.")
    error = resultado.get("error")
    if error == "clave":
        raise GoogleNoDisponible("Google rechazó la clave: revisa GOOGLE_SCRIPT_CLAVE y la propiedad CLAVE del script.")
    if error:
        registro.warning("El puente de Google falló en %s: %s %s", accion, error, resultado.get("detalle", ""))
        raise GoogleNoDisponible("Google dio un error, inténtalo más tarde.")
    return resultado


def _recortar(texto, largo: int) -> str:
    texto = " ".join(html.unescape(str(texto or "")).split())
    return texto if len(texto) <= largo else texto[:largo].rsplit(" ", 1)[0] + "..."


def _remitente(de) -> str:
    """'Ana López <ana@x.com>' → 'Ana López'; sin nombre, la dirección."""
    de = str(de or "").strip()
    nombre = de.split("<", 1)[0].strip().strip('"').strip()
    return nombre or de.strip("<>") or "alguien"


def leer_correos(cantidad: int = 5, solo_no_leidos: bool = True) -> str:
    cantidad = min(max(int(cantidad or 5), 1), MAX_CORREOS)
    try:
        datos = _llamar("correos", cantidad=cantidad, solo_no_leidos=bool(solo_no_leidos))
    except GoogleNoDisponible as error:
        return str(error)
    correos = [correo for correo in datos.get("correos") or [] if isinstance(correo, dict)]
    if not correos:
        return "No tienes correos sin leer." if solo_no_leidos else "Tu bandeja de entrada está vacía."
    frases = []
    for correo in correos:
        frase = f"De {_remitente(correo.get('de'))}: «{_recortar(correo.get('asunto'), MAX_ASUNTO) or 'sin asunto'}»"
        fragmento = _recortar(correo.get("fragmento"), MAX_FRAGMENTO)
        frases.append(f"{frase}, dice: {fragmento}" if fragmento else frase)
    no_leidos = datos.get("no_leidos")
    mostrados = "el más reciente" if len(correos) == 1 else f"los {len(correos)} más recientes"
    if not solo_no_leidos:
        inicio = "Tu último correo." if len(correos) == 1 else f"Tus {len(correos)} últimos correos."
    elif isinstance(no_leidos, int) and no_leidos > len(correos):
        inicio = f"Tienes {no_leidos} sin leer; {mostrados}."
    else:
        inicio = f"Tienes {len(correos)} sin leer."
    return inicio + " " + " ".join(frase + "." for frase in frases)


def contar_no_leidos() -> int | None:
    """Correos sin leer en la bandeja de entrada, para el resumen del día; None si Google no está o falla."""
    if not configurado():
        return None
    try:
        no_leidos = _llamar("correos", cantidad=1, solo_no_leidos=True).get("no_leidos")
    except GoogleNoDisponible as error:
        registro.warning("Sin contador de correos: %s", error)
        return None
    return no_leidos if isinstance(no_leidos, int) else None


def _a_local(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone().replace(tzinfo=None)


def _con_zona(momento: datetime) -> str:
    # Con la zona del PC: así da igual la zona horaria del script.
    return momento.astimezone().isoformat(timespec="seconds")


def eventos_google(desde: datetime, hasta: datetime) -> list[dict]:
    """Eventos del calendario principal con el formato de agenda.json; [] si Google no está o falla."""
    try:
        datos = _llamar("eventos", desde=_con_zona(desde), hasta=_con_zona(hasta))
    except GoogleNoDisponible as error:
        registro.warning("Sin eventos de Google: %s", error)
        return []
    eventos = []
    for evento in datos.get("eventos") or []:
        try:
            titulo = str(evento["titulo"]).strip()
            if evento.get("todo_el_dia"):
                fecha_hora = datetime.fromisoformat(str(evento["dia"]))
            else:
                fecha_hora = _a_local(str(evento["inicio"]))
        except (KeyError, TypeError, ValueError):
            continue
        if titulo:
            nuevo = {"titulo": titulo, "fecha_hora": fecha_hora.isoformat(timespec="minutes")}
            if evento.get("todo_el_dia"):
                nuevo["todo_el_dia"] = True
            eventos.append(nuevo)
    return eventos


def crear_evento_google(titulo: str, momento: datetime) -> bool:
    try:
        datos = _llamar("crear_evento", titulo=titulo, inicio=_con_zona(momento), fin=_con_zona(momento + DURACION_EVENTO))
    except GoogleNoDisponible as error:
        registro.warning("No se creó el evento en Google: %s", error)
        return False
    return bool(datos.get("ok"))


def crear_evento_en_segundo_plano(titulo: str, momento: datetime) -> None:
    """Apps Script tarda 1-3 s: el usuario no espera, el evento ya quedó en la agenda local."""
    threading.Thread(target=crear_evento_google, args=(titulo, momento), daemon=True).start()
