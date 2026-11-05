import ast
import math
import operator
import re
import threading

from acciones.programas import normalizar

MAX_EXPRESION = 200
# Con estos topes ninguna cuenta tarda: 2**100000 o factorial(10000) se rechazan antes de calcularse.
MAX_EXPONENTE = 1000
MAX_FACTORIAL = 170
MAX_RESULTADO = 1e100
OPERADORES = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
UNARIOS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
CONSTANTES = {"pi": math.pi, "e": math.e}
MAX_DECIMALES = 15


class FueraDeLimite(Exception):
    pass


def _log(valor, base=10):
    # En español "log" es el decimal; el natural es "ln".
    return math.log(valor, base)


def _factorial(valor):
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    if isinstance(valor, int) and valor > MAX_FACTORIAL:
        raise FueraDeLimite
    return math.factorial(valor)


def _redondear(valor, decimales=0):
    # round(5, -10**20) calcula 10**(10**20) y no termina nunca.
    if not isinstance(decimales, int) or abs(decimales) > MAX_DECIMALES:
        raise ValueError("decimales fuera de rango")
    return round(valor, decimales)


FUNCIONES = {
    "sqrt": math.sqrt, "raiz": math.sqrt, "sin": math.sin, "sen": math.sin, "cos": math.cos, "tan": math.tan,
    "log": _log, "ln": math.log, "log10": math.log10, "abs": abs, "round": _redondear, "factorial": _factorial,
}

ALIAS_UNIDADES = {
    "kilometro": "km", "metro": "m", "centimetro": "cm", "milimetro": "mm", "milla": "mile",
    "pie": "ft", "pulgada": "inch", "yarda": "yard", "milla nautica": "nautical_mile",
    "kilo": "kg", "kilogramo": "kg", "gramo": "g", "miligramo": "mg", "libra": "lb", "onza": "oz",
    "tonelada": "metric_ton", "litro": "L", "mililitro": "mL", "galon": "gallon", "taza": "cup",
    "cucharada": "tablespoon", "cucharadita": "teaspoon", "onza liquida": "fluid_ounce",
    "grado": "degC", "celsius": "degC", "centigrado": "degC", "grado celsius": "degC",
    "grados celsius": "degC", "grado centigrado": "degC", "c": "degC", "fahrenheit": "degF",
    "grado fahrenheit": "degF", "grados fahrenheit": "degF", "f": "degF", "kelvin": "K",
    "segundo": "s", "minuto": "min", "hora": "hour", "dia": "day", "semana": "week", "mes": "month", "ano": "year",
    "kilometro por hora": "km/h", "milla por hora": "mph", "metro por segundo": "m/s",
    "metro cuadrado": "m**2", "kilometro cuadrado": "km**2", "pie cuadrado": "ft**2", "hectarea": "hectare",
    "acre": "acre",
    "metro cubico": "m**3", "byte": "B", "kilobyte": "kB", "megabyte": "MB", "gigabyte": "GB", "terabyte": "TB",
    "julio": "J", "caloria": "cal", "kilocaloria": "kcal", "vatio": "W", "kilovatio": "kW",
    "kilovatio hora": "kWh", "caballo de fuerza": "hp",
}
# Plural regular por palabra: "kilómetros por hora" → "kilometro por hora", "galones" → "galon".
PLURAL = re.compile(r"(?<=[aeiou])s\b|(?<=[^aeiou\s])es\b")

_unidades = None
_candado_unidades = threading.Lock()


def _limitar(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError("resultado no real")
    if (isinstance(valor, float) and not math.isfinite(valor)) or abs(valor) >= MAX_RESULTADO:
        raise FueraDeLimite
    return valor


def _evaluar(nodo):
    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return _limitar(nodo.value)
    if isinstance(nodo, ast.Name) and nodo.id in CONSTANTES:
        return CONSTANTES[nodo.id]
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in UNARIOS:
        return UNARIOS[type(nodo.op)](_evaluar(nodo.operand))
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in OPERADORES:
        izquierda, derecha = _evaluar(nodo.left), _evaluar(nodo.right)
        if isinstance(nodo.op, ast.Pow) and abs(derecha) > MAX_EXPONENTE:
            raise FueraDeLimite
        return _limitar(OPERADORES[type(nodo.op)](izquierda, derecha))
    if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in FUNCIONES
            and not nodo.keywords):
        return _limitar(FUNCIONES[nodo.func.id](*[_evaluar(argumento) for argumento in nodo.args]))
    raise ValueError("expresión no permitida")


def _con_comas_decimales(texto: str) -> str:
    texto = re.sub(r"\b(\d{1,3}(?:\.\d{3})+),(\d+)\b", lambda m: m.group(1).replace(".", "") + "." + m.group(2), texto)
    texto = re.sub(r"(?<![\d.])\d{1,3}(?:,\d{3})+(?![\d,])", lambda m: m.group(0).replace(",", ""), texto)
    return re.sub(r"(?<=\d),(?=\d)", ".", texto)


def _candidatas(expresion: str) -> list[str]:
    texto = expresion.strip().replace("^", "**").replace("×", "*").replace("÷", "/").replace("raíz", "raiz")
    texto = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", texto)
    # "log(8,2)" lleva coma de argumentos y "3,5+1" coma decimal: se prueba primero tal cual (Python).
    candidatas = [texto]
    if "," in texto:
        candidatas.append(_con_comas_decimales(texto))
    return candidatas


def numero_para_voz(valor) -> str:
    """Formato español: miles con punto, decimales con coma, hasta 6 decimales."""
    valor = round(valor, 10)
    if valor == 0:
        return "0"
    if abs(valor) >= 1e15 or abs(valor) < 1e-6:
        mantisa, exponente = f"{valor:.6e}".split("e")
        mantisa = mantisa.rstrip("0").rstrip(".").replace(".", ",")
        return f"{mantisa} por 10 elevado a {int(exponente)}"
    texto = f"{valor:,.6f}".rstrip("0").rstrip(".") if isinstance(valor, float) else f"{valor:,}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def calcular(expresion: str) -> str:
    expresion = str(expresion)
    if len(expresion) > MAX_EXPRESION:
        return "La cuenta es demasiado larga."
    for texto in _candidatas(expresion):
        try:
            resultado = _evaluar(ast.parse(texto, mode="eval").body)
        except ZeroDivisionError:
            return "No se puede dividir entre cero."
        except (FueraDeLimite, OverflowError):
            return "Ese número es demasiado grande para calcularlo."
        except (SyntaxError, ValueError, TypeError, RecursionError):
            continue
        return f"Da {numero_para_voz(resultado)}."
    return "No puedo calcular eso."


def _registro_unidades():
    # pint tarda ~0,3 s en cargar sus definiciones: una sola vez y al primer uso (o en precargar).
    global _unidades
    with _candado_unidades:
        if _unidades is None:
            import pint

            _unidades = pint.UnitRegistry()
    return _unidades


def precargar() -> None:
    threading.Thread(target=_registro_unidades, daemon=True).start()


def _unidad(nombre: str):
    clave = " ".join(re.findall(r"[\w/*]+", normalizar(nombre).replace("°", "")))
    singulares = (clave, PLURAL.sub("", clave), clave.removesuffix("s"))
    candidato = next((ALIAS_UNIDADES[forma] for forma in singulares if forma in ALIAS_UNIDADES), nombre.strip())
    unidades = _registro_unidades()
    try:
        unidad = unidades.Unit(candidato)
    except Exception:
        # El analizador de pint lanza errores muy variados (TokenError, ZeroDivisionError, AttributeError...).
        return None
    # "1" o "%" no son unidades que convertir (bytes y bits sí, aunque pint los trate como adimensionales).
    return None if unidad in (unidades.dimensionless, unidades.percent) else unidad


def convertir_unidad(cantidad: float, de: str, a: str) -> str:
    try:
        cantidad = float(str(cantidad).replace(",", "."))
    except ValueError:
        return "Dime la cantidad con números."
    if not math.isfinite(cantidad):
        return "Dime la cantidad con números."
    de, a = str(de).strip(), str(a).strip()
    if not de or not a:
        return "Dime de qué unidad a qué unidad."
    origen, destino = _unidad(de), _unidad(a)
    for nombre, unidad in ((de, origen), (a, destino)):
        if unidad is None:
            return f"No conozco la unidad {nombre}."
    import pint

    try:
        resultado = _registro_unidades().Quantity(cantidad, origen).to(destino).magnitude
    except pint.DimensionalityError:
        return f"No se pueden convertir {de} a {a}."
    if not math.isfinite(resultado):
        return "Ese número es demasiado grande para calcularlo."
    # Dos decimales bastan para voz; por debajo de 1 se guardan 3 cifras para no decir "0".
    resultado = round(resultado, 2) if abs(resultado) >= 1 else float(f"{resultado:.3g}")
    return f"{numero_para_voz(cantidad)} {de} son {numero_para_voz(resultado)} {a}."
