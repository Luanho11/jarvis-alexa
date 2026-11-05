import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import get_slot, is_intent_name, is_request_type
from flask import Flask
from flask_ask_sdk.skill_adapter import (
    VERIFY_SIGNATURE_APP_CONFIG,
    VERIFY_TIMESTAMP_APP_CONFIG,
    SkillAdapter,
)

import cerebro_profundo
import panel
import voz
from acciones import aprendizaje, calculo, memoria, personas, vigilancia
from acciones.programas import normalizar
from acciones.recordatorios import iniciar_vigilante
from cerebro import Cerebro
from config import ALEXA_SKILL_ID

INVITACIONES = [
    "¿En qué te ayudo?",
    "Tú dirás.",
    "¿Qué tienes en mente?",
    "Jarvis a tu servicio, ¿qué hacemos?",
    "¿Por dónde empezamos?",
]
AYUDA = (
    "Háblame con normalidad: pídeme música, cambiar el volumen, "
    "abrir YouTube o agendar algo. ¿Qué necesitas?"
)
DESPEDIDA = "Hasta luego."
NO_ENTENDI = "No te entendí, ¿lo repites?"
ERROR = "Perdona, tuve un problema. ¿Lo intentas otra vez?"
REPREGUNTAS = [
    "¿Seguimos?",
    "Te escucho.",
    "Aquí sigo, dime.",
    "¿Qué más tienes en mente?",
    "Cuando quieras, sigo aquí.",
]
SIGO_PENSANDO = "Sigo con eso, dime 'y bien' en unos segundos."
PIDE_RESULTADO = "Di 'y bien' y te cuento."
SEGUIMIENTOS = {"y bien", "ya", "dime", "entonces", "y entonces", "y qué", "qué pasó", "listo"}
PREGUNTA_SIGO = "¿Sigo?"
SIGUE = {
    "si", "sigue", "continua", "si sigue", "si continua", "si por favor", "sigue por favor", "dale", "adelante",
    "claro", "si claro", "vale", "ok", "cuentame mas", "mas", "y que mas", "termina",
}
BASTA = {"no", "no gracias", "basta", "es suficiente", "suficiente", "asi esta bien", "ya esta bien"}
VALE = "Vale. ¿Algo más?"

# Alexa corta a los ~8 s contando el viaje por ngrok: pasado este tiempo se responde en dos pasos. Bajarlo no
# acelera nada (solo haría decir "y bien" más a menudo) y con la ruta rápida y gpt-oss en "low" casi nunca se llega.
ESPERA_RESPUESTA = 6.5

registro = logging.getLogger(__name__)


def saludo(ahora: datetime, nombre: str) -> str:
    if 6 <= ahora.hour < 12:
        inicio = "Buenos días"
    elif 12 <= ahora.hour < 20:
        inicio = "Buenas tardes"
    else:
        inicio = "Buenas noches"
    if nombre:
        inicio += f", {nombre}"
    return f"{inicio}. {random.choice(INVITACIONES)}"


def con_novedades(texto: str) -> str:
    """Antepone los encargos largos que terminaron mientras el usuario no hablaba."""
    terminados = cerebro_profundo.resultados_pendientes()
    if not terminados:
        return texto
    return f"Por cierto, terminé lo que me pediste: {' '.join(terminados)} {texto}"


def repregunta() -> str:
    return random.choice(REPREGUNTAS)


def es_seguimiento(texto: str) -> bool:
    return texto.lower().strip(" ¿?¡!.,") in SEGUIMIENTOS


def _frase(texto: str) -> str:
    return normalizar(texto.replace(",", " ")).strip(" ¿?¡!.")


def crear_app(cerebro, verificar=True):
    sb = SkillBuilder()
    sb.skill_id = ALEXA_SKILL_ID
    hilos = ThreadPoolExecutor(max_workers=4)
    pendientes = {}
    # Lo que falta por decir de una respuesta larga, hasta que el usuario diga "sí" a "¿sigo?".
    por_decir = {}

    def encadenar(previa, sesion, texto):
        return f"{previa.result()} {cerebro.responder(sesion, texto)}"

    def pensar(sesion, texto):
        """Devuelve la respuesta, o None si sigue pensando y queda pendiente para el siguiente turno."""
        previa = pendientes.pop(sesion, None)
        if previa is None:
            tarea = hilos.submit(cerebro.responder, sesion, texto)
        elif es_seguimiento(texto):
            tarea = previa
        else:
            tarea = hilos.submit(encadenar, previa, sesion, texto)
        try:
            return tarea.result(timeout=ESPERA_RESPUESTA)
        except TimeoutError:
            pendientes[sesion] = tarea
            return None

    def sesion_id(handler_input):
        return handler_input.request_envelope.session.session_id

    def terminar(handler_input):
        sesion = sesion_id(handler_input)
        pendientes.pop(sesion, None)
        por_decir.pop(sesion, None)
        personas.restablecer()
        # Aprende de la conversación en segundo plano (una llamada al LLM); no retrasa la despedida.
        aprendizaje.resumir_sesion(cerebro.olvidar(sesion), cerebro.completar)
        panel.emitir("espera")
        # Mientras vigila la pantalla, el HUD es donde salen los comentarios: no se esconde.
        if not vigilancia.vigilando():
            panel.ocultar_luego()

    def conversar(handler_input, texto):
        dicho, resto = voz.partir(con_novedades(texto))
        if resto:
            por_decir[sesion_id(handler_input)] = resto
            dicho = f"{dicho} {PREGUNTA_SIGO}"
        panel.emitir("respuesta", voz.texto_plano(dicho))
        return (
            handler_input.response_builder.speak(voz.a_ssml(dicho))
            .ask(PREGUNTA_SIGO if resto else repregunta())
            .response
        )

    @sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
    def inicio(handler_input):
        panel.mostrar()
        bienvenida = con_novedades(saludo(datetime.now(), memoria.nombre_usuario()))
        panel.emitir("respuesta", voz.texto_plano(bienvenida))
        return handler_input.response_builder.speak(voz.a_ssml(bienvenida)).ask(repregunta()).response

    @sb.request_handler(can_handle_func=is_intent_name("ConversarIntent"))
    def conversar_intent(handler_input):
        slot = get_slot(handler_input, "texto")
        texto = slot.value if slot else None
        if not texto:
            return conversar(handler_input, NO_ENTENDI)
        # Una petición directa ("pide a mi jarvis que...") llega sin LaunchRequest.
        panel.mostrar()
        panel.emitir("usuario", texto)
        resto = por_decir.pop(sesion_id(handler_input), None)
        if resto and _frase(texto) in SIGUE:
            return conversar(handler_input, resto)
        if resto and _frase(texto) in BASTA:
            return conversar(handler_input, VALE)
        inicio = time.perf_counter()
        respuesta = pensar(sesion_id(handler_input), texto)
        registro.info(
            "Alexa: %s en %.0f ms", "sigue pensando" if respuesta is None else "respuesta",
            (time.perf_counter() - inicio) * 1000,
        )
        if respuesta is None:
            return handler_input.response_builder.speak(SIGO_PENSANDO).ask(PIDE_RESULTADO).response
        return conversar(handler_input, respuesta)

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
    def ayuda(handler_input):
        return handler_input.response_builder.speak(AYUDA).ask(AYUDA).response

    @sb.request_handler(
        can_handle_func=lambda h: is_intent_name("AMAZON.StopIntent")(h)
        or is_intent_name("AMAZON.CancelIntent")(h)
        or is_intent_name("AMAZON.NavigateHomeIntent")(h)
    )
    def salir(handler_input):
        terminar(handler_input)
        return (
            handler_input.response_builder.speak(DESPEDIDA)
            .set_should_end_session(True)
            .response
        )

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
    def no_entendido(handler_input):
        return conversar(handler_input, NO_ENTENDI)

    @sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
    def sesion_terminada(handler_input):
        terminar(handler_input)
        return handler_input.response_builder.response

    @sb.exception_handler(can_handle_func=lambda handler_input, excepcion: True)
    def error(handler_input, excepcion):
        registro.exception("Fallo atendiendo la petición de Alexa")
        return conversar(handler_input, ERROR)

    app = Flask(__name__)
    app.config[VERIFY_SIGNATURE_APP_CONFIG] = verificar
    app.config[VERIFY_TIMESTAMP_APP_CONFIG] = verificar
    adaptador = SkillAdapter(skill=sb.create(), skill_id=ALEXA_SKILL_ID, app=app)
    adaptador.register(app=app, route="/alexa", endpoint="alexa")
    app.register_blueprint(panel.rutas)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Sin estos datos todo falla en silencio desde Alexa; mejor avisar al arrancar.
    if not ALEXA_SKILL_ID:
        raise SystemExit("Falta ALEXA_SKILL_ID en el archivo .env")
    cerebro = Cerebro()
    if not cerebro.clientes:
        raise SystemExit("Falta GROQ_API_KEY o GEMINI_API_KEY en el archivo .env")
    iniciar_vigilante()
    calculo.precargar()
    crear_app(cerebro).run(port=5000)
