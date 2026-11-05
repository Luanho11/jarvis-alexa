import cerebro_profundo
import herramientas


def test_cada_funcion_se_ofrece_sola_o_dentro_de_un_grupo():
    nombres = [h["function"]["name"] for h in herramientas.HERRAMIENTAS]
    assert len(nombres) == len(set(nombres)) == 51
    sueltas = set(nombres) - herramientas.GRUPOS.keys()
    assert sueltas | herramientas.AGRUPADAS.keys() == set(herramientas.FUNCIONES)
    assert not sueltas & herramientas.AGRUPADAS.keys()


def test_desagrupar_traduce_al_nombre_individual_con_sus_argumentos():
    assert herramientas.desagrupar("volumen", {"accion": "fijar", "porcentaje": 30, "pasos": 2}) == (
        "fijar_volumen", {"porcentaje": 30},
    )
    assert herramientas.desagrupar("energia", {"accion": "apagar", "minutos": 2}) == ("apagar", {"minutos": 2})
    assert herramientas.desagrupar("clima", {"ciudad": "Lima"}) == ("clima", {"ciudad": "Lima"})


def test_un_grupo_sin_accion_valida_explica_las_opciones():
    nombre, argumentos = herramientas.desagrupar("volumen", {"accion": "explotar"})
    assert herramientas.ejecutar(nombre, argumentos).startswith("Falta una accion válida para volumen: subir, bajar")


def test_los_grupos_ofrecen_la_accion_obligatoria():
    esquemas = {h["function"]["name"]: h["function"]["parameters"] for h in herramientas.HERRAMIENTAS}
    for grupo, (_, acciones) in herramientas.GRUPOS.items():
        assert esquemas[grupo]["required"] == ["accion"]
        assert esquemas[grupo]["properties"]["accion"]["enum"] == list(acciones)


def test_requeridos_existen_en_propiedades():
    for herramienta in herramientas.HERRAMIENTAS:
        parametros = herramienta["function"]["parameters"]
        assert set(parametros.get("required", [])) <= set(parametros["properties"])


def test_ejecutar_despacha_con_argumentos(monkeypatch):
    recibido = {}

    def fijar_volumen(porcentaje):
        recibido["porcentaje"] = porcentaje
        return "Volumen al 30 por ciento."

    monkeypatch.setitem(herramientas.FUNCIONES, "fijar_volumen", fijar_volumen)
    assert herramientas.ejecutar("fijar_volumen", {"porcentaje": 30}) == "Volumen al 30 por ciento."
    assert recibido == {"porcentaje": 30}


def test_nombre_desconocido_devuelve_texto():
    assert "volar" in herramientas.ejecutar("volar", {})


def test_error_devuelve_texto(monkeypatch):
    def falla():
        raise RuntimeError("sin pantalla")

    monkeypatch.setitem(herramientas.FUNCIONES, "silenciar", falla)
    assert herramientas.ejecutar("silenciar", {}) == "No pude hacer esa acción."
    assert herramientas.ejecutar("silenciar", {"inventado": 1}) == "No pude hacer esa acción."


def test_listas_de_seguridad_nombran_herramientas_reales():
    assert herramientas.LECTURA <= herramientas.FUNCIONES.keys()
    assert herramientas.PELIGROSAS <= herramientas.FUNCIONES.keys()
    assert not herramientas.LECTURA & herramientas.PELIGROSAS


def test_clics_frenados_tras_leer_y_mouse_fuera_del_cerebro_profundo():
    mouse = {"mover_mouse", "desplazar", "hacer_clic", "clic_en"}
    assert herramientas.PELIGROSAS & mouse == {"hacer_clic", "clic_en"}
    assert mouse <= cerebro_profundo.EXCLUIDAS


def test_herramientas_de_memoria():
    esquemas = {h["function"]["name"]: h["function"]["parameters"] for h in herramientas.HERRAMIENTAS}
    assert esquemas["recordar"]["properties"]["categoria"]["enum"] == list(herramientas.memoria.CATEGORIAS)
    assert esquemas["olvidar_todo"]["properties"] == {}
    assert "olvidar_todo" in herramientas.PELIGROSAS
    assert not {"que_sabes_de_mi", "olvidar_todo"} & herramientas.DIRECTAS
    assert "olvidar_todo" in cerebro_profundo.EXCLUIDAS


def test_leer_documentos_y_correos_son_lecturas():
    assert {"leer_documento", "leer_correos"} <= herramientas.LECTURA
    assert not {"leer_documento", "leer_correos"} & (herramientas.PELIGROSAS | herramientas.DIRECTAS)


def test_resumen_y_portapapeles_son_lecturas_y_programar_es_peligroso():
    assert {"resumen_del_dia", "leer_portapapeles"} <= herramientas.LECTURA
    assert {"programar_tarea", "borrar_programada"} <= herramientas.PELIGROSAS
    tipo = {h["function"]["name"]: h for h in herramientas.HERRAMIENTAS}["programar_tarea"]["function"]["parameters"]
    assert tipo["properties"]["tipo"]["enum"] == ["aviso", "resumen", "encargo"]
