import contextlib
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
        self._hWnd = len(title)
        self.isMinimized = minimizada
        self.isMaximized = False
        self.hecho = []

    def __getattr__(self, accion):
        return lambda: self.hecho.append(accion)


@pytest.fixture
def escritorio(monkeypatch):
    estado = SimpleNamespace(ventanas=[], activa=None, ocultas=set(), al_frente=[], colocadas=[], intocables=set())
    falso = SimpleNamespace(getAllWindows=lambda: estado.ventanas, getActiveWindow=lambda: estado.activa)
    monkeypatch.setitem(sys.modules, "pygetwindow", falso)
    monkeypatch.setattr(archivos, "soltar_foco_del_hud", lambda: None)
    monkeypatch.setattr(archivos, "_oculta", lambda hwnd: hwnd in estado.ocultas)
    monkeypatch.setattr(archivos, "_al_frente", estado.al_frente.append)
    monkeypatch.setattr(archivos, "_intocable", lambda ventana: ventana.title in estado.intocables)
    monkeypatch.setattr(archivos, "_colocar", lambda ventana, posicion: estado.colocadas.append((ventana.title, posicion)))
    monkeypatch.setattr(archivos, "_pixeles_reales", contextlib.nullcontext)
    return estado


def test_enfocar_ventana_la_trae_al_frente(escritorio):
    word = Ventana("Carta - Word", minimizada=True)
    escritorio.ventanas = [Ventana(""), Ventana("YouTube - Google Chrome"), word]
    assert archivos.enfocar_ventana("word") == "Te muestro Carta - Word."
    assert escritorio.al_frente == [word]


def test_enfocar_salta_las_ventanas_fantasma_de_la_tienda(escritorio):
    fantasma, real = Ventana("Calculadora"), Ventana("Calculadora ")
    escritorio.ventanas = [fantasma, real]
    escritorio.ocultas = {fantasma._hWnd}
    archivos.enfocar_ventana("calculadora")
    assert escritorio.al_frente == [real]


def test_enfocar_ventana_inexistente(escritorio):
    assert archivos.enfocar_ventana("excel") == "No veo ninguna ventana de excel."


def test_cerrar_y_maximizar_activa(escritorio):
    escritorio.activa = Ventana("Bloc de notas")
    assert archivos.cerrar_ventana() == "Ventana cerrada."
    assert archivos.maximizar_ventana() == "Maximicé Bloc de notas."
    assert escritorio.activa.hecho == ["close", "maximize"]


def test_no_cierra_el_escritorio_ni_las_consolas(escritorio):
    escritorio.activa = Ventana("Jarvis - python servidor.py")
    escritorio.intocables = {escritorio.activa.title}
    assert archivos.cerrar_ventana().startswith("Esa ventana no la cierro")
    assert escritorio.activa.hecho == []


def test_sin_ventana_activa(escritorio):
    escritorio.activa = Ventana("")
    assert archivos.cerrar_ventana() == "No hay ninguna ventana activa que cerrar."
    assert archivos.acomodar_ventana("derecha") == "No hay ninguna ventana activa que mover."


def test_sin_pygetwindow(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow", None)
    assert "Windows" in archivos.enfocar_ventana("word")
    assert "Windows" in archivos.acomodar_ventana("derecha")
    assert archivos.cerrar_ventana() == "No hay ninguna ventana activa que cerrar."


def test_minimizar_todo_no_alterna(monkeypatch):
    pulsadas = []
    monkeypatch.setattr(archivos, "atajo_teclado", lambda teclas: pulsadas.append(teclas) or "Hecho.")
    assert archivos.minimizar_todo() == "Listo, escritorio despejado."
    assert pulsadas == ["win+m"]


@pytest.mark.parametrize(
    "dicho, posicion",
    [
        ("a la derecha", "derecha"),
        ("Izquierda", "izquierda"),
        ("en la mitad superior", "arriba"),
        ("abajo", "abajo"),
        ("céntrala", "centro"),
        ("maximízala", "maximizar"),
        ("minimizar", "minimizar"),
        ("tamaño normal", "restaurar"),
        ("en diagonal", None),
    ],
)
def test_entiende_la_posicion(dicho, posicion):
    assert archivos._posicion(dicho) == posicion


def test_acomodar_la_activa_a_la_derecha(escritorio):
    escritorio.activa = Ventana("Sin título: Bloc de notas")
    assert archivos.acomodar_ventana("derecha") == "Puse Sin título: Bloc de notas a la derecha."
    assert escritorio.colocadas == [("Sin título: Bloc de notas", "derecha")]
    assert escritorio.al_frente == []


def test_acomodar_por_nombre_la_trae_al_frente(escritorio):
    chrome = Ventana("YouTube - Google Chrome")
    escritorio.ventanas = [chrome]
    assert archivos.acomodar_ventana("izquierda", "chrome") == "Puse YouTube - Google Chrome a la izquierda."
    assert escritorio.al_frente == [chrome]
    assert archivos.acomodar_ventana("minimizar", "chrome") == "Minimicé YouTube - Google Chrome."
    assert chrome.hecho == ["minimize"]
    assert archivos.acomodar_ventana("restaurar", "chrome") == "Dejé YouTube - Google Chrome en tamaño normal."
    assert archivos.acomodar_ventana("arriba", "excel") == "No veo ninguna ventana de excel."


def test_acomodar_sin_posicion_conocida(escritorio):
    assert archivos.acomodar_ventana("en diagonal").startswith("Dime si la pongo")


AREA = (0, 0, 1920, 1040)


@pytest.mark.parametrize(
    "posicion, rectangulo",
    [
        ("izquierda", (0, 0, 960, 1040)),
        ("derecha", (960, 0, 960, 1040)),
        ("arriba", (0, 0, 1920, 520)),
        ("abajo", (0, 520, 1920, 520)),
        ("centro", (560, 220, 800, 600)),
    ],
)
def test_rectangulo_dentro_del_area_de_trabajo(posicion, rectangulo):
    assert archivos._rectangulo(posicion, AREA, (800, 600)) == rectangulo


def test_rectangulo_en_un_segundo_monitor_y_ventana_enorme_en_el_centro():
    segundo = (1920, 0, 3201, 1400)
    assert archivos._rectangulo("derecha", segundo, (1, 1)) == (2560, 0, 641, 1400)
    assert archivos._rectangulo("centro", segundo, (5000, 5000)) == (1920, 0, 1281, 1400)
