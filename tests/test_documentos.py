import pytest
from docx import Document

from acciones import documentos


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(documentos, "ruta_carpeta", lambda nombre: tmp_path)
    return tmp_path / "Jarvis"


@pytest.fixture
def abiertos(monkeypatch):
    lista = []
    monkeypatch.setattr(documentos, "abrir", lambda ruta: lista.append(ruta) or True)
    return lista


def _textos(ruta):
    return [parrafo.text for parrafo in Document(ruta).paragraphs]


def test_crear_documento(carpeta, abiertos):
    assert documentos.crear_documento("Carta: a Ana?", "Hola Ana.\n\nTe escribo...") == "Listo, abrí Carta a Ana.docx."
    assert abiertos == [carpeta / "Carta a Ana.docx"]
    assert _textos(abiertos[0]) == ["Carta: a Ana?", "Hola Ana.", "Te escribo..."]


def test_no_sobrescribe(carpeta, abiertos):
    documentos.crear_documento("Lista", "uno")
    documentos.crear_documento("Lista", "dos")
    assert abiertos[1].name == "Lista (2).docx"


def test_no_pudo_abrir(carpeta, monkeypatch):
    monkeypatch.setattr(documentos, "abrir", lambda ruta: False)
    assert documentos.crear_documento("Nota", "x") == "Guardé Nota.docx en Documentos, carpeta Jarvis."


def test_dictar_sin_documento(carpeta):
    assert "Pídeme uno" in documentos.dictar("hola")


def test_dictar_añade_al_ultimo(carpeta, abiertos):
    documentos.crear_documento("Nota", "primera")
    assert documentos.dictar("segunda línea") == "Añadido a Nota.docx."
    assert _textos(carpeta / "Nota.docx") == ["Nota", "primera", "segunda línea"]


def test_dictar_ignora_el_archivo_de_bloqueo_de_word(carpeta, abiertos):
    documentos.crear_documento("Nota", "primera")
    (carpeta / "~$Nota.docx").write_bytes(b"no es un docx")
    assert documentos.dictar("segunda") == "Añadido a Nota.docx."


@pytest.fixture
def bloqueado(carpeta, abiertos, monkeypatch):
    documentos.crear_documento("Nota", "primera")

    def guardar(self, ruta):
        raise PermissionError

    monkeypatch.setattr(type(Document()), "save", guardar)


def test_dictar_con_word_abierto_escribe_en_su_ventana(bloqueado, monkeypatch):
    acciones = []
    monkeypatch.setattr(documentos, "enfocar_ventana", lambda nombre: acciones.append(nombre) or "Te muestro Nota - Word.")
    monkeypatch.setattr(documentos, "atajo_teclado", acciones.append)
    monkeypatch.setattr(documentos, "escribir_texto", acciones.append)
    assert documentos.dictar("más texto") == "Lo escribí en Nota.docx. Recuerda guardar."
    assert acciones == ["Nota", "ctrl+end", "\nmás texto"]


def test_dictar_bloqueado_sin_ventana(bloqueado, monkeypatch):
    monkeypatch.setattr(documentos, "enfocar_ventana", lambda nombre: "No veo ninguna ventana de nota.")
    assert "Ciérralo" in documentos.dictar("más texto")
