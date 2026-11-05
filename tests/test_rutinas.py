import json

import pytest

from acciones import rutinas


@pytest.fixture
def llamadas(monkeypatch):
    registro = []

    def falsa(nombre):
        return lambda **argumentos: registro.append((nombre, argumentos))

    falsas = {nombre: falsa(nombre) for nombre in rutinas.ACCIONES}
    monkeypatch.setattr(rutinas, "ACCIONES", falsas)
    return registro


@pytest.fixture
def archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "rutinas.json"
    monkeypatch.setattr(rutinas, "RUTINAS", ruta)
    return ruta


def test_sin_rutinas_usa_el_ejemplo(archivo, llamadas):
    assert rutinas.listar_modos() == "Tus modos son: trabajo, estudio, relax."
    assert rutinas.activar_modo("Modo Relax") == "Modo relax activado."
    assert llamadas[-1] == ("fijar_volumen", {"porcentaje": 30})
    assert llamadas[0][0] == "reproducir_en_youtube"


def test_modo_del_usuario(archivo, llamadas):
    pasos = [{"accion": "abrir_programa", "argumentos": {"nombre": "steam"}}]
    archivo.write_text(json.dumps({"Juegos": pasos}), encoding="utf-8")
    assert rutinas.activar_modo("juegos") == "Modo juegos activado."
    assert llamadas == [("abrir_programa", {"nombre": "steam"})]


def test_modo_desconocido(archivo, llamadas):
    assert rutinas.activar_modo("fiesta") == "No tengo el modo fiesta. Tus modos son: trabajo, estudio, relax."
    assert llamadas == []


def test_pasos_no_permitidos_o_mal_escritos(archivo, llamadas):
    pasos = [
        {"accion": "apagar", "argumentos": {}},
        {"accion": "abrir_web", "argumentos": {"direccion": "x"}},
        "abrir word",
        {"accion": "abrir_web", "argumentos": {"url": "github.com"}},
    ]
    rutinas.ACCIONES["abrir_web"] = lambda url: llamadas.append(url)
    archivo.write_text(json.dumps({"raro": pasos}), encoding="utf-8")
    assert rutinas.activar_modo("raro") == "Modo raro activado, pero hubo problemas en 3 de sus pasos."
    assert llamadas == ["github.com"]


def test_json_roto(archivo):
    archivo.write_text("{ trabajo", encoding="utf-8")
    assert "rutinas.json" in rutinas.listar_modos()
    assert "rutinas.json" in rutinas.activar_modo("trabajo")


def test_rutinas_guardadas_en_ansi(archivo):
    archivo.write_bytes('{"música": []}'.encode("cp1252"))
    assert "rutinas.json" in rutinas.listar_modos()
