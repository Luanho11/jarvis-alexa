import herramientas


def test_hay_una_herramienta_por_funcion():
    nombres = [h["function"]["name"] for h in herramientas.HERRAMIENTAS]
    assert len(nombres) == len(set(nombres)) == 55
    assert set(nombres) == set(herramientas.FUNCIONES)


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
