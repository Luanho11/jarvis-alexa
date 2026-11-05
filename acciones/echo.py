import json
import logging
import os
import threading
from datetime import date
from pathlib import Path

import requests

import config
import voz

URL = "https://api-v3.voicemonkey.io/announce"
ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "echo_uso.json"
TIEMPO_LIMITE = 10
# A partir de este porcentaje del límite, cada aviso dice cuántos quedan.
AVISO_CERCA = 0.8

registro = logging.getLogger(__name__)
_candado = threading.Lock()


def _archivo() -> Path:
    return Path(os.environ.get("ECHO_USO_ARCHIVO", ARCHIVO_POR_DEFECTO))


def _usados(mes: str) -> int:
    archivo = _archivo()
    if not archivo.exists():
        return 0
    try:
        uso = json.loads(archivo.read_text(encoding="utf-8"))
        return uso["envios"] if uso.get("mes") == mes else 0
    except (ValueError, KeyError, TypeError, AttributeError):
        # Sin cuenta legible se empieza de cero: Voice Monkey corta igual al llegar a su límite (429).
        registro.warning("echo_uso.json no se puede leer; empiezo la cuenta de este mes de cero")
        return 0


def _anotar(mes: str, envios: int) -> None:
    _archivo().write_text(json.dumps({"mes": mes, "envios": envios}), encoding="utf-8")


def _fallo(texto: str) -> str:
    registro.warning(texto)
    return texto


def decir_en_echo(texto: str) -> str:
    """Hace que el Echo diga el texto con Voice Monkey, sin pasar del límite mensual."""
    if not (config.VOICEMONKEY_TOKEN and config.VOICEMONKEY_DISPOSITIVO):
        return "El Echo no puede hablar solo: falta configurar Voice Monkey."
    # Los avisos llegan desde varios hilos (temporizadores y vigilante): el contador no debe pisarse.
    with _candado:
        mes = date.today().strftime("%Y-%m")
        usados = _usados(mes)
        limite = config.LIMITE_ECHO_MES
        if usados >= limite:
            return _fallo(f"Ya usé los {limite} avisos del Echo de este mes; el día 1 vuelvo a tener.")
        restantes = limite - usados - 1
        cerca = usados + 1 >= limite * AVISO_CERCA
        if cerca:
            texto = f"{texto} Por cierto, me quedan {restantes} avisos en el Echo este mes."
        datos = {"token": config.VOICEMONKEY_TOKEN, "device": config.VOICEMONKEY_DISPOSITIVO, "speech": voz.a_ssml(texto)}
        try:
            respuesta = requests.post(URL, json=datos, timeout=TIEMPO_LIMITE)
        except requests.RequestException:
            return _fallo("No pude hablar por el Echo: Voice Monkey no responde.")
        if not respuesta.ok:
            return _fallo(f"Voice Monkey rechazó el aviso ({respuesta.status_code}: {respuesta.text[:80]}).")
        _anotar(mes, usados + 1)
    if cerca:
        return f"Lo dije en el Echo. Quedan {restantes} avisos este mes."
    return "Lo dije en el Echo."
