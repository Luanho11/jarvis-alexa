import re
from pathlib import Path

from docx import Document

from acciones.archivos import enfocar_ventana, ruta_carpeta
from acciones.programas import abrir
from acciones.sistema import atajo_teclado, escribir_texto


def _carpeta_jarvis() -> Path:
    documentos = ruta_carpeta("documentos") or Path.home() / "Documents"
    return documentos / "Jarvis"


def _ruta_libre(carpeta: Path, titulo: str) -> Path:
    nombre = re.sub(r'[<>:"/\\|?*]', "", titulo).strip() or "Documento"
    ruta = carpeta / f"{nombre}.docx"
    numero = 2
    while ruta.exists():
        ruta = carpeta / f"{nombre} ({numero}).docx"
        numero += 1
    return ruta


def _parrafos(texto: str) -> list[str]:
    return [linea.strip() for linea in texto.splitlines() if linea.strip()]


def crear_documento(titulo: str, contenido: str) -> str:
    carpeta = _carpeta_jarvis()
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = _ruta_libre(carpeta, titulo)
        documento = Document()
        documento.add_heading(titulo, level=0)
        for parrafo in _parrafos(contenido):
            documento.add_paragraph(parrafo)
        documento.save(ruta)
    except OSError:
        return "No pude guardar el documento."
    if not abrir(ruta):
        return f"Guardé {ruta.name} en Documentos, carpeta Jarvis."
    return f"Listo, abrí {ruta.name}."


def _ultimo_documento() -> Path | None:
    # Word crea "~$Nombre.docx" (su archivo de bloqueo) al abrir un documento: no es un .docx de verdad.
    documentos = [ruta for ruta in _carpeta_jarvis().glob("*.docx") if not ruta.name.startswith("~$")]
    return max(documentos, key=lambda ruta: ruta.stat().st_mtime) if documentos else None


def dictar(texto: str) -> str:
    ruta = _ultimo_documento()
    if ruta is None:
        return "Aún no he creado ningún documento. Pídeme uno primero."
    try:
        documento = Document(ruta)
        for parrafo in _parrafos(texto):
            documento.add_paragraph(parrafo)
        documento.save(ruta)
    except PermissionError:
        # Word bloquea el .docx mientras está abierto: se escribe en su ventana al final del texto.
        if not enfocar_ventana(ruta.stem).startswith("Te muestro"):
            return f"{ruta.name} está bloqueado y no encuentro su ventana. Ciérralo y vuelve a dictar."
        atajo_teclado("ctrl+end")
        escribir_texto("\n" + texto)
        return f"Lo escribí en {ruta.name}. Recuerda guardar."
    return f"Añadido a {ruta.name}."
