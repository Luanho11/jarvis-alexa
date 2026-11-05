"""Arranca Jarvis sin ventanas negras: servidor y ngrok en segundo plano y un icono junto al reloj de Windows."""
import ctypes
import logging
import os
import shutil
import socket
import subprocess
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import dotenv_values

CARPETA = Path(__file__).parent
REGISTRO = CARPETA / "logs" / "jarvis.log"
ENV = CARPETA / ".env"
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

registro = logging.getLogger("lanzador")


def configurar_registro(archivo: Path = REGISTRO) -> None:
    # Sin consola, el archivo es el único sitio donde ver qué pasó; rota para no crecer sin fin.
    archivo.parent.mkdir(exist_ok=True)
    manejador = RotatingFileHandler(archivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO, handlers=[manejador], format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True,
    )


def comando_ngrok(ngrok: str, dominio: str | None) -> list[str]:
    # 127.0.0.1 y no "localhost": Flask solo escucha en IPv4 y ngrok podría intentar IPv6.
    url = [f"--url={dominio}"] if dominio else []
    return [ngrok, "http", *url, "127.0.0.1:5000"]


def arrancar_ngrok() -> subprocess.Popen | None:
    ngrok = shutil.which("ngrok")
    if not ngrok:
        avisar("No encuentro ngrok. Instálalo con: winget install ngrok.ngrok")
        return None
    dominio = (dotenv_values(ENV).get("NGROK_DOMINIO") or "").strip() or None
    return subprocess.Popen(
        comando_ngrok(ngrok, dominio),
        creationflags=SIN_VENTANA, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def avisar(texto: str) -> None:
    registro.error(texto)
    try:
        ctypes.windll.user32.MessageBoxW(None, texto, "Jarvis", 0x40)
    except AttributeError:
        pass


def imagen_icono():
    from PIL import Image, ImageDraw

    imagen = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.ellipse((4, 4, 60, 60), outline=(58, 214, 255), width=6)
    dibujo.ellipse((22, 22, 42, 42), fill=(93, 242, 255))
    return imagen


def puerto_ocupado() -> bool:
    with socket.socket() as conexion:
        return conexion.connect_ex(("127.0.0.1", 5000)) == 0


def main() -> None:
    configurar_registro()
    if puerto_ocupado():
        avisar("Jarvis ya está abierto: busca su icono junto al reloj.")
        return
    import panel
    import servidor

    try:
        app = servidor.preparar()
    except SystemExit as motivo:
        avisar(f"{motivo}. Te abro el archivo para que lo revises.")
        os.startfile(ENV)
        return
    threading.Thread(target=lambda: app.run(port=5000, use_reloader=False), daemon=True).start()
    ngrok = arrancar_ngrok()

    import pystray

    def salir(icono):
        if ngrok:
            ngrok.terminate()
        icono.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir panel", lambda: panel.mostrar(), default=True),
        pystray.MenuItem("Ver registro", lambda: os.startfile(REGISTRO)),
        pystray.MenuItem("Editar claves (.env)", lambda: os.startfile(ENV)),
        pystray.MenuItem("Salir", salir),
    )
    registro.info("Jarvis listo")
    pystray.Icon("Jarvis", imagen_icono(), "Jarvis", menu).run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Sin consola, un fallo al arrancar solo se vería así.
        registro.exception("Jarvis no pudo arrancar")
        avisar(f"Jarvis no pudo arrancar. Mira el registro: {REGISTRO}")
