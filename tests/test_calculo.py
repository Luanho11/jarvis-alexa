import time

import pytest

from acciones import calculo


@pytest.mark.parametrize(
    ("expresion", "respuesta"),
    [
        ("2+2*3", "Da 8."),
        ("0.1+0.2", "Da 0,3."),
        ("sqrt(16)", "Da 4."),
        ("raíz(9)", "Da 3."),
        ("2^10", "Da 1.024."),
        ("200*15/100", "Da 30."),
        ("3 x 4", "Da 12."),
        ("7 × 6 ÷ 3", "Da 14."),
        ("10 // 3 + 10 % 3", "Da 4."),
        ("-(2.5) + +1", "Da -1,5."),
        ("1/3", "Da 0,333333."),
        ("2**0.5", "Da 1,414214."),
        ("1234.5 * 2", "Da 2.469."),
        ("123456789 * 1000", "Da 123.456.789.000."),
        ("2**60", "Da 1,152922 por 10 elevado a 18."),
        ("0.0000001", "Da 1 por 10 elevado a -7."),
        ("-0.0", "Da 0."),
        ("sin(pi/2) + cos(0) + tan(0)", "Da 2."),
        ("sen(0)", "Da 0."),
        ("log(100) + log10(1000) + ln(e)", "Da 6."),
        ("log(8, 2)", "Da 3."),
        ("abs(-3) + round(2.567, 2)", "Da 5,57."),
        ("factorial(5)", "Da 120."),
        ("factorial(5.0)", "Da 120."),
    ],
)
def test_calcula(expresion, respuesta):
    assert calculo.calcular(expresion) == respuesta


@pytest.mark.parametrize(
    ("expresion", "respuesta"),
    [
        ("3,5 + 1", "Da 4,5."),
        ("1,234 * 2", "Da 2.468."),
        ("1.234,56 * 2", "Da 2.469,12."),
        ("1,234.5 + 0.5", "Da 1.235."),
        ("round(3,14159 , 2)", "Da 3,14."),
    ],
)
def test_comas_decimales_y_de_miles(expresion, respuesta):
    assert calculo.calcular(expresion) == respuesta


@pytest.mark.parametrize("expresion", ["1/0", "5 // 0", "5 % 0", "0 ** -1"])
def test_division_entre_cero(expresion):
    assert calculo.calcular(expresion) == "No se puede dividir entre cero."


@pytest.mark.parametrize(
    "expresion", ["2**100000", "factorial(10000)", "10**1000", "9**999", "1e400", "10.0**400", "(10**60)*(10**50)"]
)
def test_numeros_enormes_se_rechazan_al_momento(expresion):
    inicio = time.perf_counter()
    assert calculo.calcular(expresion) == "Ese número es demasiado grande para calcularlo."
    assert time.perf_counter() - inicio < 0.05


@pytest.mark.parametrize(
    "expresion",
    [
        "__import__('os')", "().__class__", "open('x')", "x", "", "2 +", "True + 1", "'a' * 3", "[1, 2]",
        "(1).real", "sqrt(x=4)", "pow(2, 3)", "lambda: 1", "sqrt(-1)", "log(0)", "(-8) ** 0.5",
        "factorial(-1)", "factorial(2.5)", "round(5, -10**20)", "2 < 3", "1 if 1 else 2", "1; 2", "\x00",
    ],
)
def test_rechaza_lo_que_no_es_una_cuenta(expresion):
    inicio = time.perf_counter()
    assert calculo.calcular(expresion) == "No puedo calcular eso."
    assert time.perf_counter() - inicio < 0.05


def test_expresion_demasiado_larga():
    assert calculo.calcular("1+" * 100 + "1") == "La cuenta es demasiado larga."
    assert calculo.calcular("-" * 199 + "1") == "Da -1."


@pytest.mark.parametrize(
    ("cantidad", "de", "a", "respuesta"),
    [
        (100, "°F", "°C", "100 °F son 37,78 °C."),
        (100, "fahrenheit", "grados centígrados", "100 fahrenheit son 37,78 grados centígrados."),
        (30, "grados celsius", "grados fahrenheit", "30 grados celsius son 86 grados fahrenheit."),
        (0, "celsius", "kelvin", "0 celsius son 273,15 kelvin."),
        (5, "millas", "kilómetros", "5 millas son 8,05 kilómetros."),
        (2, "tazas", "litros", "2 tazas son 0,473 litros."),
        (1, "galón", "litros", "1 galón son 3,79 litros."),
        ("5,5", "libras", "kilos", "5,5 libras son 2,49 kilos."),
        (1, "onzas líquidas", "mililitros", "1 onzas líquidas son 29,57 mililitros."),
        (10, "km/h", "metros por segundo", "10 km/h son 2,78 metros por segundo."),
        (1, "metros cuadrados", "pies cuadrados", "1 metros cuadrados son 10,76 pies cuadrados."),
        (1, "mm", "km", "1 mm son 0,000001 km."),
        (1, "gigabytes", "megabytes", "1 gigabytes son 1.000 megabytes."),
        (2, "horas", "minutos", "2 horas son 120 minutos."),
        (12, "pulgadas", "pies", "12 pulgadas son 1 pies."),
    ],
)
def test_convierte(cantidad, de, a, respuesta):
    assert calculo.convertir_unidad(cantidad, de, a) == respuesta


def test_unidades_incompatibles_o_desconocidas():
    assert calculo.convertir_unidad(1, "kilos", "metros") == "No se pueden convertir kilos a metros."
    assert calculo.convertir_unidad(3, "zorglubs", "m") == "No conozco la unidad zorglubs."
    assert calculo.convertir_unidad(3, "m", "))(") == "No conozco la unidad ))(."
    assert calculo.convertir_unidad(3, "1", "m") == "No conozco la unidad 1."
    assert calculo.convertir_unidad(3, "", "m") == "Dime de qué unidad a qué unidad."


@pytest.mark.parametrize("cantidad", ["mucho", float("nan"), float("inf")])
def test_cantidad_que_no_es_numero(cantidad):
    assert calculo.convertir_unidad(cantidad, "m", "km") == "Dime la cantidad con números."


def test_conversion_que_desborda():
    assert calculo.convertir_unidad(1e308, "km", "mm") == "Ese número es demasiado grande para calcularlo."


def test_precargar_comparte_un_solo_registro(monkeypatch):
    monkeypatch.setattr(calculo, "_unidades", None)
    calculo.precargar()
    assert calculo._registro_unidades() is calculo._registro_unidades()
