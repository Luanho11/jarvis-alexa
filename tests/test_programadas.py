import json
import threading
from datetime import datetime, timedelta

import pytest

from acciones import programadas

# Jueves 5/11/2026.
HOY = datetime(2026, 11, 5, 6, 0)
# Los tests sustituyen threading.Thread (el del módulo, compartido); este es el de verdad.
HILO_REAL = threading.Thread


class HiloInmediato:
    def __init__(self, target, args, daemon):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    ruta = tmp_path / "programadas.json"
    monkeypatch.setenv("PROGRAMADAS_ARCHIVO", str(ruta))
    monkeypatch.setattr(programadas, "_ahora", lambda: HOY)
    monkeypatch.setattr(programadas.threading, "Thread", HiloInmediato)
    return ruta


@pytest.fixture
def avisos(monkeypatch):
    dichos = []
    monkeypatch.setattr(programadas.recordatorios, "avisar", dichos.append)
    return dichos


@pytest.fixture
def encargos(monkeypatch):
    pedidos = []

    def encargar(descripcion):
        pedidos.append(descripcion)
        return programadas.cerebro_profundo.EMPEZADA

    monkeypatch.setattr(programadas.cerebro_profundo, "encargar_tarea", encargar)
    return pedidos


def guardadas(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def test_programar_guarda_el_registro(entorno):
    assert programadas.programar_tarea("tomar la pastilla", "8:00") == (
        "Programado el aviso tomar la pastilla, todos los días a las 08:00."
    )
    tarea = guardadas(entorno)["tareas"][0]
    assert len(tarea.pop("id")) == 8
    assert tarea == {"que": "tomar la pastilla", "hora": "08:00", "dias": "todos", "tipo": "aviso", "ultima": None}


@pytest.mark.parametrize("hora", ["7.30", "07:30", " 7:30 "])
def test_hora_en_varias_formas(entorno, hora):
    programadas.programar_tarea("x", hora)
    assert guardadas(entorno)["tareas"][0]["hora"] == "07:30"


@pytest.mark.parametrize("hora", ["", "25:00", "7:75", "siete", "7:3"])
def test_hora_mal_escrita(entorno, hora):
    assert programadas.programar_tarea("x", hora) == "Dime la hora como 7:30."
    assert not entorno.exists()


@pytest.mark.parametrize(
    ("dias", "guardado"),
    [
        ("", "todos"),
        ("Todos los días", "todos"),
        ("entre semana", "laborables"),
        ("fines de semana", "fines"),
        ("miércoles, lunes", "lunes,miércoles"),
        ("lunes y miercoles", "lunes,miércoles"),
        ("los sábados", "sábado"),
        ("2026-11-20", "2026-11-20"),
    ],
)
def test_dias_con_y_sin_tildes(entorno, dias, guardado):
    programadas.programar_tarea("x", "9:00", dias)
    assert guardadas(entorno)["tareas"][0]["dias"] == guardado


@pytest.mark.parametrize("dias", ["lunes y mañana", "2026-13-40", "cuando pueda"])
def test_dias_que_no_entiende(dias):
    assert programadas.programar_tarea("x", "9:00", dias).startswith("No entendí los días")


def test_fecha_pasada_o_tipo_raro_o_sin_que():
    assert programadas.programar_tarea("x", "5:00", "2026-11-05") == "Esa fecha y hora ya pasaron."
    assert programadas.programar_tarea("x", "9:00", "todos", "alarma") == "El tipo debe ser aviso, resumen o encargo."
    assert programadas.programar_tarea("  ", "9:00") == "Dime qué quieres que haga."
    assert programadas.programar_tarea("x" * 501, "9:00") == "Es demasiado largo; dímelo más corto."


def test_resumen_sin_que_y_duplicados(entorno):
    assert programadas.programar_tarea("", "7:00", "laborables", "resumen") == (
        "Programado el resumen del día, de lunes a viernes a las 07:00."
    )
    assert programadas.programar_tarea("Resumen del dia", "7:00", "entre semana", "resumen") == "Eso ya estaba programado."
    assert len(guardadas(entorno)["tareas"]) == 1


def test_encargo_avisa_del_tope():
    texto = programadas.programar_tarea("busca ofertas de vuelos", "9:00", "lunes", "encargo")
    assert texto == (
        "Programado el encargo busca ofertas de vuelos, los lunes a las 09:00. "
        "Como mucho lanzo 3 encargos programados al día."
    )


def test_tope_de_tareas():
    for numero in range(programadas.MAX_TAREAS):
        programadas.programar_tarea(f"tarea {numero}", "9:00")
    assert programadas.programar_tarea("una más", "9:00") == "Ya tienes 20 tareas programadas; borra alguna primero."


def test_listar(entorno):
    assert programadas.listar_programadas() == "No tienes tareas programadas."
    programadas.programar_tarea("regar las plantas", "20:00", "lunes,jueves")
    programadas.programar_tarea("", "7:00", "fines", "resumen")
    programadas.programar_tarea("revisar el correo", "9:00", "2026-11-20", "encargo")
    assert programadas.listar_programadas() == (
        "Tienes 3 tareas programadas: el resumen del día, los fines de semana a las 07:00; "
        "el encargo revisar el correo, el 20/11 a las 09:00; el aviso regar las plantas, los lunes y jueves a las 20:00."
    )


def test_borrar_exacta_parecida_y_ambigua(entorno):
    programadas.programar_tarea("tomar la pastilla", "8:00")
    programadas.programar_tarea("sacar al perro", "8:00")
    programadas.programar_tarea("sacar la basura", "21:00")
    assert programadas.borrar_programada("Tomar la pastilla") == "Borré tomar la pastilla de las tareas programadas."
    assert programadas.borrar_programada("sacar") == "Hay varias parecidas; dime cuál exactamente."
    assert programadas.borrar_programada("basura") == "Borré sacar la basura de las tareas programadas."
    assert programadas.borrar_programada("nadar") == "No encontré esa tarea programada."
    assert programadas.borrar_programada(" ") == "Dime qué tarea programada borro."
    assert [t["que"] for t in guardadas(entorno)["tareas"]] == ["sacar al perro"]


def test_aviso_dispara_una_sola_vez_en_la_ventana(avisos):
    programadas.programar_tarea("tomar la pastilla", "8:00")
    programadas.revisar(datetime(2026, 11, 5, 7, 59, 50))
    assert avisos == []
    for vez in range(20):
        programadas.revisar(datetime(2026, 11, 5, 8, 0) + timedelta(seconds=25 * vez))
    assert avisos == ["Recordatorio: tomar la pastilla"]


def test_tras_reiniciar_no_repite_y_al_dia_siguiente_si(entorno, avisos, monkeypatch):
    programadas.programar_tarea("tomar la pastilla", "8:00")
    programadas.revisar(datetime(2026, 11, 5, 8, 1))
    assert guardadas(entorno)["tareas"][0]["ultima"] == "2026-11-05"
    # Un proceso nuevo solo tiene lo que hay en disco.
    monkeypatch.setattr(programadas, "_candado", threading.Lock())
    programadas.revisar(datetime(2026, 11, 5, 8, 2))
    programadas.revisar(datetime(2026, 11, 6, 8, 0))
    assert avisos == ["Recordatorio: tomar la pastilla"] * 2


def test_pasada_la_ventana_no_dispara(avisos):
    programadas.programar_tarea("tomar la pastilla", "8:00")
    programadas.revisar(datetime(2026, 11, 5, 8, 10))
    programadas.revisar(datetime(2026, 11, 5, 23, 0))
    assert avisos == []


def test_programada_despues_de_la_hora_empieza_manana(entorno, avisos, monkeypatch):
    monkeypatch.setattr(programadas, "_ahora", lambda: datetime(2026, 11, 5, 8, 3))
    programadas.programar_tarea("tomar la pastilla", "8:00")
    programadas.revisar(datetime(2026, 11, 5, 8, 4))
    assert avisos == []
    programadas.revisar(datetime(2026, 11, 6, 8, 4))
    assert avisos == ["Recordatorio: tomar la pastilla"]


def test_laborables_no_dispara_en_sabado(avisos):
    programadas.programar_tarea("fichar", "9:00", "laborables")
    programadas.revisar(datetime(2026, 11, 7, 9, 0))
    assert avisos == []
    programadas.revisar(datetime(2026, 11, 9, 9, 0))
    assert avisos == ["Recordatorio: fichar"]


def test_dias_sueltos(avisos):
    programadas.programar_tarea("yoga", "18:00", "martes, sabado")
    programadas.revisar(datetime(2026, 11, 5, 18, 0))
    programadas.revisar(datetime(2026, 11, 7, 18, 0))
    assert avisos == ["Recordatorio: yoga"]


def test_fecha_unica_dispara_y_se_borra(entorno, avisos):
    programadas.programar_tarea("llamar al banco", "10:00", "2026-11-06")
    programadas.revisar(datetime(2026, 11, 5, 10, 0))
    assert avisos == []
    programadas.revisar(datetime(2026, 11, 6, 10, 0))
    programadas.revisar(datetime(2026, 11, 6, 10, 1))
    assert avisos == ["Recordatorio: llamar al banco"]
    assert guardadas(entorno)["tareas"] == []


def test_fecha_unica_vencida_se_borra_sin_avisar(entorno, avisos):
    programadas.programar_tarea("llamar al banco", "10:00", "2026-11-06")
    programadas.revisar(datetime(2026, 11, 8, 12, 0))
    assert avisos == []
    assert guardadas(entorno)["tareas"] == []


def test_resumen_programado_avisa_con_el_resumen(avisos, monkeypatch):
    from acciones import resumen

    monkeypatch.setattr(resumen, "resumen_del_dia", lambda: "Hoy es jueves.")
    programadas.programar_tarea("", "7:00", "todos", "resumen")
    programadas.revisar(datetime(2026, 11, 5, 7, 0))
    assert avisos == ["Hoy es jueves."]


def test_encargo_programado_y_tope_diario(entorno, avisos, encargos):
    for numero in range(4):
        programadas.programar_tarea(f"encargo {numero}", "9:00", "todos", "encargo")
    programadas.revisar(datetime(2026, 11, 5, 9, 0))
    assert encargos == ["encargo 0", "encargo 1", "encargo 2"]
    assert avisos == ["Hoy ya lancé 3 encargos programados; me salto encargo 3."]
    assert guardadas(entorno)["encargos"] == {"fecha": "2026-11-05", "cuenta": 3}
    programadas.revisar(datetime(2026, 11, 6, 9, 0))
    assert len(encargos) == 6
    assert guardadas(entorno)["encargos"] == {"fecha": "2026-11-06", "cuenta": 3}


def test_encargo_que_no_puede_empezar_avisa(avisos, monkeypatch):
    monkeypatch.setattr(programadas.cerebro_profundo, "encargar_tarea", lambda descripcion: "Ya tengo 2 tareas en marcha.")
    programadas.programar_tarea("buscar vuelos", "9:00", "todos", "encargo")
    programadas.revisar(datetime(2026, 11, 5, 9, 0))
    assert avisos == ["No pude empezar el encargo programado buscar vuelos. Ya tengo 2 tareas en marcha."]


def test_un_fallo_al_avisar_no_sale_del_hilo(monkeypatch):
    def falla(texto):
        raise RuntimeError("sin PowerShell")

    monkeypatch.setattr(programadas.recordatorios, "avisar", falla)
    programadas.programar_tarea("x", "9:00")
    programadas.revisar(datetime(2026, 11, 5, 9, 0))


@pytest.mark.parametrize("contenido", ["{roto", "[]", '{"tareas": 5}', '{"tareas": ["x"]}', "\xff\xfe"])
def test_json_roto_no_lanza_y_no_se_sobrescribe(entorno, avisos, contenido):
    entorno.write_text(contenido, encoding="latin-1")
    programadas.revisar(datetime(2026, 11, 5, 9, 0))
    assert programadas.programar_tarea("x", "9:00") == programadas.ARCHIVO_ROTO
    assert programadas.listar_programadas() == programadas.ARCHIVO_ROTO
    assert programadas.borrar_programada("x") == programadas.ARCHIVO_ROTO
    assert entorno.read_text(encoding="latin-1") == contenido
    with pytest.raises(ValueError):
        programadas.pendientes_de_hoy(HOY)


def test_json_con_bom_y_tarea_mal_escrita_a_mano(entorno, avisos):
    datos = {"tareas": [
        {"que": "sin hora", "dias": "todos", "tipo": "aviso"},
        {"que": "regar", "hora": "9:00", "dias": "Lunes, Jueves", "tipo": "aviso"},
    ]}
    entorno.write_text(json.dumps(datos), encoding="utf-8-sig")
    programadas.revisar(datetime(2026, 11, 5, 9, 0))
    assert avisos == ["Recordatorio: regar"]
    assert programadas.listar_programadas() == "Tienes 1 tarea programada: el aviso regar, los lunes y jueves a las 09:00."
    assert len(guardadas(entorno)["tareas"]) == 2


def test_si_no_puede_guardar_no_dispara(avisos, monkeypatch):
    programadas.programar_tarea("x", "9:00")

    def sin_permiso(archivo, datos):
        raise PermissionError

    monkeypatch.setattr(programadas, "escribir_json", sin_permiso)
    programadas.revisar(datetime(2026, 11, 5, 9, 0))
    assert avisos == []


def test_pendientes_de_hoy(entorno):
    programadas.programar_tarea("pastilla", "20:00")
    programadas.programar_tarea("", "7:00", "todos", "resumen")
    programadas.programar_tarea("yoga", "8:00", "sábado")
    programadas.programar_tarea("correo", "5:00", "laborables")
    assert [t["que"] for t in programadas.pendientes_de_hoy(datetime(2026, 11, 5, 6, 0))] == ["pastilla"]


def test_hilos_simultaneos_no_pierden_tareas(entorno):
    hilos = [HILO_REAL(target=programadas.programar_tarea, args=(f"tarea {n}", "9:00")) for n in range(15)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len(guardadas(entorno)["tareas"]) == 15
