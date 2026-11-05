import ctypes
import json
import time

import panel
from acciones import vision
from acciones.programas import normalizar
from acciones.sistema import pyautogui_sin_failsafe

DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}
BOTONES = {"izquierdo": "left", "derecho": "right", "medio": "middle", "central": "middle"}
MAX_CLICS = 3
# Windows mide la rueda en 1/120 de muesca y pyautogui le pasa la cantidad tal cual: scroll(5) casi no se movería.
MUESCA = 120
MAX_MUESCAS = 50
MOUSEEVENTF_HWHEEL = 0x01000
# Lo que tarda Windows en animar el minimizado del HUD.
ESPERA_HUD = 0.4

SIN_WINDOWS = "Solo puedo usar el mouse en Windows."
NO_ENCONTRADO = "No encontré eso en la pantalla."
# Formato de detección de Gemini recomendado por Google: caja [ymin, xmin, ymax, xmax] normalizada de 0 a 1000.
INSTRUCCION = (
    "Esta es la pantalla de mi PC. Localiza este elemento: {descripcion}. "
    'Responde solo con JSON: {{"box_2d": [ymin, xmin, ymax, xmax]}} con enteros normalizados de 0 a 1000. '
    'Si no está en la pantalla, responde {{"box_2d": []}}.'
)
FORMATO_JSON = {
    "type": "json_schema",
    "json_schema": {
        "name": "elemento",
        "schema": {
            "type": "object",
            "properties": {"box_2d": {"type": "array", "items": {"type": "integer"}}},
            "required": ["box_2d"],
        },
    },
}


def _direccion(texto: str) -> tuple[int, int] | None:
    texto = normalizar(texto)
    return next((paso for nombre, paso in DIRECCIONES.items() if nombre in texto), None)


def _boton(texto: str) -> str | None:
    texto = normalizar(texto)
    if not texto:
        return "left"
    return next((boton for nombre, boton in BOTONES.items() if nombre in texto), None)


def _veces(veces: int) -> int:
    return min(max(int(veces), 1), MAX_CLICS)


def _limitar(x: int, y: int, ancho: int, alto: int) -> tuple[int, int]:
    return min(max(x, 0), ancho - 1), min(max(y, 0), alto - 1)


def _posicion(texto: str, ancho: int, alto: int) -> tuple[int, int] | None:
    texto = normalizar(texto)
    x = 0 if "izquierd" in texto else ancho - 1 if "derech" in texto else ancho // 2
    y = 0 if "superior" in texto or "arriba" in texto else alto - 1 if "inferior" in texto or "abajo" in texto else alto // 2
    if (x, y) == (ancho // 2, alto // 2) and "centro" not in texto and "medio" not in texto:
        return None
    return x, y


def _apartar_hud() -> None:
    # Mientras hablas el HUD queda encima de todo: taparía lo que se busca y se quedaría con el clic o el scroll.
    if panel.ocultar():
        time.sleep(ESPERA_HUD)


def _rueda_horizontal(cantidad: int) -> None:
    # pyautogui.hscroll en Windows hace scroll vertical: se usa la rueda horizontal de la API de Windows.
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, cantidad, 0)


def _leer_caja(texto: str) -> tuple | None:
    """La caja [ymin, xmin, ymax, xmax] de la respuesta de Gemini, o None si no es válida o no lo encontró."""
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        datos = json.loads(texto)
    except ValueError:
        return None
    if isinstance(datos, list) and datos:
        datos = datos[0]
    caja = datos.get("box_2d") if isinstance(datos, dict) else None
    if not isinstance(caja, list) or len(caja) != 4:
        return None
    if not all(isinstance(valor, (int, float)) and not isinstance(valor, bool) for valor in caja):
        return None
    ymin, xmin, ymax, xmax = caja
    if not (0 <= ymin <= ymax <= 1000 and 0 <= xmin <= xmax <= 1000):
        return None
    return ymin, xmin, ymax, xmax


def _a_pantalla(caja: tuple, ancho: int, alto: int) -> tuple[int, int]:
    """Centro de la caja en las coordenadas de pyautogui (ancho y alto de pyautogui.size())."""
    # La caja va de 0 a 1000 sobre la imagen entera, así que no importa a cuánto se redujo la captura ni el
    # escalado DPI: ImageGrab capta la pantalla principal en píxeles físicos y pyautogui hace clic en los suyos
    # (físicos, porque al importarse llama a SetProcessDPIAware; lógicos si eso fallara), y ambos cubren la misma.
    ymin, xmin, ymax, xmax = caja
    x = round((xmin + xmax) / 2 / 1000 * ancho)
    y = round((ymin + ymax) / 2 / 1000 * alto)
    return _limitar(x, y, ancho, alto)


def mover_mouse(direccion: str = "", pixeles: int = 100, posicion: str = "") -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return SIN_WINDOWS
    ancho, alto = pyautogui.size()
    if posicion:
        destino = _posicion(posicion, ancho, alto)
        if destino is None:
            return f"No conozco la posición {posicion}."
    else:
        paso = _direccion(direccion)
        if paso is None:
            return "Dime si muevo el mouse arriba, abajo, a la izquierda o a la derecha."
        x, y = pyautogui.position()
        distancia = max(int(pixeles), 1)
        destino = _limitar(x + paso[0] * distancia, y + paso[1] * distancia, ancho, alto)
    pyautogui.moveTo(*destino, duration=0.2)
    return "Listo."


def hacer_clic(boton: str = "izquierdo", veces: int = 1) -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return SIN_WINDOWS
    nombre = _boton(boton)
    if nombre is None:
        return f"No conozco el botón {boton}."
    _apartar_hud()
    clics = _veces(veces)
    pyautogui.click(button=nombre, clicks=clics)
    return "Doble clic." if clics == 2 else "Clic."


def desplazar(direccion: str = "abajo", cantidad: int = 5) -> str:
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return SIN_WINDOWS
    paso = _direccion(direccion)
    if paso is None:
        return "Dime si desplazo arriba, abajo, a la izquierda o a la derecha."
    muescas = min(max(int(cantidad), 1), MAX_MUESCAS)
    _apartar_hud()
    horizontal, vertical = paso
    if vertical:
        pyautogui.scroll(-vertical * muescas * MUESCA)
    else:
        _rueda_horizontal(horizontal * muescas * MUESCA)
    return "Listo."


def clic_en(descripcion: str, boton: str = "izquierdo", veces: int = 1) -> str:
    descripcion = descripcion.strip()
    if not descripcion:
        return "Dime en qué hago clic."
    try:
        pyautogui = pyautogui_sin_failsafe()
    except ImportError:
        return SIN_WINDOWS
    nombre = _boton(boton)
    if nombre is None:
        return f"No conozco el botón {boton}."
    _apartar_hud()
    try:
        respuesta = vision.mirar_pantalla(INSTRUCCION.format(descripcion=descripcion), response_format=FORMATO_JSON)
    except vision.SinVision as error:
        return str(error)
    caja = _leer_caja(respuesta)
    if caja is None:
        return NO_ENCONTRADO
    x, y = _a_pantalla(caja, *pyautogui.size())
    panel.emitir("accion", f"Clic en {descripcion}")
    pyautogui.click(x, y, button=nombre, clicks=_veces(veces))
    return f"Hice clic en {descripcion}."
