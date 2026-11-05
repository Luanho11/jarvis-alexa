import pytest

from acciones import notas


@pytest.fixture(autouse=True)
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(notas.config, "NOTAS_CARPETA", str(tmp_path / "notas"))
    return tmp_path / "notas"


def test_guarda_nota_compatible_con_obsidian(carpeta):
    assert notas.guardar_nota("Ideas: viaje/Perú?", "Ir a Cusco en julio.", "viajes, #familia") == "Guardé la nota Ideas viajePerú."
    texto = (carpeta / "Ideas viajePerú.md").read_text(encoding="utf-8")
    assert texto.startswith("---\nfecha: ")
    assert "tags: [viajes, familia]\n---\n\n# Ideas viajePerú\n\nIr a Cusco en julio.\n" in texto


def test_misma_nota_anade_al_final(carpeta):
    notas.guardar_nota("Compras", "leche")
    assert notas.guardar_nota("compras", "pan") == "Añadí eso a la nota compras."
    assert len(list(carpeta.glob("*.md"))) == 1
    assert notas.leer_nota("compras").startswith("Compras: leche")
    assert "pan" in notas.leer_nota("compras")


def test_sin_titulo_o_contenido():
    assert notas.guardar_nota("  ", "algo") == notas.guardar_nota("titulo", " ") == "Necesito un título y un contenido para la nota."


def test_busca_sin_tildes_y_ordena_por_puntuacion():
    notas.guardar_nota("Receta de lentejas", "Lentejas con chorizo, cebolla y pimentón.", "cocina")
    notas.guardar_nota("Viaje", "Probar las lentejas de la abuela.")
    notas.guardar_nota("Trabajo", "Reunión el lunes con el equipo de diseño.")
    notas.guardar_nota("Gimnasio", "Pierna los martes.")
    notas.guardar_nota("Pendientes", "Llamar a la abuela.")

    resultado = notas.buscar_notas("lentéjas")
    assert resultado.startswith("Receta de lentejas: Lentejas con chorizo")
    assert "Viaje: Probar las lentejas de la abuela." in resultado
    assert "Trabajo" not in resultado
    assert notas.buscar_notas("reunion").startswith("Trabajo: Reunión el lunes")
    assert notas.buscar_notas("cocina").startswith("Receta de lentejas")


def test_busqueda_devuelve_tres_como_mucho_con_extracto_corto():
    for numero in range(5):
        notas.guardar_nota(f"Película {numero}", "película " * (numero + 1) + "x" * 300)
    resultado = notas.buscar_notas("películas que vi")
    assert resultado.count("Película") == 3
    assert resultado.startswith("Película 4")
    assert len(resultado) < 3 * (notas.LARGO_EXTRACTO + 20)


def test_busqueda_sin_resultados_o_vacia():
    assert notas.buscar_notas("dinosaurios") == "No encontré notas sobre eso."
    assert notas.buscar_notas("de la") == "Dime qué busco en tus notas."


def test_lee_notas_hechas_a_mano_y_por_nombre_parecido(carpeta):
    carpeta.mkdir()
    (carpeta / "Libros pendientes.md").write_text("Dune y Rayuela.", encoding="utf-8")
    assert notas.leer_nota("libros") == "Libros pendientes: Dune y Rayuela."
    assert notas.leer_nota("libros pendiente") == "Libros pendientes: Dune y Rayuela."
    assert notas.buscar_notas("rayuela") == "Libros pendientes: Dune y Rayuela."
    assert notas.leer_nota("astronomía") == "No tengo ninguna nota llamada astronomía."
