from types import SimpleNamespace

import pytest

from acciones import programas


@pytest.fixture
def abiertos(monkeypatch):
    lista = []
    monkeypatch.setattr(programas.os, "startfile", lista.append, raising=False)
    return lista


@pytest.fixture
def menu_inicio(tmp_path, monkeypatch):
    carpeta = tmp_path / "Programs"
    (carpeta / "Juegos").mkdir(parents=True)
    for acceso in ("Visual Studio Code.lnk", "Juegos/Steam.lnk", "Discord.lnk"):
        (carpeta / acceso).touch()
    monkeypatch.setattr(programas, "_carpetas_inicio", lambda: [carpeta])
    return carpeta


def test_abre_alias_sin_tildes_ni_mayusculas(abiertos, menu_inicio):
    assert programas.abrir_programa("Word") == "Abrí word."
    assert programas.abrir_programa("Configuración") == "Abrí configuracion."
    assert abiertos == ["winword", "ms-settings:"]


def test_busca_en_menu_inicio_por_parte_del_nombre(abiertos, menu_inicio):
    assert programas.abrir_programa("visual studio") == "Abrí Visual Studio Code."
    assert abiertos == [menu_inicio / "Visual Studio Code.lnk"]


def test_busca_en_menu_inicio_con_errores(abiertos, menu_inicio):
    assert programas.abrir_programa("estim") == "Abrí Steam."
    assert abiertos == [menu_inicio / "Juegos" / "Steam.lnk"]


def test_alias_no_instalado_busca_en_menu_inicio(monkeypatch, menu_inicio):
    abiertos = []

    def startfile(destino):
        if destino == "spotify:":
            raise OSError
        abiertos.append(destino)

    (menu_inicio / "Spotify.lnk").touch()
    monkeypatch.setattr(programas.os, "startfile", startfile, raising=False)
    assert programas.abrir_programa("spotify") == "Abrí Spotify."
    assert abiertos == [menu_inicio / "Spotify.lnk"]


def test_programa_inexistente(abiertos, menu_inicio):
    assert programas.abrir_programa("xyzzy") == "No encontré ese programa."
    assert abiertos == []


@pytest.fixture
def taskkill(monkeypatch):
    llamadas = []

    def correr(codigo):
        def run(comando, capture_output):
            llamadas.append(comando)
            return SimpleNamespace(returncode=codigo)

        monkeypatch.setattr(programas.subprocess, "run", run)

    return llamadas, correr


def test_cerrar_alias(taskkill):
    llamadas, correr = taskkill
    correr(0)
    assert programas.cerrar_programa("Word") == "Cerré word."
    assert llamadas == [["taskkill", "/IM", "WINWORD.EXE", "/F"]]


def test_cerrar_nombre_desconocido_usa_exe(taskkill):
    llamadas, correr = taskkill
    correr(128)
    assert programas.cerrar_programa("Obs Studio") == "obs studio no estaba abierto."
    assert llamadas == [["taskkill", "/IM", "obsstudio.exe", "/F"]]


def test_no_cierra_procesos_protegidos(taskkill):
    llamadas, correr = taskkill
    correr(0)
    assert programas.cerrar_programa("explorer") == "Ese no lo puedo cerrar."
    assert llamadas == []


def test_cerrar_fuera_de_windows(monkeypatch):
    def run(comando, capture_output):
        raise FileNotFoundError

    monkeypatch.setattr(programas.subprocess, "run", run)
    assert "Windows" in programas.cerrar_programa("chrome")


@pytest.mark.parametrize("nombre", ["*", "chr*", "terminal", "CMD", "OpenConsole", "sihost"])
def test_no_cierra_comodines_ni_la_consola_de_jarvis(taskkill, nombre):
    llamadas, correr = taskkill
    correr(0)
    assert programas.cerrar_programa(nombre) == "Ese no lo puedo cerrar."
    assert llamadas == []


def test_cerrar_con_extension_no_la_duplica(taskkill):
    llamadas, correr = taskkill
    correr(0)
    programas.cerrar_programa("obs64.exe")
    assert llamadas == [["taskkill", "/IM", "obs64.exe", "/F"]]
