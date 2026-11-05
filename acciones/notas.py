import difflib
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import config

# Búsqueda por palabras y no por embeddings: con unos cientos de notas basta, es instantánea,
# no gasta cuota de ninguna API, funciona sin internet y no añade dependencias.
MAX_RESULTADOS = 3
LARGO_EXTRACTO = 160
LARGO_LECTURA = 2000
PALABRAS_VACIAS = {"que", "los", "las", "una", "unos", "con", "por", "para", "del", "sobre", "mis", "nota", "notas"}
# Caracteres que Windows u Obsidian no admiten en el nombre de un archivo o enlace.
PROHIBIDOS = r'[\\/:*?"<>|#^\[\]]'


def _carpeta() -> Path:
    carpeta = Path(config.NOTAS_CARPETA)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))


def _palabras(texto: str) -> list[str]:
    # Sin la "s" final, "películas" encuentra "película" (y la búsqueda por subcadena encuentra el plural).
    palabras = [p for p in re.findall(r"\w+", _normalizar(texto)) if len(p) > 2 and p not in PALABRAS_VACIAS]
    return [p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palabras]


def _nombre_archivo(titulo: str) -> str:
    return re.sub(PROHIBIDOS, "", titulo).strip()[:80]


def _archivos() -> dict[str, Path]:
    return {_normalizar(archivo.stem): archivo for archivo in _carpeta().glob("*.md")}


def _buscar_archivo(nombre: str) -> Path | None:
    # Windows no distingue mayúsculas en los nombres de archivo: "compras" y "Compras" son la misma nota.
    return _archivos().get(_normalizar(nombre))


def _leer(archivo: Path) -> tuple[str, str]:
    """Devuelve (etiquetas, cuerpo); las notas hechas a mano en Obsidian pueden no tener cabecera."""
    texto = archivo.read_text(encoding="utf-8")
    if not texto.startswith("---\n"):
        return "", texto.strip()
    cabecera, _, cuerpo = texto[4:].partition("\n---\n")
    etiquetas = re.search(r"^tags:\s*\[?(.*?)\]?\s*$", cabecera, re.MULTILINE)
    return (etiquetas.group(1) if etiquetas else ""), cuerpo.strip()


def guardar_nota(titulo: str, contenido: str, etiquetas: str = "") -> str:
    nombre = _nombre_archivo(titulo)
    contenido = contenido.strip()
    if not nombre or not contenido:
        return "Necesito un título y un contenido para la nota."
    archivo = _buscar_archivo(nombre) or _carpeta() / f"{nombre}.md"
    ahora = datetime.now()
    if archivo.exists():
        with archivo.open("a", encoding="utf-8") as nota:
            nota.write(f"\n\n## {ahora:%Y-%m-%d %H:%M}\n\n{contenido}\n")
        return f"Añadí eso a la nota {nombre}."
    lista = ", ".join(e.strip().lstrip("#") for e in etiquetas.split(",") if e.strip())
    # "tags" es la propiedad que Obsidian reconoce como etiquetas.
    archivo.write_text(
        f"---\nfecha: {ahora:%Y-%m-%d %H:%M}\ntags: [{lista}]\n---\n\n# {nombre}\n\n{contenido}\n",
        encoding="utf-8",
    )
    return f"Guardé la nota {nombre}."


def _extracto(cuerpo: str, palabras: list[str]) -> str:
    lineas = [linea.strip() for linea in cuerpo.splitlines() if linea.strip() and not linea.lstrip().startswith("#")]
    elegida = next((l for l in lineas if any(p in _normalizar(l) for p in palabras)), lineas[0] if lineas else "")
    return elegida if len(elegida) <= LARGO_EXTRACTO else elegida[:LARGO_EXTRACTO].rsplit(" ", 1)[0] + "…"


def buscar_notas(consulta: str) -> str:
    palabras = _palabras(consulta)
    if not palabras:
        return "Dime qué busco en tus notas."
    puntuadas = []
    for archivo in _carpeta().glob("*.md"):
        etiquetas, cuerpo = _leer(archivo)
        titulo, etiquetas, texto = _normalizar(archivo.stem), _normalizar(etiquetas), _normalizar(cuerpo)
        puntos = sum(3 * (p in titulo) + 2 * (p in etiquetas) + texto.count(p) for p in palabras)
        if puntos:
            puntuadas.append((puntos, archivo.stem, cuerpo))
    if not puntuadas:
        return "No encontré notas sobre eso."
    mejores = sorted(puntuadas, key=lambda nota: -nota[0])[:MAX_RESULTADOS]
    return " ".join(f"{titulo}: {_extracto(cuerpo, palabras)}" for _, titulo, cuerpo in mejores)


def leer_nota(titulo: str) -> str:
    archivos = _archivos()
    buscado = _normalizar(_nombre_archivo(titulo))
    parecidos = [n for n in archivos if buscado and buscado in n] or difflib.get_close_matches(buscado, archivos, n=1)
    clave = buscado if buscado in archivos else next(iter(parecidos), None)
    if clave is None:
        return f"No tengo ninguna nota llamada {titulo}."
    archivo = archivos[clave]
    _, cuerpo = _leer(archivo)
    cuerpo = cuerpo.removeprefix(f"# {archivo.stem}").strip()
    return f"{archivo.stem}: {cuerpo[:LARGO_LECTURA]}"
