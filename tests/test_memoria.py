import json
import threading

import pytest

from acciones import memoria


@pytest.fixture(autouse=True)
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "memoria.json"
    monkeypatch.setenv("MEMORIA_ARCHIVO", str(ruta))
    return ruta


def test_recordar_guarda_en_utf8(archivo):
    assert memoria.recordar(" Su ciudad es Bogotá ") == "Lo recordaré: Su ciudad es Bogotá."
    assert json.loads(archivo.read_text(encoding="utf-8")) == ["Su ciudad es Bogotá"]
    assert memoria.datos_guardados() == ["Su ciudad es Bogotá"]


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
