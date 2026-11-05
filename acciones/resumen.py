import logging
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

import cerebro_profundo
from acciones import agenda, info, programadas, web

# Cabe en los ~6,5 s del servidor con margen; lo que no llegue a tiempo se omite.
TIEMPO_LIMITE = 4
MAX_LARGO = 600
MAX_CITAS = 4
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")

registro = logging.getLogger(__name__)


def _enumerar(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def _clima(_ahora: datetime) -> str:
    return web.pronostico_hoy()


def _citas(ahora: datetime) -> str:
    eventos = agenda.eventos_de(ahora.date())
    if not eventos:
        return "No tienes citas hoy."
    citas = [f"{evento['titulo']} a las {evento['fecha_hora'][11:16]}" for evento in eventos[:MAX_CITAS]]
    cuantas = "1 cita" if len(eventos) == 1 else f"{len(eventos)} citas"
    return f"Tienes {cuantas}: {_enumerar(citas)}."


def _programadas(ahora: datetime) -> str:
    tareas = programadas.pendientes_de_hoy(ahora)
    if not tareas:
        return ""
    return "Programado para hoy: " + _enumerar([f"{tarea['que']} a las {tarea['hora']}" for tarea in tareas]) + "."


def _encargos(_ahora: datetime) -> str:
    # Solo se cuentan: el texto de cada uno lo entrega el cerebro en el siguiente turno.
    terminados = cerebro_profundo.cuantos_pendientes()
    if not terminados:
        return ""
    if terminados == 1:
        return "Terminé 1 encargo; pregúntame por él."
    return f"Terminé {terminados} encargos; pregúntame por ellos."


def _titulares(_ahora: datetime) -> str:
    titulares = info.titulares(3)
    return "Titulares: " + ". ".join(titulares) + "." if titulares else ""


FUENTES = (_clima, _citas, _programadas, _encargos, _titulares)


def resumen_del_dia() -> str:
    """Fecha, clima, citas, tareas de hoy, encargos terminados y titulares, sin LLM y en ≤4 s."""
    ahora = datetime.now()
    hilos = ThreadPoolExecutor(max_workers=len(FUENTES))
    futuros = [hilos.submit(fuente, ahora) for fuente in FUENTES]
    wait(futuros, timeout=TIEMPO_LIMITE)
    # Sin esperar a la fuente colgada: su hilo acaba solo cuando vence el timeout de su petición.
    hilos.shutdown(wait=False, cancel_futures=True)
    partes = [f"Hoy es {programadas.DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]}."]
    for fuente, futuro in zip(FUENTES, futuros):
        if not futuro.done():
            registro.warning("El resumen omite %s: no llegó a tiempo", fuente.__name__)
            continue
        try:
            texto = futuro.result()
        except Exception:
            # Una fuente rota (sin red, archivo ilegible) no debe dejar sin resumen.
            registro.warning("El resumen omite %s", fuente.__name__, exc_info=True)
            continue
        if texto:
            partes.append(texto)
    texto = " ".join(partes)
    if len(texto) > MAX_LARGO:
        texto = texto[: MAX_LARGO - 3].rsplit(" ", 1)[0] + "..."
    return texto
