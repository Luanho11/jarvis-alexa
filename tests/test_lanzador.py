import logging

import pytest

import lanzador


def test_comando_ngrok_con_y_sin_dominio():
    assert lanzador.comando_ngrok("ngrok", "jarvis.ngrok-free.app") == [
        "ngrok", "http", "--url=jarvis.ngrok-free.app", "127.0.0.1:5000",
    ]
    assert lanzador.comando_ngrok("ngrok", None) == ["ngrok", "http", "127.0.0.1:5000"]


def test_el_registro_va_a_un_archivo(tmp_path):
    archivo = tmp_path / "logs" / "jarvis.log"
    try:
        lanzador.configurar_registro(archivo)
        logging.getLogger("prueba").info("hola registro")
        logging.getLogger().handlers[0].flush()
        assert "hola registro" in archivo.read_text(encoding="utf-8")
    finally:
        for manejador in logging.getLogger().handlers[:]:
            manejador.close()
            logging.getLogger().removeHandler(manejador)


@pytest.fixture
def avisos(monkeypatch):
    lista = []
    monkeypatch.setattr(lanzador, "avisar", lista.append)
    monkeypatch.setattr(lanzador, "configurar_registro", lambda: None)
    return lista


def test_no_arranca_dos_veces(avisos, monkeypatch):
    monkeypatch.setattr(lanzador, "puerto_ocupado", lambda: True)
    lanzador.main()
    assert avisos == ["Jarvis ya está abierto: busca su icono junto al reloj."]


def test_sin_claves_avisa_y_abre_el_env(avisos, monkeypatch):
    import servidor

    abiertos = []
    monkeypatch.setattr(lanzador, "puerto_ocupado", lambda: False)
    monkeypatch.setattr(servidor, "preparar", lambda: (_ for _ in ()).throw(SystemExit("Falta ALEXA_SKILL_ID en el archivo .env")))
    monkeypatch.setattr(lanzador.os, "startfile", abiertos.append, raising=False)
    lanzador.main()
    assert avisos == ["Falta ALEXA_SKILL_ID en el archivo .env. Te abro el archivo para que lo revises."]
    assert abiertos == [lanzador.ENV]


def test_sin_ngrok_avisa(avisos, monkeypatch):
    monkeypatch.setattr(lanzador.shutil, "which", lambda nombre: None)
    assert lanzador.arrancar_ngrok() is None
    assert "winget install ngrok.ngrok" in avisos[0]


def test_icono_se_dibuja():
    pytest.importorskip("PIL")
    assert lanzador.imagen_icono().size == (64, 64)
