import json
import threading
import time
from datetime import date, datetime, timedelta

import pytest

from acciones import aprendizaje, memoria


@pytest.fixture(autouse=True)
def archivos(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(tmp_path / "memoria.json"))
    monkeypatch.setenv("USO_ARCHIVO", str(tmp_path / "uso.json"))
    monkeypatch.setenv("DIARIO_ARCHIVO", str(tmp_path / "diario.json"))
    return tmp_path


def usar(herramienta, veces=1, **argumentos):
    for _ in range(veces):
        aprendizaje.registrar_uso(herramienta, argumentos)


def leer_uso():
    return json.loads(aprendizaje._archivo_uso().read_text(encoding="utf-8"))


def conversacion(*frases):
    mensajes = []
    for frase in frases:
        mensajes += [{"role": "user", "content": frase}, {"role": "assistant", "content": "Vale."}]
    return mensajes


class LLMFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.peticiones = []

    def __call__(self, mensajes):
        self.peticiones.append(mensajes)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def test_sin_uso_no_hay_preferencias():
    assert aprendizaje.preferencias_aprendidas() == ""
    assert aprendizaje.contexto() == ""


def test_aprende_musica_programas_volumen_y_modos(monkeypatch):
    monkeypatch.setattr(aprendizaje, "datetime", type("Reloj", (), {"now": staticmethod(lambda: datetime(2026, 11, 5, 22))}))
    usar("reproducir_en_youtube", 3, busqueda="Música de Bad Bunny")
    usar("abrir_en_spotify", 1, busqueda="bad bunny")
    usar("reproducir_en_youtube", 3, busqueda="Karol G")
    usar("reproducir_en_youtube", 2, busqueda="Shakira")
    usar("abrir_programa", 3, nombre="Chrome")
    usar("fijar_volumen", 3, porcentaje=32)
    usar("fijar_volumen", 1, porcentaje=80)
    usar("activar_modo", 3, nombre="trabajo")
    assert aprendizaje.preferencias_aprendidas() == (
        "Suele escuchar bad bunny y karol g; abre a menudo chrome; volumen habitual 30 %; "
        "usa el modo trabajo; suele hablarme por la noche."
    )


def test_no_guarda_texto_escrito_ni_busquedas(archivos):
    usar("escribir_texto", texto="mi contraseña secreta")
    usar("buscar_informacion", pregunta="síntomas de una enfermedad")
    usar("guardar_nota", titulo="Diario", contenido="algo privado")
    guardado = (archivos / "uso.json").read_text(encoding="utf-8")
    assert "contraseña" not in guardado and "enfermedad" not in guardado and "privado" not in guardado
    assert json.loads(guardado)["herramientas"] == {"escribir_texto": 1, "buscar_informacion": 1, "guardar_nota": 1}


def test_argumentos_raros_no_rompen_nada():
    usar("fijar_volumen", porcentaje="treinta")
    usar("fijar_volumen", porcentaje=True)
    usar("fijar_volumen", porcentaje=250)
    usar("abrir_programa", nombre=None)
    usar("abrir_programa")
    uso = leer_uso()
    assert uso["volumen"] == {"100": 1}
    assert "programas" not in uso


def test_los_habitos_viejos_pierden_peso_y_los_nuevos_entran(monkeypatch):
    monkeypatch.setattr(aprendizaje, "TOPE_CUENTA", 10)
    monkeypatch.setattr(aprendizaje, "MAX_CLAVES", 2)
    usar("abrir_programa", 10, nombre="word")
    usar("abrir_programa", 1, nombre="excel")
    usar("abrir_programa", 1, nombre="steam")
    cuenta = leer_uso()["programas"]
    assert cuenta == {"word": 5, "steam": 1}


def test_uso_roto_empieza_de_cero_y_lo_arregla(archivos):
    (archivos / "uso.json").write_text("{roto", encoding="utf-8")
    assert aprendizaje.preferencias_aprendidas() == ""
    usar("abrir_programa", 3, nombre="chrome")
    assert aprendizaje.preferencias_aprendidas().startswith("Abre a menudo chrome")


def test_si_no_puede_escribir_no_falla(monkeypatch):
    def sin_permiso(*_):
        raise PermissionError("bloqueado")

    monkeypatch.setattr(aprendizaje.memoria, "escribir_json", sin_permiso)
    usar("abrir_programa", nombre="chrome")


def test_hilos_a_la_vez_no_pierden_cuentas():
    hilos = [threading.Thread(target=usar, args=("abrir_programa", 25), kwargs={"nombre": "chrome"}) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    uso = leer_uso()
    # 200 es el tope: justo no se divide.
    assert uso["programas"] == {"chrome": 200}


def test_resumen_guarda_hechos_nuevos_y_el_diario():
    memoria.recordar("Vive en Lima")
    llm = LLMFalso(
        'Claro:\n```json\n{"hechos": [{"dato": "Se llama Ana", "categoria": "personal"}, '
        '{"dato": "Su perro se llama Toby", "categoria": "personas"}, {"dato": "vive en lima"}], '
        '"resumen": "Habló de su perro Toby."}\n```'
    )
    aprendizaje._resumir(conversacion("me llamo Ana", "mi perro se llama Toby"), llm)
    assert memoria.nombre_usuario() == "Ana"
    assert memoria.datos_guardados() == ["Se llama Ana", "Vive en Lima", "Su perro se llama Toby"]
    assert [d["origen"] for d in memoria.perfil()["datos"]] == ["usuario", "conversacion"]
    assert aprendizaje.recuerdos_recientes() == "Conversaciones anteriores: hoy, Habló de su perro Toby."
    sistema, usuario = llm.peticiones[0]
    assert "Vive en Lima" in sistema["content"]
    assert usuario["content"] == "Usuario: me llamo Ana\nJarvis: Vale.\nUsuario: mi perro se llama Toby\nJarvis: Vale."


def test_resumen_limita_hechos_y_recorta_lo_que_dijo_jarvis():
    hechos = [{"dato": f"Dato {numero}"} for numero in range(9)]
    llm = LLMFalso(json.dumps({"hechos": hechos, "resumen": ""}))
    mensajes = conversacion("hola", "adiós")
    mensajes[1]["content"] = "x" * 1000
    aprendizaje._resumir(mensajes, llm)
    assert memoria.datos_guardados() == [f"Dato {numero}" for numero in range(aprendizaje.MAX_HECHOS)]
    assert aprendizaje.recuerdos_recientes() == ""
    assert "x" * aprendizaje.LARGO_TURNO_JARVIS + "\n" in llm.peticiones[0][1]["content"]


@pytest.mark.parametrize("respuesta", ["no sé", "{roto", "[1, 2]", '{"hechos": "x", "resumen": 3}', None, ValueError("429")])
def test_respuestas_invalidas_o_fallos_del_llm_no_rompen(respuesta):
    aprendizaje._resumir(conversacion("hola", "adiós"), LLMFalso(respuesta))
    assert memoria.datos_guardados() == []
    assert aprendizaje.recuerdos_recientes() == ""


def test_resumen_con_memoria_rota_no_falla(archivos):
    (archivos / "memoria.json").write_text("[roto", encoding="utf-8")
    llm = LLMFalso('{"hechos": ["Le gusta el té"], "resumen": "Charlaron."}')
    aprendizaje._resumir(conversacion("hola", "adiós"), llm)
    assert (archivos / "memoria.json").read_text(encoding="utf-8") == "[roto"


def test_resumir_sesion_va_en_segundo_plano_y_hace_una_sola_llamada():
    soltar = threading.Event()
    terminado = threading.Event()

    def llm_lento(mensajes):
        soltar.wait(5)
        terminado.set()
        return '{"hechos": [], "resumen": "Hablaron del clima."}'

    aprendizaje.resumir_sesion(conversacion("hola", "¿qué tiempo hace?"), llm_lento)
    assert not terminado.is_set()
    soltar.set()
    assert terminado.wait(5)
    limite = time.monotonic() + 5
    while not aprendizaje.recuerdos_recientes() and time.monotonic() < limite:
        time.sleep(0.01)
    assert aprendizaje.recuerdos_recientes() == "Conversaciones anteriores: hoy, Hablaron del clima."


def test_resumir_sesion_corta_no_gasta_cuota():
    llm = LLMFalso("{}")
    aprendizaje.resumir_sesion(conversacion("pon música"), llm)
    aprendizaje.resumir_sesion([], llm)
    aprendizaje.resumir_sesion(None, llm)
    aprendizaje.resumir_sesion(["hola", None], llm)
    assert llm.peticiones == []


def test_diario_guarda_un_ano_y_recuerda_lo_ultimo(archivos):
    hoy = date.today()
    viejas = [{"fecha": (hoy - timedelta(days=dias)).isoformat(), "resumen": f"Tema {dias}."} for dias in (400, 40, 3, 1)]
    (archivos / "diario.json").write_text(json.dumps(viejas + [{"fecha": "mal"}, "x"]), encoding="utf-8")
    aprendizaje._anotar_diario("Tema de hoy")
    guardado = json.loads((archivos / "diario.json").read_text(encoding="utf-8"))
    assert [entrada["resumen"] for entrada in guardado] == ["Tema 40.", "Tema 3.", "Tema 1.", "Tema de hoy"]
    assert aprendizaje.recuerdos_recientes(2) == "Conversaciones anteriores: hoy, Tema de hoy; ayer, Tema 1."
    assert aprendizaje.recuerdos_recientes() == "Conversaciones anteriores: hoy, Tema de hoy; ayer, Tema 1; hace 3 días, Tema 3."
    assert aprendizaje.recuerdos_recientes(0) == ""


def test_diario_trae_la_conversacion_relacionada_con_el_pedido(archivos):
    hoy = date.today()
    entradas = [{"fecha": (hoy - timedelta(days=90)).isoformat(), "resumen": "Planearon su viaje a Cusco en julio."}]
    entradas += [{"fecha": hoy.isoformat(), "resumen": f"Charlaron de fútbol {numero}."} for numero in range(5)]
    (archivos / "diario.json").write_text(json.dumps(entradas), encoding="utf-8")
    texto = aprendizaje.recuerdos_recientes(2, pedido="¿qué te conté de mi viaje?")
    assert texto == "Conversaciones anteriores: hoy, Charlaron de fútbol 4; hace 90 días, Planearon su viaje a Cusco en julio."


def test_diario_roto_no_bloquea(archivos):
    (archivos / "diario.json").write_text("{", encoding="utf-8")
    assert aprendizaje.recuerdos_recientes() == ""


def test_contexto_junta_perfil_habitos_y_recuerdos_dentro_del_limite():
    memoria.recordar("Se llama Ana")
    usar("abrir_programa", 3, nombre="chrome")
    aprendizaje._anotar_diario("Habló de su viaje")
    texto = aprendizaje.contexto()
    assert texto.startswith("Se llama Ana. Por su uso: Abre a menudo chrome")
    assert texto.endswith("Conversaciones anteriores: hoy, Habló de su viaje.")
    memoria.recordar("Su hermana Marta vive en Madrid")
    for numero in range(300):
        memoria.recordar(f"Dato número {numero} con bastante texto para ocupar sitio en el prompt")
    lleno = aprendizaje.contexto(pedido="llama a mi hermana")
    assert len(lleno) <= 1500
    assert "Se llama Ana." in lleno and "Abre a menudo chrome" in lleno and "Habló de su viaje" in lleno
    assert "Su hermana Marta vive en Madrid" in lleno
    assert "Su hermana Marta" not in aprendizaje.contexto(pedido="pon música")


def test_que_sabes_de_mi():
    assert aprendizaje.que_sabes_de_mi().startswith("Todavía no sé nada")
    memoria.recordar("Se llama Ana")
    memoria.recordar("Le gusta el jazz")
    usar("fijar_volumen", 3, porcentaje=40)
    texto = aprendizaje.que_sabes_de_mi()
    assert texto.startswith("Recuerdo 1 datos del usuario")
    assert "Se llama Ana. Gustos: Le gusta el jazz." in texto
    assert "volumen habitual 40 %" in texto.lower()
    assert "memoria.json" in texto


@pytest.mark.parametrize("confirmacion", ["", "sí", "borra todo", "no, no lo borres todo", "si borras todo", "olvídalo"])
def test_olvidar_todo_exige_confirmacion_explicita(archivos, confirmacion):
    memoria.recordar("Se llama Ana")
    assert aprendizaje.olvidar_todo(confirmacion) == aprendizaje.PIDE_CONFIRMACION
    assert memoria.nombre_usuario() == "Ana"


@pytest.mark.parametrize("confirmacion", ["sí, bórralo todo", "Si borralo todo.", "sí, olvídalo todo jarvis"])
def test_olvidar_todo_borra_perfil_uso_y_diario(archivos, confirmacion):
    memoria.recordar("Se llama Ana")
    usar("abrir_programa", nombre="chrome")
    aprendizaje._anotar_diario("Charlaron")
    respuesta = aprendizaje.olvidar_todo(confirmacion)
    assert respuesta.startswith("Borré todo")
    assert list(archivos.iterdir()) == []
    assert aprendizaje.que_sabes_de_mi().startswith("Todavía no sé nada")


def test_resumen_corrige_lo_que_ya_no_es_cierto():
    memoria.recordar("Vive en Lima")
    memoria.recordar("Trabaja en un banco")
    memoria.recordar("Le gusta Lima")
    llm = LLMFalso(json.dumps({
        "hechos": [{"dato": "Vive en Cusco", "categoria": "personal"}],
        "olvidar": ["Trabaja en un banco", "Lima", 7],
        "resumen": "Contó que se mudó a Cusco y dejó el banco.",
    }))
    aprendizaje._resumir(conversacion("me mudé a cusco", "y dejé el banco"), llm)
    assert memoria.datos_guardados() == ["Vive en Cusco", "Le gusta Lima"]
    assert "Trabaja en un banco" in llm.peticiones[0][0]["content"]


@pytest.mark.parametrize("frase, datos", [
    ("me llamo ana y vivo en lima", ["Se llama Ana", "Vive en lima"]),
    ("tengo 30 años y trabajo en google", ["Tiene 30 años", "Trabaja en google"]),
    ("la verdad es que no me gusta el reguetón", ["No le gusta el reguetón"]),
    ("sí porque me gustan los perros, pero no los gatos", ["Le gustan los perros"]),
    ("mi mamá se llama rosa y mi perro se llama toby", ["Su mamá se llama Rosa", "Su perro se llama Toby"]),
    ("prefiero que me hables de usted", ["Prefiere que le hables de usted"]),
    ("mi comida favorita es el ceviche", ["Su comida favorita es el ceviche"]),
    ("Soy de Colombia. ¿Qué tiempo hace?", ["Es de Colombia"]),
])
def test_aprende_de_lo_que_cuenta_sin_llm(frase, datos):
    assert aprendizaje.aprender_de_frase(frase) == datos
    assert memoria.datos_guardados() == datos
    assert {d["origen"] for d in memoria.perfil()["datos"]} <= {"frase"}


@pytest.mark.parametrize("frase", [
    "qué me gusta escuchar", "si me gusta lo compro", "sabes si me gusta el café", "me gusta esta canción",
    "escribe me gusta el rock", "abre el estudio de grabación", "pon el concierto en vivo en youtube",
    "soy de los que madrugan", "me gusta mucho", "trabajo en casa hoy", "¿me gusta el rock?",
    "mi contraseña es 1234", "mi clave favorita es 99", "vivo en la calle 12345678", "me gusta tu idea",
    "me gusta " + "mucho " * 400, "", "   ",
])
def test_no_aprende_de_preguntas_ordenes_ni_datos_sensibles(frase):
    assert aprendizaje.aprender_de_frase(frase) == []
    assert memoria.datos_guardados() == []


def test_lo_que_cuenta_actualiza_lo_que_sabia():
    aprendizaje.aprender_de_frase("vivo en lima y me gusta el café")
    assert aprendizaje.aprender_de_frase("ya no vivo en lima ahora vivo en cusco") == ["Ya no vive en lima", "Vive en cusco"]
    assert aprendizaje.aprender_de_frase("ya no me gusta el café") == ["Ya no le gusta el café"]
    assert aprendizaje.aprender_de_frase("vivo en cusco") == []
    assert memoria.datos_guardados() == ["Vive en cusco"]


def test_aprender_de_frase_con_memoria_rota_no_falla(archivos):
    (archivos / "memoria.json").write_text("[roto", encoding="utf-8")
    assert aprendizaje.aprender_de_frase("vivo en lima") == []
    assert (archivos / "memoria.json").read_text(encoding="utf-8") == "[roto"


def test_conversacion_privada_no_aprende_hasta_que_termina(archivos):
    llm = LLMFalso('{"hechos": ["Le gusta el té"], "resumen": "Charlaron."}')
    assert aprendizaje.conversacion_privada().startswith("Modo privado")
    assert aprendizaje.aprender_de_frase("vivo en lima") == []
    usar("abrir_programa", nombre="chrome")
    aprendizaje.resumir_sesion(conversacion("hola", "adiós"), llm)
    assert llm.peticiones == [] and not (archivos / "uso.json").exists()
    assert memoria.recordar("Le gusta el té") == "Lo recordaré: Le gusta el té."
    assert aprendizaje.aprender_de_frase("vivo en lima") == ["Vive en lima"]


def test_conversacion_privada_se_puede_quitar():
    aprendizaje.conversacion_privada(True)
    assert aprendizaje.conversacion_privada("false") == "Vuelvo a aprender de lo que hablemos."
    assert aprendizaje.aprender_de_frase("vivo en lima") == ["Vive en lima"]
