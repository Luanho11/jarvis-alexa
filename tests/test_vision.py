import base64
import sys
from types import SimpleNamespace

import openai
import pytest

from acciones import vision


class FalsoCliente:
    def __init__(self, respuesta=None, error=None):
        self.pedidos = []
        self.respuesta = respuesta
        self.error = error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **pedido):
        self.pedidos.append(pedido)
        if self.error:
            raise self.error
        mensaje = SimpleNamespace(content=self.respuesta)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


@pytest.fixture
def con_clave(monkeypatch):
    monkeypatch.setattr(vision.config, "GEMINI_API_KEY", "clave")
    monkeypatch.setattr(vision, "_capturar_jpeg_base64", lambda: "QUJD")


def _usar_cliente(monkeypatch, cliente):
    creados = []
    monkeypatch.setattr(vision.openai, "OpenAI", lambda **opciones: creados.append(opciones) or cliente)
    return creados


def test_sin_clave_de_gemini(monkeypatch):
    monkeypatch.setattr(vision.config, "GEMINI_API_KEY", "")
    assert vision.describir_pantalla() == "Para ver la pantalla necesito la clave de Gemini."


def test_describe_la_pantalla(monkeypatch, con_clave):
    cliente = FalsoCliente(" Veo un video de YouTube. ")
    creados = _usar_cliente(monkeypatch, cliente)
    assert vision.describir_pantalla("¿qué video es?") == "Veo un video de YouTube."
    assert creados[0]["base_url"] == vision.config.URL_GEMINI and creados[0]["timeout"] == 15
    texto, imagen = cliente.pedidos[0]["messages"][0]["content"]
    assert texto["text"].endswith("a esta pregunta: ¿qué video es?")
    assert imagen["image_url"]["url"] == "data:image/jpeg;base64,QUJD"


def test_error_de_gemini(monkeypatch, con_clave):
    _usar_cliente(monkeypatch, FalsoCliente(error=openai.OpenAIError("sin cuota")))
    assert vision.describir_pantalla() == "No pude analizar la pantalla ahora."


def test_sin_captura(monkeypatch):
    monkeypatch.setattr(vision.config, "GEMINI_API_KEY", "clave")

    def falla():
        raise OSError

    monkeypatch.setattr(vision, "_capturar_jpeg_base64", falla)
    assert vision.describir_pantalla() == "No pude capturar la pantalla."


def test_captura_reducida_en_jpeg(monkeypatch):
    class FalsaImagen:
        def convert(self, modo):
            self.modo = modo
            return self

        def thumbnail(self, tamano):
            self.tamano = tamano

        def save(self, memoria, format, quality):
            memoria.write(b"jpeg")

    imagen = FalsaImagen()
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(ImageGrab=SimpleNamespace(grab=lambda: imagen)))
    assert base64.b64decode(vision._capturar_jpeg_base64()) == b"jpeg"
    assert imagen.modo == "RGB" and imagen.tamano == (1280, 1280)
