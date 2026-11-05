import json
import threading
import time
from datetime import datetime, timedelta

import pytest

from acciones import memoria


@pytest.fixture(autouse=True)
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "memoria.json"
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(ruta))
    return ruta


def textos(categoria=None):
    return [d["texto"] for d in memoria.perfil()["datos"] if categoria in (None, d["categoria"])]


def test_recordar_guarda_en_utf8_con_fechas_y_sin_dejar_temporales(archivo):
    assert memoria.recordar(" Su ciudad es Bogotá ") == "Lo recordaré: Su ciudad es Bogotá."
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert guardado["version"] == 3
    dato = guardado["datos"][0]
    assert dato["texto"] == "Su ciudad es Bogotá" and dato["categoria"] == "personal" and dato["veces"] == 1
    assert datetime.fromisoformat(dato["creado"]) and dato["visto"] == dato["creado"]
    assert memoria.datos_guardados() == ["Su ciudad es Bogotá"]
    assert [ruta.name for ruta in archivo.parent.iterdir()] == ["memoria.json"]


def test_sin_archivo_no_hay_datos():
    assert memoria.datos_guardados() == []
    assert memoria.cantidad() == 0


def test_no_duplica_ni_guarda_vacios():
    memoria.recordar("Prefiere Spotify")
    assert memoria.recordar("prefiere spotify") == "Eso ya lo sabía."
    assert memoria.recordar("  ") == "No me dijiste qué recordar."
    assert memoria.recordar("¡¡!!") == "No me dijiste qué recordar."
    assert memoria.datos_guardados() == ["Prefiere Spotify"]


def test_no_hay_limite_de_datos():
    for numero in range(300):
        memoria.recordar(f"Dato número {numero}")
    assert memoria.cantidad() == 300
    assert memoria.datos_guardados()[0] == "Dato número 0"


def test_repetirlo_otro_dia_cuenta_como_confirmacion(archivo):
    memoria.recordar("Le gusta el jazz")
    memoria.recordar("le gusta el jazz")
    assert memoria.perfil()["datos"][0]["veces"] == 1
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    guardado["datos"][0]["visto"] = "2026-01-01T10:00"
    archivo.write_text(json.dumps(guardado), encoding="utf-8")
    memoria.recordar("Le gusta el jazz")
    dato = memoria.perfil()["datos"][0]
    assert dato["veces"] == 2 and dato["visto"] > "2026-01-01T10:00"


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
            memoria.contexto_usuario(pedido=f"dato {hilo}")

    hilos = [threading.Thread(target=guardar, args=(hilo,)) for hilo in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert memoria.cantidad() == 40


def test_memoria_rota_a_mano_no_bloquea_pero_no_se_pisa(archivo):
    archivo.write_text('["Se llama Ana", ', encoding="utf-8")
    assert memoria.datos_guardados() == []
    assert memoria.nombre_usuario() == ""
    assert memoria.contexto_usuario(pedido="Ana") == ""
    with pytest.raises(ValueError):
        memoria.recordar("Le gusta el té")
    assert archivo.read_text(encoding="utf-8") == '["Se llama Ana", '


def test_migra_la_lista_antigua_sin_perder_datos_y_sin_escribir_al_leer(archivo):
    antigua = ["Vive en Lima", "Se llama Ana", "Le gusta el rock", "Su hijo se llama Pedro",
               "No le gusta que la llamen señora", "Los lunes va al gimnasio", "Se llama Anabel"]
    archivo.write_text(json.dumps(antigua, ensure_ascii=False), encoding="utf-8")
    assert memoria.nombre_usuario() == "Anabel"
    assert {d["texto"]: d["categoria"] for d in memoria.perfil()["datos"]} == {
        "Vive en Lima": "personal",
        "Le gusta el rock": "gustos",
        "Su hijo se llama Pedro": "personas",
        "No le gusta que la llamen señora": "evitar",
        "Los lunes va al gimnasio": "rutinas",
    }
    assert json.loads(archivo.read_text(encoding="utf-8")) == antigua
    memoria.recordar("Prefiere el té")
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert guardado["version"] == 3 and guardado["nombre"] == "Anabel" and len(guardado["datos"]) == 6


def test_migra_la_version_2(archivo):
    archivo.write_text(json.dumps({"version": 2, "nombre": "Ana", "datos": {
        "gustos": ["Le gusta el rock"], "evitar": [], "trabajo": ["Es enfermera"],
    }}), encoding="utf-8")
    assert memoria.datos_guardados() == ["Se llama Ana", "Le gusta el rock", "Es enfermera"]
    assert textos("personal") == ["Es enfermera"]


def test_categoria_pedida_o_por_sinonimo_y_si_no_se_adivina():
    memoria.recordar("Trabaja de nueve a seis", "horarios")
    memoria.recordar("Le encantan los tacos", "inventada")
    memoria.recordar("Su esposa es Marta")
    assert textos("rutinas") == ["Trabaja de nueve a seis"]
    assert textos("gustos") == ["Le encantan los tacos"]
    assert textos("personas") == ["Su esposa es Marta"]


def test_un_dato_mas_completo_sustituye_al_que_contiene():
    memoria.recordar("Le gusta el rock")
    assert memoria.recordar("Le gusta el rock clásico") == "Lo recordaré: Le gusta el rock clásico."
    assert memoria.recordar("le gusta el ROCK.") == "Eso ya lo sabía."
    assert memoria.recordar("Le gusta el ro") == "Lo recordaré: Le gusta el ro."
    assert memoria.datos_guardados() == ["Le gusta el rock clásico", "Le gusta el ro"]


def test_un_dato_de_valor_unico_se_actualiza():
    memoria.recordar("Vive en Lima")
    memoria.recordar("Le gusta Lima")
    memoria.recordar("Tiene 30 años")
    memoria.recordar("Su comida favorita es la pizza")
    memoria.recordar("Vive en Cusco desde junio")
    memoria.recordar("Tiene 31 años")
    memoria.recordar("Su comida favorita es el ceviche")
    memoria.recordar("Su color favorito es el azul")
    assert memoria.datos_guardados() == [
        "Vive en Cusco desde junio", "Le gusta Lima", "Tiene 31 años", "Su comida favorita es el ceviche",
        "Su color favorito es el azul",
    ]


def test_lo_contrario_corrige_y_ya_no_borra():
    memoria.recordar("Le gusta el café")
    assert memoria.recordar("No le gusta el café") == "Lo recordaré: No le gusta el café."
    assert textos() == ["No le gusta el café"] and textos("evitar") == ["No le gusta el café"]
    assert memoria.recordar("Le gusta el café") == "Lo recordaré: Le gusta el café."
    assert textos("gustos") == ["Le gusta el café"]
    memoria.recordar("Trabaja en Google como diseñadora")
    assert memoria.recordar("Ya no trabaja en Google") == "Entendido, lo actualicé."
    assert memoria.recordar("Ya no vive en Marte") == "Entendido."
    assert textos() == ["Le gusta el café"]


def test_nombre_con_mas_datos_guarda_ambos_y_el_nombre_va_aparte():
    memoria.recordar("Se llama Ana y vive en Quito")
    assert memoria.nombre_usuario() == "Ana"
    assert memoria.datos_guardados() == ["Se llama Ana", "Se llama Ana y vive en Quito"]
    assert memoria.recordar("Se llama Ana") == "Eso ya lo sabía."
    assert memoria.recordar("se llama ana y vive en quito.") == "Eso ya lo sabía."


def test_contexto_compacto_por_importancia_y_dentro_del_limite():
    assert memoria.contexto_usuario() == ""
    memoria.recordar("Se llama Ana")
    memoria.recordar("Vive en Lima.")
    memoria.recordar("Le gusta el jazz")
    memoria.recordar("Odia madrugar")
    assert memoria.contexto_usuario() == "Se llama Ana. Evitar: Odia madrugar. Datos: Vive en Lima. Gustos: Le gusta el jazz."
    corto = memoria.contexto_usuario(60)
    assert len(corto) <= 60
    assert corto == "Se llama Ana. Evitar: Odia madrugar. Datos: Vive en Lima."


def test_contexto_elige_lo_relacionado_con_el_pedido_entre_muchos_datos():
    memoria.recordar("Se llama Ana")
    memoria.recordar("No soporta el reguetón")
    memoria.recordar("Su hermana Marta cumple años en mayo")
    for numero in range(200):
        memoria.recordar(f"Dato de relleno número {numero} con texto para ocupar sitio")
    texto = memoria.contexto_usuario(400, pedido="¿Qué le regalo a mi hermano?")
    assert len(texto) <= 400
    assert texto.startswith("Se llama Ana. Evitar: No soporta el reguetón. Personas: Su hermana Marta")
    assert "Su hermana" not in memoria.contexto_usuario(400, pedido="pon música")


def test_contexto_prefiere_lo_confirmado_y_reciente(archivo):
    memoria.recordar("Le gusta el tenis")
    memoria.recordar("Le gusta el golf")
    memoria.recordar("Le gusta el pádel")
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    viejo = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M")
    for dato in guardado["datos"]:
        dato["visto"] = viejo
    guardado["datos"][1]["veces"] = 4
    guardado["datos"][2]["visto"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
    archivo.write_text(json.dumps(guardado), encoding="utf-8")
    assert memoria.contexto_usuario() == "Gustos: Le gusta el golf; Le gusta el pádel; Le gusta el tenis."


def test_contexto_anota_cuando_se_uso_un_dato_una_vez_al_dia(archivo):
    memoria.recordar("Su perro se llama Toby")
    memoria.recordar("Vive en Lima")
    memoria.contexto_usuario(pedido="saca al perro")
    usados = {d["texto"]: d.get("usado") for d in memoria.perfil()["datos"]}
    assert usados["Su perro se llama Toby"] and usados["Vive en Lima"] is None
    antes = archivo.stat().st_mtime_ns
    memoria.contexto_usuario(pedido="el perro")
    assert archivo.stat().st_mtime_ns == antes


def test_contexto_con_miles_de_datos_es_rapido(archivo):
    datos = [{"texto": f"Dato número {numero} sobre la vida de {numero % 97}"} for numero in range(2000)]
    archivo.write_text(json.dumps({"version": 3, "nombre": "Ana", "datos": datos}), encoding="utf-8")
    memoria.contexto_usuario(pedido="primera lectura")
    inicio = time.perf_counter()
    texto = memoria.contexto_usuario(pedido="la vida de Ana")
    assert time.perf_counter() - inicio < 0.1
    assert len(texto) <= 1200


def test_olvidar_dato_busca_en_todas_las_categorias_y_el_nombre():
    memoria.recordar("Se llama Ana")
    memoria.recordar("Le gusta el café")
    memoria.recordar("Su hermana toma cafe")
    assert memoria.olvidar_dato("café") == "Listo, lo olvidé."
    assert memoria.datos_guardados() == ["Se llama Ana"]
    assert memoria.olvidar_dato("se llama ana") == "Listo, lo olvidé."
    assert memoria.nombre_usuario() == ""


def test_olvidar_parecido_solo_borra_lo_casi_identico():
    memoria.recordar("Vive en Lima con su esposa")
    memoria.recordar("Le gusta Lima")
    assert not memoria.olvidar_parecido("Lima")
    assert memoria.olvidar_parecido("vive en lima con su esposa.")
    assert memoria.datos_guardados() == ["Le gusta Lima"]


def test_lee_utf8_con_bom_del_bloc_de_notas(archivo):
    archivo.write_text('["Se llama Ana"]', encoding="utf-8-sig")
    assert memoria.nombre_usuario() == "Ana"


@pytest.mark.parametrize(
    "contenido", ['{"datos": "nada"}', '{"datos": {"gustos": [1]}}', '"hola"', '{"datos": [{"texto": 3}]}', '{"datos": ["x"]}'],
)
def test_formato_inesperado_no_bloquea_pero_no_se_pisa(archivo, contenido):
    archivo.write_text(contenido, encoding="utf-8")
    assert memoria.datos_guardados() == []
    with pytest.raises(ValueError):
        memoria.recordar("Le gusta el té")
    assert archivo.read_text(encoding="utf-8") == contenido


def test_datos_editados_a_mano_con_campos_raros_se_aceptan(archivo):
    archivo.write_text(json.dumps({"datos": [
        {"texto": "Es enfermera", "categoria": "trabajo", "veces": "mucho", "creado": "ayer"},
        {"texto": "  "},
    ]}), encoding="utf-8")
    dato = memoria.perfil()["datos"][0]
    assert memoria.datos_guardados() == ["Es enfermera"]
    assert dato["categoria"] == "personal" and dato["veces"] == 1
    assert memoria.contexto_usuario() == "Datos: Es enfermera."


def test_un_cambio_hecho_a_mano_se_lee_al_momento(archivo):
    memoria.recordar("Vive en Lima")
    assert memoria.datos_guardados() == ["Vive en Lima"]
    archivo.write_text('["Vive en Quito, Ecuador"]', encoding="utf-8")
    assert memoria.datos_guardados() == ["Vive en Quito, Ecuador"]


def test_reintenta_si_windows_bloquea_el_archivo_un_instante(monkeypatch):
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
