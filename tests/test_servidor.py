import threading

import pytest

import servidor


class CerebroFalso:
    def __init__(self):
        self.recibido = []
        self.olvidadas = []

    def responder(self, sesion_id, texto):
        self.recibido.append((sesion_id, texto))
        return f"Respuesta a {texto} & más"

    def olvidar(self, sesion_id):
        self.olvidadas.append(sesion_id)
        return [{"role": "user", "content": "hola"}]

    def completar(self, mensajes):
        return ""


class CerebroLento(CerebroFalso):
    def __init__(self):
        super().__init__()
        self.listo = threading.Event()

    def responder(self, sesion_id, texto):
        self.listo.wait(timeout=5)
        return super().responder(sesion_id, texto)


class CerebroRoto(CerebroFalso):
    def responder(self, sesion_id, texto):
        raise RuntimeError("sin red")


def sobre(peticion):
    return {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "sesion-1",
            "application": {"applicationId": servidor.ALEXA_SKILL_ID},
            "user": {"userId": "usuario-1"},
        },
        "context": {
            "System": {
                "application": {"applicationId": servidor.ALEXA_SKILL_ID},
                "user": {"userId": "usuario-1"},
                "device": {"deviceId": "echo-1", "supportedInterfaces": {}},
                "apiEndpoint": "https://api.eu.amazonalexa.com",
            }
        },
        "request": {
            "requestId": "peticion-1",
            "timestamp": "2026-11-04T10:00:00Z",
            "locale": "es-ES",
            **peticion,
        },
    }


def intent(nombre, slots=None):
    return {"type": "IntentRequest", "intent": {"name": nombre, "slots": slots or {}}}


def conversar(texto):
    return intent("ConversarIntent", {"texto": {"name": "texto", "value": texto}})


@pytest.fixture
def cerebro():
    return CerebroFalso()


@pytest.fixture(autouse=True)
def hud(monkeypatch):
    eventos = []
    monkeypatch.setattr(servidor.panel, "emitir", lambda tipo, texto="": eventos.append((tipo, texto)))
    monkeypatch.setattr(servidor.panel, "mostrar", lambda: eventos.append(("mostrar", "")))
    monkeypatch.setattr(servidor.panel, "ocultar_luego", lambda: eventos.append(("ocultar", "")))
    return eventos


def enviar(cerebro, peticion):
    cliente = servidor.crear_app(cerebro, verificar=False).test_client()
    respuesta = cliente.post("/alexa", json=sobre(peticion))
    assert respuesta.status_code == 200
    return respuesta.get_json()["response"]


def voz(respuesta):
    return respuesta["outputSpeech"]["ssml"]


def test_inicio_saluda_por_el_nombre_y_deja_la_sesion_abierta(cerebro, monkeypatch):
    monkeypatch.setattr(servidor.memoria, "nombre_usuario", lambda: "Ana")
    respuesta = enviar(cerebro, {"type": "LaunchRequest"})
    assert ", Ana. " in voz(respuesta)
    assert any(frase in respuesta["reprompt"]["outputSpeech"]["ssml"] for frase in servidor.REPREGUNTAS)
    assert respuesta["shouldEndSession"] is False


def test_conversar_pasa_el_texto_al_cerebro_y_sigue_escuchando(cerebro):
    respuesta = enviar(cerebro, conversar("pon música de bad bunny"))
    assert cerebro.recibido == [("sesion-1", "pon música de bad bunny")]
    assert "Respuesta a pon música de bad bunny &amp; más" in voz(respuesta)
    assert any(frase in respuesta["reprompt"]["outputSpeech"]["ssml"] for frase in servidor.REPREGUNTAS)
    assert respuesta["shouldEndSession"] is False


def test_las_interjecciones_del_cerebro_salen_en_ssml_y_limpias_en_el_hud(hud):
    class CerebroExpresivo(CerebroFalso):
        def responder(self, sesion_id, texto):
            return "{Bravo}, ganaste... otra vez."

    respuesta = enviar(CerebroExpresivo(), conversar("gané"))
    assert '<say-as interpret-as="interjection">bravo</say-as>, ganaste<break time="400ms"/> otra vez.' in voz(respuesta)
    assert hud[-1] == ("respuesta", "Bravo, ganaste... otra vez.")


def test_conversar_sin_texto_pide_repetir(cerebro):
    respuesta = enviar(cerebro, intent("ConversarIntent"))
    assert cerebro.recibido == []
    assert servidor.NO_ENTENDI in voz(respuesta)


@pytest.mark.parametrize(
    "nombre", ["AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.NavigateHomeIntent"]
)
def test_salir_se_despide_cierra_y_olvida(cerebro, nombre):
    respuesta = enviar(cerebro, intent(nombre))
    assert servidor.DESPEDIDA in voz(respuesta)
    assert respuesta["shouldEndSession"] is True
    assert cerebro.olvidadas == ["sesion-1"]


def test_fin_de_sesion_olvida(cerebro):
    enviar(cerebro, {"type": "SessionEndedRequest", "reason": "USER_INITIATED"})
    assert cerebro.olvidadas == ["sesion-1"]


def test_ayuda(cerebro):
    respuesta = enviar(cerebro, intent("AMAZON.HelpIntent"))
    assert servidor.AYUDA in voz(respuesta)
    assert respuesta["shouldEndSession"] is False


def test_fallback_pide_repetir(cerebro):
    respuesta = enviar(cerebro, intent("AMAZON.FallbackIntent"))
    assert servidor.NO_ENTENDI in voz(respuesta)


def test_error_del_cerebro_no_tumba_la_skill():
    respuesta = enviar(CerebroRoto(), conversar("hola"))
    assert servidor.ERROR in voz(respuesta)
    assert respuesta["shouldEndSession"] is False


def test_con_verificacion_rechaza_peticiones_sin_firma(cerebro):
    cliente = servidor.crear_app(cerebro).test_client()
    respuesta = cliente.post("/alexa", json=sobre({"type": "LaunchRequest"}))
    assert respuesta.status_code == 400


@pytest.fixture
def lento(monkeypatch):
    monkeypatch.setattr(servidor, "ESPERA_RESPUESTA", 0.05)
    cerebro = CerebroLento()
    cliente = servidor.crear_app(cerebro, verificar=False).test_client()

    def turno(peticion):
        return cliente.post("/alexa", json=sobre(peticion)).get_json()["response"]

    yield cerebro, turno
    cerebro.listo.set()


def test_si_tarda_avisa_y_entrega_al_decir_y_bien(lento):
    cerebro, turno = lento
    respuesta = turno(conversar("resume la historia de roma"))
    assert servidor.SIGO_PENSANDO in voz(respuesta)
    assert respuesta["shouldEndSession"] is False

    cerebro.listo.set()
    respuesta = turno(conversar("¿y bien?"))
    assert "Respuesta a resume la historia de roma" in voz(respuesta)
    assert cerebro.recibido == [("sesion-1", "resume la historia de roma")]


def test_si_sigue_sin_estar_repite_el_aviso(lento):
    cerebro, turno = lento
    turno(conversar("algo lento"))
    assert servidor.SIGO_PENSANDO in voz(turno(conversar("ya")))
    cerebro.listo.set()
    assert "Respuesta a algo lento" in voz(turno(conversar("entonces")))


def test_pedido_nuevo_con_uno_pendiente_entrega_ambos_en_orden(lento):
    cerebro, turno = lento
    turno(conversar("primero"))
    cerebro.listo.set()
    respuesta = turno(conversar("segundo"))
    assert "Respuesta a primero &amp; más Respuesta a segundo &amp; más" in voz(respuesta)
    assert [texto for _, texto in cerebro.recibido] == ["primero", "segundo"]


def test_salir_descarta_lo_pendiente(lento):
    cerebro, turno = lento
    turno(conversar("primero"))
    turno(intent("AMAZON.StopIntent"))
    cerebro.listo.set()
    assert "Respuesta a y bien" in voz(turno(conversar("y bien")))


@pytest.mark.parametrize("texto", ["Y bien", "¿y bien?", "ya", "Entonces."])
def test_reconoce_frases_de_seguimiento(texto):
    assert servidor.es_seguimiento(texto)


def test_no_confunde_un_pedido_con_seguimiento():
    assert not servidor.es_seguimiento("ya puedes poner música")


def test_hud_aparece_al_abrir_y_muestra_la_conversacion(cerebro, hud, monkeypatch):
    monkeypatch.setattr(servidor, "saludo", lambda ahora, nombre: "Buenas, Ana.")
    monkeypatch.setattr(servidor.memoria, "nombre_usuario", lambda: "Ana")
    enviar(cerebro, {"type": "LaunchRequest"})
    enviar(cerebro, conversar("pon música"))
    assert hud == [
        ("mostrar", ""),
        ("respuesta", "Buenas, Ana."),
        ("mostrar", ""),
        ("usuario", "pon música"),
        ("respuesta", "Respuesta a pon música & más"),
    ]


def test_hud_queda_en_espera_y_se_oculta_al_salir(cerebro, hud):
    enviar(cerebro, intent("AMAZON.StopIntent"))
    assert hud == [("espera", ""), ("ocultar", "")]


def test_hud_sigue_visible_si_vigila_la_pantalla(cerebro, hud, monkeypatch):
    monkeypatch.setattr(servidor.vigilancia, "vigilando", lambda: True)
    enviar(cerebro, intent("AMAZON.StopIntent"))
    assert hud == [("espera", "")]


def test_hud_se_sirve_desde_el_mismo_servidor(cerebro):
    cliente = servidor.crear_app(cerebro, verificar=False).test_client()
    with cliente.get("/hud") as respuesta:
        assert respuesta.status_code == 200


def test_con_novedades_antepone_los_encargos_terminados(monkeypatch):
    monkeypatch.setattr(servidor.cerebro_profundo, "resultados_pendientes", lambda: ["El resumen está en Word."])
    assert servidor.con_novedades("Hola.") == "Por cierto, terminé lo que me pediste: El resumen está en Word. Hola."


def test_con_novedades_sin_encargos_deja_el_texto(monkeypatch):
    monkeypatch.setattr(servidor.cerebro_profundo, "resultados_pendientes", list)
    assert servidor.con_novedades("Hola.") == "Hola."


def test_al_salir_aprende_de_la_conversacion_en_segundo_plano(cerebro, monkeypatch):
    recibido = []
    monkeypatch.setattr(servidor.aprendizaje, "resumir_sesion", lambda historial, llamar: recibido.append((historial, llamar)))
    enviar(cerebro, intent("AMAZON.StopIntent"))
    assert recibido == [([{"role": "user", "content": "hola"}], cerebro.completar)]


LARGA = " ".join(f"Frase número {i} con varias palabras para contar." for i in range(1, 21))


class CerebroLargo(CerebroFalso):
    def responder(self, sesion_id, texto):
        self.recibido.append((sesion_id, texto))
        return LARGA


@pytest.fixture
def largo(monkeypatch):
    monkeypatch.setattr(servidor.aprendizaje, "resumir_sesion", lambda historial, llamar: None)
    cerebro = CerebroLargo()
    cliente = servidor.crear_app(cerebro, verificar=False).test_client()
    return cerebro, lambda peticion: cliente.post("/alexa", json=sobre(peticion)).get_json()["response"]


def test_respuesta_larga_dice_una_parte_y_pregunta_si_sigue(largo):
    cerebro, turno = largo
    primera = voz(turno(conversar("cuéntame una historia")))
    assert primera.endswith(f"{servidor.PREGUNTA_SIGO}</speak>")
    assert "Frase número 1 " in primera and "Frase número 20" not in primera

    dichas = [primera]
    respuesta = turno(conversar("Sí, sigue."))
    dichas.append(voz(respuesta))
    while servidor.PREGUNTA_SIGO in dichas[-1]:
        dichas.append(voz(turno(conversar("sí"))))
    assert "Frase número 20 con varias palabras para contar." in dichas[-1]
    assert cerebro.recibido == [("sesion-1", "cuéntame una historia")]
    todo = " ".join(dichas)
    assert all(f"Frase número {i} con" in todo for i in range(1, 21))


def test_no_corta_la_lectura_y_otra_pregunta_descarta_el_resto(largo):
    cerebro, turno = largo
    turno(conversar("cuéntame una historia"))
    assert servidor.VALE in voz(turno(conversar("no, gracias")))
    turno(conversar("cuéntame otra"))
    turno(conversar("¿qué hora es?"))
    assert [texto for _, texto in cerebro.recibido] == ["cuéntame una historia", "cuéntame otra", "¿qué hora es?"]


def test_respuesta_corta_no_pregunta_si_sigue(cerebro):
    respuesta = enviar(cerebro, conversar("hola"))
    assert servidor.PREGUNTA_SIGO not in voz(respuesta)


def test_al_salir_vuelve_a_hablar_normal(cerebro, monkeypatch):
    restablecidas = []
    monkeypatch.setattr(servidor.personas, "restablecer", lambda: restablecidas.append(True))
    monkeypatch.setattr(servidor.aprendizaje, "resumir_sesion", lambda historial, llamar: None)
    enviar(cerebro, intent("AMAZON.StopIntent"))
    assert restablecidas == [True]
