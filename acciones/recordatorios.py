import base64
import logging
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta

import config
import panel
from acciones import agenda, echo

INTERVALO = 30
# Al arrancar no se anuncian eventos que pasaron hace rato, solo los del último intervalo.
MARGEN = timedelta(minutes=2)

# Notificación (globo de la bandeja) y voz con lo que ya trae Windows, sin dependencias.
SCRIPT_AVISO = """
Add-Type -AssemblyName System.Windows.Forms, System.Speech
$icono = New-Object System.Windows.Forms.NotifyIcon
$icono.Icon = [System.Drawing.SystemIcons]::Information
$icono.Visible = $true
$icono.ShowBalloonTip(10000, 'Jarvis', '{texto}', 'Info')
(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{texto}')
Start-Sleep -Seconds 5
$icono.Dispose()
"""

avisados: set[tuple[str, str]] = set()
registro = logging.getLogger(__name__)


def avisar(texto: str, en_echo: bool = True) -> None:
    """Avisa en el HUD y en el PC; con en_echo, también en el Echo si Voice Monkey está configurado."""
    panel.emitir("aviso", texto)
    # PowerShell también cierra las comillas simples con las tipográficas (‘ ’ ‚ ‛), frecuentes en textos del LLM.
    script = SCRIPT_AVISO.replace("{texto}", re.sub("['‘’‚‛]", "''", texto))
    # Codificado, el script no pasa por las reglas de comillas de la línea de órdenes de Windows.
    codificado = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-EncodedCommand", codificado],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        print(f"[Jarvis] {texto}")
    if en_echo and config.AVISOS_EN_ECHO:
        echo.decir_en_echo(texto)


def revisar(ahora: datetime) -> None:
    for evento in agenda.leer_eventos():
        # Un evento escrito a mano mal (o con zona horaria) no debe dejar sin aviso a los demás.
        try:
            clave = (evento["titulo"], evento["fecha_hora"])
            momento = datetime.fromisoformat(evento["fecha_hora"]).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError):
            registro.warning("Evento mal escrito en agenda.json: %s", evento)
            continue
        if clave not in avisados and ahora - MARGEN <= momento <= ahora:
            avisados.add(clave)
            avisar(f"Recordatorio: {evento['titulo']}")


def _vigilar() -> None:
    while True:
        # Un agenda.json ilegible no debe parar los avisos para siempre.
        try:
            revisar(datetime.now())
        except Exception:
            registro.exception("No pude revisar la agenda")
        time.sleep(INTERVALO)


def iniciar_vigilante() -> None:
    threading.Thread(target=_vigilar, daemon=True).start()


def poner_temporizador(minutos: int, motivo: str = "") -> str:
    minutos = int(minutos)
    if minutos <= 0:
        return "Dime cuántos minutos."
    texto = f"Se acabó el tiempo: {motivo}" if motivo else "Se acabó el tiempo."
    temporizador = threading.Timer(minutos * 60, avisar, args=[texto])
    temporizador.daemon = True
    temporizador.start()
    unidad = "minuto" if minutos == 1 else "minutos"
    return f"Temporizador de {minutos} {unidad} en marcha."
