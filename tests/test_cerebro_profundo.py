from types import SimpleNamespace
from typing import ClassVar

import httpx2
import openai
import pytest
from openai.types.chat import ChatCompletionMessage

import cerebro_profundo
import herramientas


def mensaje(contenido=None, llamadas=()):
    return ChatCompletionMessage.model_validate({
        "role": "assistant",
        "content": contenido,
        "tool_calls": [
            {"id": f"llamada{i}", "type": "function", "function": {"name": nombre, "arguments": argumentos}}
            for i, (nombre, argumentos) in enumerate(llamadas)
        ] or None,
    })


def limite(mensaje="429"):
    peticion = httpx2.Request("POST", "https://llm.prueba")
    return openai.RateLimitError(mensaje, response=httpx2.Response(429, request=peticion), body=None)


class ClienteFalso:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.peticiones = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **peticion):
        self.peticiones.append(peticion)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return SimpleNamespace(choices=[SimpleNamespace(message=respuesta)])


class HiloFalso:
    """Guarda el hilo sin arrancarlo: el test decide cuándo corre la tarea."""

    creados: ClassVar[list] = []

    def __init__(self, target, args, daemon):
        self.target, self.args = target, args
        HiloFalso.creados.append(self)

    def start(self):
        pass

    def correr(self):
        self.target(*self.args)


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(tmp_path / "memoria.json"))
    monkeypatch.setattr(cerebro_profundo, "_tareas", [])
    monkeypatch.setattr(cerebro_profundo, "_pendientes", [])
    monkeypatch.setattr(cerebro_profundo, "PAUSA_LIMITE", 0)
    monkeypatch.setattr(cerebro_profundo.threading, "Thread", HiloFalso)
    monkeypatch.setattr(HiloFalso, "creados", [])
    eventos, avisos = [], []
    monkeypatch.setattr(cerebro_profundo.panel, "emitir", lambda tipo, texto="": eventos.append((tipo, texto)))
    monkeypatch.setattr(cerebro_profundo.recordatorios, "avisar", avisos.append)
    return SimpleNamespace(eventos=eventos, avisos=avisos)


def usar(monkeypatch, *clientes):
    monkeypatch.setattr(cerebro_profundo, "crear_clientes", lambda: [(c, f"modelo{i}") for i, c in enumerate(clientes)])


def test_responde_al_instante_y_entrega_al_terminar(monkeypatch, entorno):
    monkeypatch.setattr(herramientas, "ejecutar", lambda nombre, args: "Encontré tres precios.")
    cliente = ClienteFalso(mensaje(llamadas=[("buscar_informacion", '{"pregunta": "precio tele"}')]), mensaje("Comparé las teles."))
    usar(monkeypatch, cliente)

    assert cerebro_profundo.encargar_tarea("compara precios de teles") == "Me pongo con eso, te aviso cuando termine."
    assert cliente.peticiones == []
    assert cerebro_profundo.estado_tareas() == "Sigo con compara precios de teles."

    HiloFalso.creados[0].correr()
    assert entorno.avisos == ["Comparé las teles."]
    assert ("accion", "Tarea: buscar_informacion") in entorno.eventos
    assert cerebro_profundo.estado_tareas() == "Comparé las teles."
    assert cerebro_profundo.resultados_pendientes() == ["Comparé las teles."]
    assert cerebro_profundo.resultados_pendientes() == []
    assert cliente.peticiones[1]["messages"][-1] == {"role": "tool", "tool_call_id": "llamada0", "content": "Encontré tres precios."}


def test_no_ofrece_ni_ejecuta_herramientas_excluidas(monkeypatch):
    nombres = ["encargar_tarea", "estado_tareas", "apagar", "buscar_informacion"]
    monkeypatch.setattr(herramientas, "HERRAMIENTAS", [{"function": {"name": n}} for n in nombres])
    ejecutadas = []
    monkeypatch.setattr(herramientas, "ejecutar", lambda nombre, args: ejecutadas.append(nombre) or "ok")
    cliente = ClienteFalso(mensaje(llamadas=[("apagar", "{}"), ("encargar_tarea", '{"descripcion": "otra"}')]), mensaje("Listo."))
    usar(monkeypatch, cliente)

    cerebro_profundo.encargar_tarea("investiga algo")
    HiloFalso.creados[0].correr()
    assert [h["function"]["name"] for h in cliente.peticiones[0]["tools"]] == ["buscar_informacion"]
    assert ejecutadas == []
    assert "no está disponible" in cliente.peticiones[1]["messages"][-1]["content"]


def test_tras_leer_internet_no_escribe_ni_cierra_nada(monkeypatch):
    ejecutadas = []
    monkeypatch.setattr(herramientas, "ejecutar", lambda nombre, args: ejecutadas.append(nombre) or "ok")
    cliente = ClienteFalso(
        mensaje(llamadas=[("escribir_texto", '{"texto": "hola"}'), ("leer_nota", '{"titulo": "web"}')]),
        mensaje(llamadas=[("cerrar_programa", '{"nombre": "word"}'), ("crear_documento", '{"titulo": "a", "contenido": "b"}')]),
        mensaje("Listo."),
    )
    usar(monkeypatch, cliente)

    cerebro_profundo.encargar_tarea("resume mi nota web")
    HiloFalso.creados[0].correr()
    assert ejecutadas == ["escribir_texto", "leer_nota", "crear_documento"]
    assert cliente.peticiones[2]["messages"][-2]["content"] == herramientas.BLOQUEADA


def test_maximo_dos_tareas_a_la_vez(monkeypatch):
    usar(monkeypatch, ClienteFalso(mensaje("a")))
    cerebro_profundo.encargar_tarea("uno")
    cerebro_profundo.encargar_tarea("dos")
    assert "2 tareas en marcha" in cerebro_profundo.encargar_tarea("tres")
    assert len(HiloFalso.creados) == 2
    HiloFalso.creados[0].correr()
    assert cerebro_profundo.encargar_tarea("tres") == "Me pongo con eso, te aviso cuando termine."


def test_reintenta_una_vez_si_hay_limite_y_luego_pasa_al_respaldo(monkeypatch, entorno):
    principal = ClienteFalso(limite(), limite())
    respaldo = ClienteFalso(mensaje("Hecho con el respaldo."))
    usar(monkeypatch, principal, respaldo)
    cerebro_profundo.encargar_tarea("organiza mi semana")
    HiloFalso.creados[0].correr()
    assert len(principal.peticiones) == 2
    assert respaldo.peticiones[0]["model"] == "modelo1"
    assert entorno.avisos == ["Hecho con el respaldo."]

    reintento = ClienteFalso(limite(), mensaje("Al segundo intento."))
    usar(monkeypatch, reintento)
    cerebro_profundo.encargar_tarea("otra")
    HiloFalso.creados[1].correr()
    assert entorno.avisos[-1] == "Al segundo intento."


@pytest.mark.parametrize("aviso", ["quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier", "Rate limit reached on requests per day (RPD)"])
def test_limite_diario_pasa_al_respaldo_sin_esperar(monkeypatch, entorno, aviso):
    pausas = []
    monkeypatch.setattr(cerebro_profundo.time, "sleep", pausas.append)
    principal = ClienteFalso(limite(aviso))
    usar(monkeypatch, principal, ClienteFalso(mensaje("Hecho.")))
    cerebro_profundo.encargar_tarea("organiza mi semana")
    HiloFalso.creados[0].correr()
    assert len(principal.peticiones) == 1 and pausas == []
    assert entorno.avisos == ["Hecho."]


def test_si_todo_falla_avisa_con_honestidad(monkeypatch, entorno):
    usar(monkeypatch, ClienteFalso(openai.APIConnectionError(request=httpx2.Request("POST", "https://llm.prueba"))))
    cerebro_profundo.encargar_tarea("resume las noticias")
    HiloFalso.creados[0].correr()
    assert entorno.avisos == ["No pude terminar la tarea resume las noticias."]
    assert cerebro_profundo.resultados_pendientes() == entorno.avisos


def test_sin_tiempo_cierra_sin_herramientas(monkeypatch):
    monkeypatch.setattr(cerebro_profundo, "TIEMPO_MAXIMO", 0)
    cliente = ClienteFalso(mensaje("Lo que alcancé."))
    usar(monkeypatch, cliente)
    cerebro_profundo.encargar_tarea("investiga")
    HiloFalso.creados[0].correr()
    assert cliente.peticiones[0]["tool_choice"] == "none"
    assert cliente.peticiones[0]["timeout"] == cerebro_profundo.TIEMPO_CIERRE


def test_maximo_de_rondas(monkeypatch):
    monkeypatch.setattr(herramientas, "ejecutar", lambda nombre, args: "ok")
    bucle = [mensaje(llamadas=[("buscar_informacion", "{}")]) for _ in range(cerebro_profundo.MAX_RONDAS)]
    cliente = ClienteFalso(*bucle, mensaje("Terminé."))
    usar(monkeypatch, cliente)
    cerebro_profundo.encargar_tarea("investiga mucho")
    HiloFalso.creados[0].correr()
    assert len(cliente.peticiones) == cerebro_profundo.MAX_RONDAS + 1
    assert cliente.peticiones[-1]["tool_choice"] == "none"
    assert "tool_choice" not in cliente.peticiones[0]


def test_sin_descripcion_sin_clientes_y_sin_tareas(monkeypatch):
    assert cerebro_profundo.estado_tareas() == "No me has encargado ninguna tarea."
    assert cerebro_profundo.encargar_tarea("  ") == "Dime qué tarea quieres que haga."
    usar(monkeypatch)
    assert "ninguna IA" in cerebro_profundo.encargar_tarea("algo")
    assert HiloFalso.creados == []


def test_crear_clientes_prefiere_gemini_profundo_sin_duplicar(monkeypatch):
    config = cerebro_profundo.config
    monkeypatch.setattr(config, "GEMINI_API_KEY", "clave_gemini")
    monkeypatch.setattr(config, "GROQ_API_KEY", "clave_groq")
    monkeypatch.setattr(config, "MODELO_PROFUNDO", "profundo")
    monkeypatch.setattr(config, "MODELO_GEMINI", "rapido")
    assert [m for _, m in cerebro_profundo.crear_clientes()] == ["profundo", "rapido", config.MODELO_GROQ]
    assert all(c.max_retries == 0 for c, _ in cerebro_profundo.crear_clientes())

    monkeypatch.setattr(config, "MODELO_PROFUNDO", "rapido")
    assert [m for _, m in cerebro_profundo.crear_clientes()] == ["rapido", config.MODELO_GROQ]

    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert [m for _, m in cerebro_profundo.crear_clientes()] == [config.MODELO_GROQ]


def test_cuantos_pendientes_no_los_consume():
    cerebro_profundo._pendientes.extend(["Uno.", "Dos."])
    assert cerebro_profundo.cuantos_pendientes() == 2
    assert cerebro_profundo.resultados_pendientes() == ["Uno.", "Dos."]
    assert cerebro_profundo.cuantos_pendientes() == 0


def test_programar_tarea_no_se_usa_en_segundo_plano():
    assert cerebro_profundo._ejecutar("programar_tarea", '{"que": "x", "hora": "9:00"}', False) == (
        "Esa acción no está disponible en una tarea en segundo plano."
    )


def test_grupos_en_segundo_plano_quitan_solo_lo_excluido(monkeypatch):
    nombres = [h["function"]["name"] for h in cerebro_profundo._herramientas()]
    assert "mouse" not in nombres and "energia" in nombres
    assert cerebro_profundo._ejecutar("energia", '{"accion": "apagar"}', False) == (
        "Esa acción no está disponible en una tarea en segundo plano."
    )
