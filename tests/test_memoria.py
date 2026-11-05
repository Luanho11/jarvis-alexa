import json
import threading

import pytest

from acciones import memoria


@pytest.fixture(autouse=True)
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "memoria.json"
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(ruta))
    return ruta


def test_recordar_guarda_en_utf8_sin_dejar_temporales(archivo):
    assert memoria.recordar(" Su ciudad es Bogotá ") == "Lo recordaré: Su ciudad es Bogotá."
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert guardado["version"] == 2
    assert guardado["datos"]["personal"] == ["Su ciudad es Bogotá"]
    assert memoria.datos_guardados() == ["Su ciudad es Bogotá"]
    assert [ruta.name for ruta in archivo.parent.iterdir()] == ["memoria.json"]


def test_sin_archivo_no_hay_datos():
    assert memoria.datos_guardados() == []


def test_no_duplica_ni_guarda_vacios():
    memoria.recordar("Prefiere Spotify")
    assert memoria.recordar("prefiere spotify") == "Eso ya lo sabía."
    assert memoria.recordar("  ") == "No me dijiste qué recordar."
    assert memoria.datos_guardados() == ["Prefiere Spotify"]


def test_limite_descarta_lo_mas_antiguo(monkeypatch):
    monkeypatch.setattr(memoria, "MAX_DATOS", 2)
    for dato in ["uno", "dos", "tres"]:
        memoria.recordar(dato)
    assert memoria.datos_guardados() == ["dos", "tres"]


def test_olvidar_dato_por_coincidencia_parcial():
    memoria.recordar("Su perro se llama Toby")
    memoria.recordar("Vive en Lima")
    assert memoria.olvidar_dato("perro") == "Listo, lo olvidé."
    assert memoria.datos_guardados() == ["Vive en Lima"]


def test_olvidar_dato_inexistente_o_vacio():
    memoria.recordar("Vive en Lima")
    assert memoria.olvidar_dato("gato") == "No tenía guardado nada sobre eso."
    assert memoria.olvidar_dato("") == "No me dijiste qué olvidar."
    assert memoria.datos_guardados() == ["Vive en Lima"]


@pytest.mark.parametrize(
    "dato, nombre",
    [("Se llama Ana", "Ana"), ("El usuario se llama josé luis", "José"), ("Mi nombre es Lucía", "Lucía"), ("Nombre: Pedro", "Pedro")],
)
def test_nombre_usuario(dato, nombre):
    memoria.recordar(dato)
    assert memoria.nombre_usuario() == nombre


def test_nombre_usuario_ignora_nombres_de_otros_y_usa_el_mas_reciente():
    assert memoria.nombre_usuario() == ""
    memoria.recordar("Su hijo se llama Pedro")
    assert memoria.nombre_usuario() == ""
    memoria.recordar("Se llama Ana")
    memoria.recordar("Se llama Anabel")
    assert memoria.nombre_usuario() == "Anabel"


def test_hilos_a_la_vez_no_pierden_datos(archivo):
    def guardar(hilo):
        for numero in range(5):
            memoria.recordar(f"dato {hilo}-{numero}")
            memoria.datos_guardados()

    hilos = [threading.Thread(target=guardar, args=(hilo,)) for hilo in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len(memoria.datos_guardados()) == 40


def test_memoria_rota_a_mano_no_bloquea_pero_no_se_pisa(archivo):
    archivo.write_text('["Se llama Ana", ', encoding="utf-8")
    assert memoria.datos_guardados() == []
    assert memoria.nombre_usuario() == ""
    with pytest.raises(ValueError):
        memoria.recordar("Le gusta el té")
    assert archivo.read_text(encoding="utf-8") == '["Se llama Ana", '


def test_migra_la_lista_antigua_sin_perder_datos_y_sin_escribir_al_leer(archivo):
    antigua = ["Vive en Lima", "Se llama Ana", "Le gusta el rock", "Su hijo se llama Pedro",
               "No le gusta que la llamen señora", "Los lunes va al gimnasio", "Se llama Anabel"]
    archivo.write_text(json.dumps(antigua, ensure_ascii=False), encoding="utf-8")
    datos = memoria.perfil()["datos"]
    assert memoria.nombre_usuario() == "Anabel"
    assert datos == {
        "personal": ["Vive en Lima"],
        "gustos": ["Le gusta el rock"],
        "personas": ["Su hijo se llama Pedro"],
        "rutinas": ["Los lunes va al gimnasio"],
        "evitar": ["No le gusta que la llamen señora"],
    }
    assert json.loads(archivo.read_text(encoding="utf-8")) == antigua
    memoria.recordar("Prefiere el té")
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert guardado["nombre"] == "Anabel"
    assert guardado["datos"]["gustos"] == ["Le gusta el rock", "Prefiere el té"]


def test_categoria_pedida_o_por_sinonimo_y_si_no_se_adivina():
    memoria.recordar("Trabaja de nueve a seis", "horarios")
    memoria.recordar("Le encantan los tacos", "inventada")
    memoria.recordar("Su esposa es Marta")
    datos = memoria.perfil()["datos"]
    assert datos["rutinas"] == ["Trabaja de nueve a seis"]
    assert datos["gustos"] == ["Le encantan los tacos"]
    assert datos["personas"] == ["Su esposa es Marta"]


def test_un_dato_mas_completo_sustituye_al_que_contiene():
    memoria.recordar("Le gusta el rock")
    assert memoria.recordar("Le gusta el rock clásico") == "Lo recordaré: Le gusta el rock clásico."
    assert memoria.recordar("le gusta el ROCK.") == "Eso ya lo sabía."
    assert memoria.recordar("Le gusta el ro") == "Lo recordaré: Le gusta el ro."
    assert memoria.datos_guardados() == ["Le gusta el rock clásico", "Le gusta el ro"]


def test_nombre_con_mas_datos_guarda_ambos_y_el_nombre_va_aparte(archivo):
    memoria.recordar("Se llama Ana y vive en Quito")
    assert memoria.nombre_usuario() == "Ana"
    assert memoria.datos_guardados() == ["Se llama Ana", "Se llama Ana y vive en Quito"]
    assert memoria.recordar("Se llama Ana") == "Eso ya lo sabía."
    assert memoria.recordar("se llama ana y vive en quito.") == "Eso ya lo sabía."


def test_consolidar_descarta_lo_antiguo_de_lo_menos_importante_y_nunca_el_nombre(monkeypatch):
    monkeypatch.setattr(memoria, "MAX_DATOS", 4)
    memoria.recordar("Se llama Ana")
    memoria.recordar("No soporta el reguetón")
    memoria.recordar("Le gusta el jazz")
    memoria.recordar("Le gusta el cine")
    memoria.recordar("Vive en Lima")
    memoria.recordar("Prefiere el café")
    datos = memoria.perfil()["datos"]
    assert memoria.nombre_usuario() == "Ana"
    assert datos["gustos"] == ["Le gusta el cine", "Prefiere el café"]
    assert datos["evitar"] == ["No soporta el reguetón"]
    assert datos["personal"] == ["Vive en Lima"]


def test_contexto_compacto_por_importancia_y_dentro_del_limite():
    assert memoria.contexto_usuario() == ""
    memoria.recordar("Se llama Ana")
    memoria.recordar("Vive en Lima.")
    memoria.recordar("Le gusta el jazz")
    memoria.recordar("Le gusta el cine")
    memoria.recordar("Odia madrugar")
    assert memoria.contexto_usuario() == (
        "Se llama Ana. Evitar: Odia madrugar. Datos: Vive en Lima. Gustos: Le gusta el cine; Le gusta el jazz."
    )
    corto = memoria.contexto_usuario(60)
    assert len(corto) <= 60
    assert corto == "Se llama Ana. Evitar: Odia madrugar. Datos: Vive en Lima."


def test_contexto_lleno_cabe_en_el_limite_por_defecto():
    for numero in range(memoria.MAX_DATOS):
        memoria.recordar(f"Dato número {numero} con bastante texto para ocupar sitio en el prompt")
    texto = memoria.contexto_usuario()
    assert len(texto) <= 1200
    assert "número 49" in texto


def test_olvidar_dato_busca_en_todas_las_categorias_y_el_nombre():
    memoria.recordar("Se llama Ana")
    memoria.recordar("Le gusta el café")
    memoria.recordar("Su hermana toma cafe")
    assert memoria.olvidar_dato("café") == "Listo, lo olvidé."
    assert memoria.datos_guardados() == ["Se llama Ana"]
    assert memoria.olvidar_dato("se llama ana") == "Listo, lo olvidé."
    assert memoria.nombre_usuario() == ""


def test_lee_utf8_con_bom_del_bloc_de_notas(archivo):
    archivo.write_text('["Se llama Ana"]', encoding="utf-8-sig")
    assert memoria.nombre_usuario() == "Ana"


@pytest.mark.parametrize("contenido", ['{"datos": "nada"}', '{"datos": {"gustos": [1]}}', '"hola"'])
def test_formato_inesperado_no_bloquea_pero_no_se_pisa(archivo, contenido):
    archivo.write_text(contenido, encoding="utf-8")
    assert memoria.datos_guardados() == []
    with pytest.raises(ValueError):
        memoria.recordar("Le gusta el té")
    assert archivo.read_text(encoding="utf-8") == contenido


def test_categoria_inventada_a_mano_se_conserva_como_dato_personal(archivo):
    archivo.write_text('{"nombre": "Ana", "datos": {"trabajo": ["Es enfermera"]}}', encoding="utf-8")
    assert memoria.datos_guardados() == ["Se llama Ana", "Es enfermera"]


def test_reintenta_si_windows_bloquea_el_archivo_un_instante(archivo, monkeypatch):
    reemplazar = memoria.os.replace
    fallos = []

    def bloqueado_una_vez(origen, destino):
        if not fallos:
            fallos.append(1)
            raise PermissionError("en uso")
        reemplazar(origen, destino)

    monkeypatch.setattr(memoria.os, "replace", bloqueado_una_vez)
    assert memoria.recordar("Vive en Lima") == "Lo recordaré: Vive en Lima."
    assert memoria.datos_guardados() == ["Vive en Lima"]


def test_borrar_todo(archivo):
    memoria.recordar("Se llama Ana")
    memoria.borrar_todo()
    memoria.borrar_todo()
    assert not archivo.exists()
    assert memoria.datos_guardados() == []
