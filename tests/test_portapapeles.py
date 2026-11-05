import sys
from types import SimpleNamespace

import pytest

from acciones import portapapeles


class PyperclipException(Exception):
    pass


@pytest.fixture
def pyperclip(monkeypatch):
    falso = SimpleNamespace(contenido="", copiados=[], PyperclipException=PyperclipException)
    falso.paste = lambda: falso.contenido
    falso.copy = falso.copiados.append
    monkeypatch.setitem(sys.modules, "pyperclip", falso)
    return falso


def test_lee_lo_copiado(pyperclip):
    pyperclip.contenido = "  hello world \n"
    assert portapapeles.leer_portapapeles() == "Lo copiado: hello world"


@pytest.mark.parametrize("contenido", ["", "   \n\t", None])
def test_vacio_o_sin_texto(pyperclip, contenido):
    pyperclip.contenido = contenido
    assert portapapeles.leer_portapapeles() == "El portapapeles está vacío o no tiene texto."


def test_largo_se_recorta_con_aviso(pyperclip):
    pyperclip.contenido = "a" * 10_000
    texto = portapapeles.leer_portapapeles()
    assert texto == "Lo copiado: " + "a" * 4000 + "... (es largo: solo leí los primeros 4000 caracteres)"


def test_copiar(pyperclip):
    assert portapapeles.copiar_al_portapapeles("hola, qué tal") == "Copiado."
    assert pyperclip.copiados == ["hola, qué tal"]
    assert portapapeles.copiar_al_portapapeles("  ") == "No hay nada que copiar."
    assert pyperclip.copiados == ["hola, qué tal"]


def test_portapapeles_ocupado(pyperclip):
    def ocupado(*_):
        raise PyperclipException("OpenClipboard falló")

    pyperclip.paste = ocupado
    pyperclip.copy = ocupado
    assert portapapeles.leer_portapapeles() == "No pude leer el portapapeles."
    assert portapapeles.copiar_al_portapapeles("x") == "No pude copiar al portapapeles."


def test_sin_pyperclip(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyperclip", None)
    assert portapapeles.leer_portapapeles() == "Solo funciona en Windows."
    assert portapapeles.copiar_al_portapapeles("x") == "Solo funciona en Windows."
