from pathlib import Path

BAT = (Path(__file__).parent.parent / "iniciar.bat").read_bytes()


def test_iniciar_bat_tiene_finales_de_linea_de_windows():
    # Con saltos LF, cmd.exe salta mal a las etiquetas (goto) y el arranque falla de formas raras.
    assert b"\n" not in BAT.replace(b"\r\n", b"")


def test_iniciar_bat_es_ascii():
    # La consola de Windows no usa UTF-8 por defecto: una tilde se vería rota.
    BAT.decode("ascii")


def test_requirements_es_ascii():
    # pip lo lee con la codificación de Windows (cp1252), no con UTF-8.
    (Path(__file__).parent.parent / "requirements.txt").read_bytes().decode("ascii")
