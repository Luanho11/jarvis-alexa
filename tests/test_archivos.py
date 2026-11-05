import os
import sys
from types import SimpleNamespace

import pytest

from acciones import archivos


@pytest.fixture
def casa(tmp_path, monkeypatch):
    monkeypatch.setattr(archivos.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setitem(sys.modules, "winreg", None)
    for carpeta in ("Documents", "Downloads", "Desktop"):
        (tmp_path / carpeta).mkdir()
    return tmp_path


@pytest.fixture
def abiertos(monkeypatch):
    lista = []
    monkeypatch.setattr(archivos, "abrir", lambda ruta: lista.append(ruta) or True)
    return lista


def test_abrir_carpeta(casa, abiertos):
    assert archivos.abrir_carpeta("Descargas") == "Abrí Descargas."
    assert abiertos == [casa / "Downloads"]


def test_prefiere_onedrive(casa, abiertos):
    (casa / "OneDrive" / "Documentos").mkdir(parents=True)
    archivos.abrir_carpeta("documentos")
    assert abiertos == [casa / "OneDrive" / "Documentos"]


def test_usa_la_carpeta_que_windows_anota_en_el_registro(casa, abiertos, monkeypatch):
    real = casa / "D" / "Mis descargas"
    real.mkdir(parents=True)
    (casa / "OneDrive" / "Descargas").mkdir(parents=True)
    leidas = []

    class Clave:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def leer(clave, nombre):
        leidas.append(nombre)
        return str(casa / "${CARPETA_PRUEBA}" / "Mis descargas"), 2

    winreg = SimpleNamespace(HKEY_CURRENT_USER=1, OpenKey=lambda raiz, ruta: Clave(), QueryValueEx=leer)
    monkeypatch.setitem(sys.modules, "winreg", winreg)
    monkeypatch.setenv("CARPETA_PRUEBA", "D")
    archivos.abrir_carpeta("descargas")
    assert abiertos == [real]
    assert leidas == ["{374DE290-123F-4565-9164-39C4925E467B}"]


def test_carpeta_desconocida_o_inexistente(casa, abiertos):
    assert archivos.abrir_carpeta("juegos") == "No encontré la carpeta juegos."
    assert archivos.abrir_carpeta("música") == "No encontré la carpeta música."
    assert abiertos == []


def test_buscar_abre_coincidencia_exacta(casa, abiertos):
    (casa / "Desktop" / "Informe final.docx").touch()
    (casa / "Documents" / "informe final borrador.docx").touch()
    assert archivos.buscar_archivo("informe final") == "Abrí Informe final.docx."
    assert abiertos == [casa / "Desktop" / "Informe final.docx"]


def test_buscar_lista_los_mas_recientes(casa, abiertos):
    for numero in range(4):
        ruta = casa / "Documents" / f"factura {numero}.pdf"
        ruta.touch()
        os.utime(ruta, (numero, numero))
    respuesta = archivos.buscar_archivo("factura")
    assert respuesta == "Encontré 4 archivos. Los más recientes: factura 3.pdf, factura 2.pdf, factura 1.pdf. ¿Cuál abro?"
    assert abiertos == []


def test_buscar_ignora_ocultas_y_respeta_tiempo(casa, abiertos, monkeypatch):
    (casa / "Documents" / ".git").mkdir()
    (casa / "Documents" / ".git" / "notas.txt").touch()
    assert archivos.buscar_archivo("notas") == "No encontré ningún archivo con notas."
    (casa / "Downloads" / "notas.txt").touch()
    monkeypatch.setattr(archivos, "SEGUNDOS_BUSQUEDA", -1)
    assert archivos.buscar_archivo("notas") == "No encontré ningún archivo con notas."


class Ventana:
    def __init__(self, title, minimizada=False):
        self.title = title
        self.isMinimized = minimizada
        self.hecho = []

    def __getattr__(self, accion):
        return lambda: self.hecho.append(accion)


class ErrorVentana(Exception):
    pass


@pytest.fixture
def escritorio(monkeypatch):
    estado = SimpleNamespace(ventanas=[], activa=None)
    falso = SimpleNamespace(
        getAllWindows=lambda: estado.ventanas,
        getActiveWindow=lambda: estado.activa,
        PyGetWindowException=ErrorVentana,
    )
    monkeypatch.setitem(sys.modules, "pygetwindow", falso)
    return estado


def test_enfocar_ventana_restaura_y_activa(escritorio):
    word = Ventana("Carta - Word", minimizada=True)
    escritorio.ventanas = [Ventana(""), Ventana("YouTube - Google Chrome"), word]
    assert archivos.enfocar_ventana("word") == "Te muestro Carta - Word."
    assert word.hecho == ["restore", "activate"]


def test_enfocar_ventana_bloqueada_por_windows(escritorio):
    chrome = Ventana("YouTube - Google Chrome")

    def activar():
        raise ErrorVentana

    chrome.activate = activar
    escritorio.ventanas = [chrome]
    archivos.enfocar_ventana("chrome")
    assert chrome.hecho == ["minimize", "restore"]


def test_enfocar_ventana_inexistente(escritorio):
    assert archivos.enfocar_ventana("excel") == "No veo ninguna ventana de excel."


def test_cerrar_y_maximizar_activa(escritorio):
    escritorio.activa = Ventana("Bloc de notas")
    assert archivos.cerrar_ventana() == "Ventana cerrada."
    assert archivos.maximizar_ventana() == "Ventana maximizada."
    assert escritorio.activa.hecho == ["close", "maximize"]


def test_sin_ventana_activa(escritorio):
    escritorio.activa = Ventana("")
    assert archivos.cerrar_ventana() == "No hay ninguna ventana activa que cerrar."


def test_sin_pygetwindow(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow", None)
    assert "Windows" in archivos.enfocar_ventana("word")
    assert archivos.maximizar_ventana() == "No hay ninguna ventana activa que maximizar."


def test_minimizar_todo(monkeypatch):
    pulsadas = []
    monkeypatch.setattr(archivos, "atajo_teclado", lambda teclas: pulsadas.append(teclas) or "Hecho.")
    assert archivos.minimizar_todo() == "Listo, escritorio despejado."
    assert pulsadas == ["win+d"]
