import logging

import cerebro_profundo
from acciones import (
    agenda,
    archivos,
    documentos,
    info,
    memoria,
    notas,
    pc,
    programas,
    recordatorios,
    rutinas,
    sistema,
    vigilancia,
    vision,
    web,
)


def _herramienta(nombre: str, descripcion: str, parametros: dict | None = None, requeridos: tuple = ()) -> dict:
    esquema = {"type": "object", "properties": parametros or {}}
    if requeridos:
        esquema["required"] = list(requeridos)
    return {"type": "function", "function": {"name": nombre, "description": descripcion, "parameters": esquema}}


def _parametro(tipo: str, descripcion: str = "") -> dict:
    return {"type": tipo, "description": descripcion} if descripcion else {"type": tipo}


# Cada llamada al LLM envía todas las herramientas y el plan gratis de Groq limita los tokens por minuto:
# descripciones mínimas.
TEXTO = _parametro("string")
PASOS = {"pasos": _parametro("integer", "Pasos de 2 %. Por defecto 5.")}
BUSQUEDA = {"busqueda": _parametro("string", "Canción, artista o video.")}
MINUTOS = {"minutos": _parametro("integer", "Margen, mínimo 1.")}
SEGUNDOS = {"segundos": _parametro("integer", "Múltiplo de 10. Por defecto 10.")}
NOMBRE_PROGRAMA = {"nombre": _parametro("string", "Ej. word, excel, chrome.")}

HERRAMIENTAS = [
    _herramienta("subir_volumen", "Sube el volumen del PC.", PASOS),
    _herramienta("bajar_volumen", "Baja el volumen del PC.", PASOS),
    _herramienta("fijar_volumen", "Pone el volumen del PC en un porcentaje (0-100).", {"porcentaje": _parametro("integer")}, ("porcentaje",)),
    _herramienta("silenciar", "Silencia o quita el silencio del PC."),
    _herramienta("pausar_reanudar", "Pausa o reanuda lo que suena en el PC."),
    _herramienta("siguiente", "Siguiente canción o video."),
    _herramienta("anterior", "Canción o video anterior."),
    _herramienta("abrir_youtube", "Abre YouTube; con búsqueda muestra los resultados.", BUSQUEDA),
    _herramienta("reproducir_en_youtube", "Reproduce en YouTube el primer resultado.", BUSQUEDA, ("busqueda",)),
    _herramienta("abrir_web", "Abre una web en el navegador.", {"url": _parametro("string", "Ej. google.com")}, ("url",)),
    _herramienta("abrir_programa", "Abre cualquier programa instalado.", NOMBRE_PROGRAMA, ("nombre",)),
    _herramienta("cerrar_programa", "Cierra un programa abierto.", NOMBRE_PROGRAMA, ("nombre",)),
    _herramienta("pantalla_completa", "Pone o quita la pantalla completa en YouTube."),
    _herramienta("adelantar", "Adelanta el video de YouTube.", SEGUNDOS),
    _herramienta("retroceder", "Retrocede el video de YouTube.", SEGUNDOS),
    _herramienta("siguiente_video", "Siguiente video de YouTube."),
    _herramienta("buscar_en_google", "Busca en Google en el navegador.", {"busqueda": TEXTO}, ("busqueda",)),
    _herramienta("clima", "Clima actual.", {"ciudad": _parametro("string", "Vacío: la del usuario.")}),
    _herramienta("abrir_en_spotify", "Busca en Spotify.", BUSQUEDA, ("busqueda",)),
    _herramienta("apagar", "Apaga el PC tras unos minutos.", MINUTOS),
    _herramienta("reiniciar", "Reinicia el PC tras unos minutos.", MINUTOS),
    _herramienta("cancelar_apagado", "Cancela un apagado o reinicio programado."),
    _herramienta("suspender", "Suspende el PC."),
    _herramienta("bloquear", "Bloquea la sesión de Windows."),
    _herramienta("captura_pantalla", "Guarda una captura de pantalla."),
    _herramienta("escribir_texto", "Escribe texto donde esté el cursor.", {"texto": TEXTO}, ("texto",)),
    _herramienta("atajo_teclado", "Pulsa teclas.", {"teclas": _parametro("string", "Ej. ctrl+w, alt+f4, win+d, enter.")}, ("teclas",)),
    _herramienta("estado_pc", "Uso de CPU, memoria y batería."),
    _herramienta("poner_temporizador", "Temporizador que avisa en el PC.", {"minutos": _parametro("integer"), "motivo": TEXTO}, ("minutos",)),
    _herramienta(
        "agregar_evento",
        "Guarda un evento en la agenda.",
        {"titulo": TEXTO, "fecha_hora": _parametro("string", "ISO 8601 local, ej. 2026-11-05T15:00.")},
        ("titulo", "fecha_hora"),
    ),
    _herramienta("listar_eventos", "Eventos de un día o, sin fecha, los próximos.", {"fecha": _parametro("string", "YYYY-MM-DD")}),
    _herramienta("borrar_evento", "Borra un evento por su título.", {"titulo": TEXTO}, ("titulo",)),
    _herramienta("recordar", "Guarda un dato duradero del usuario.", {"dato": _parametro("string", "Una frase.")}, ("dato",)),
    _herramienta("olvidar_dato", "Borra un dato guardado del usuario.", {"dato": TEXTO}, ("dato",)),
    _herramienta("buscar_informacion", "Busca en internet información actual para responder.", {"pregunta": TEXTO}, ("pregunta",)),
    _herramienta("noticias", "Titulares de noticias recientes.", {"tema": _parametro("string", "Vacío: generales.")}),
    _herramienta(
        "convertir_moneda",
        "Convierte una cantidad entre monedas.",
        {"cantidad": _parametro("number"), "de": _parametro("string", "Código ISO, ej. USD."), "a": _parametro("string", "Código ISO, ej. MXN.")},
        ("cantidad", "de", "a"),
    ),
    _herramienta("describir_pantalla", "Mira la pantalla del PC y responde sobre ella.", {"pregunta": TEXTO}),
    _herramienta("activar_modo", "Activa un modo o rutina (trabajo, estudio, relax...).", {"nombre": TEXTO}, ("nombre",)),
    _herramienta("listar_modos", "Dice los modos disponibles."),
    _herramienta(
        "crear_documento",
        "Crea y abre un Word con el texto que redactes.",
        {"titulo": TEXTO, "contenido": _parametro("string", "Un párrafo por línea.")},
        ("titulo", "contenido"),
    ),
    _herramienta("dictar", "Añade texto al último Word que creaste.", {"texto": TEXTO}, ("texto",)),
    _herramienta(
        "abrir_carpeta",
        "Abre una carpeta del usuario.",
        {"nombre": _parametro("string", "documentos, descargas, escritorio, imágenes, música o videos.")},
        ("nombre",),
    ),
    _herramienta("buscar_archivo", "Busca un archivo por nombre y lo abre.", {"nombre": TEXTO}, ("nombre",)),
    _herramienta("minimizar_todo", "Minimiza todo y muestra el escritorio."),
    _herramienta("enfocar_ventana", "Trae al frente una ventana abierta.", {"nombre": _parametro("string", "Parte del título.")}, ("nombre",)),
    _herramienta("cerrar_ventana", "Cierra la ventana activa."),
    _herramienta("maximizar_ventana", "Maximiza la ventana activa."),
    _herramienta(
        "vigilar_pantalla",
        "Vigila la pantalla y comenta lo que pasa en el panel visual (o en voz).",
        {
            "minutos": _parametro("integer", "Por defecto 5."),
            "intervalo": _parametro("integer", "Segundos, mínimo 15. Por defecto 20."),
            "en_voz": _parametro("boolean"),
        },
    ),
    _herramienta("dejar_de_vigilar", "Deja de vigilar la pantalla."),
    _herramienta(
        "encargar_tarea",
        "Encarga al cerebro profundo una tarea larga o de varios pasos; avisa al terminar.",
        {"descripcion": _parametro("string", "Encargo completo, con todos los detalles.")},
        ("descripcion",),
    ),
    _herramienta("estado_tareas", "Dice cómo van los encargos largos."),
    _herramienta(
        "guardar_nota",
        "Guarda una nota en el segundo cerebro del usuario.",
        {"titulo": _parametro("string"), "contenido": _parametro("string"), "etiquetas": _parametro("string", "Separadas por comas.")},
        ("titulo", "contenido"),
    ),
    _herramienta("buscar_notas", "Busca en las notas del usuario.", {"consulta": _parametro("string")}, ("consulta",)),
    _herramienta("leer_nota", "Lee una nota del usuario.", {"titulo": _parametro("string")}, ("titulo",)),
]

# Devuelven texto de terceros (internet, pantalla, notas) que puede esconder órdenes para el LLM.
LECTURA = {"buscar_informacion", "noticias", "describir_pantalla", "leer_nota", "buscar_notas", "estado_tareas"}
# Tras una lectura, en la misma petición estas no se ejecutan: actúan sobre el PC o la memoria y una orden
# inyectada las usaría sin que el usuario lo pida. Si el usuario las pide en su siguiente frase, sí se ejecutan.
PELIGROSAS = {
    "escribir_texto", "atajo_teclado", "cerrar_programa", "cerrar_ventana", "apagar", "reiniciar", "suspender",
    "bloquear", "recordar", "olvidar_dato", "borrar_evento", "encargar_tarea",
}
BLOQUEADA = "Por seguridad no hago esto justo después de leer internet, la pantalla o las notas. Pide al usuario que lo confirme."

FUNCIONES = {
    "subir_volumen": pc.subir_volumen,
    "bajar_volumen": pc.bajar_volumen,
    "fijar_volumen": pc.fijar_volumen,
    "silenciar": pc.silenciar,
    "pausar_reanudar": pc.pausar_reanudar,
    "siguiente": pc.siguiente,
    "anterior": pc.anterior,
    "abrir_youtube": pc.abrir_youtube,
    "reproducir_en_youtube": pc.reproducir_en_youtube,
    "abrir_web": pc.abrir_web,
    "abrir_programa": programas.abrir_programa,
    "cerrar_programa": programas.cerrar_programa,
    "pantalla_completa": pc.pantalla_completa,
    "adelantar": pc.adelantar,
    "retroceder": pc.retroceder,
    "siguiente_video": pc.siguiente_video,
    "buscar_en_google": web.buscar_en_google,
    "clima": web.clima,
    "abrir_en_spotify": web.abrir_en_spotify,
    "apagar": sistema.apagar,
    "reiniciar": sistema.reiniciar,
    "cancelar_apagado": sistema.cancelar_apagado,
    "suspender": sistema.suspender,
    "bloquear": sistema.bloquear,
    "captura_pantalla": sistema.captura_pantalla,
    "escribir_texto": sistema.escribir_texto,
    "atajo_teclado": sistema.atajo_teclado,
    "estado_pc": sistema.estado_pc,
    "poner_temporizador": recordatorios.poner_temporizador,
    "recordar": memoria.recordar,
    "olvidar_dato": memoria.olvidar_dato,
    "buscar_informacion": info.buscar_informacion,
    "noticias": info.noticias,
    "convertir_moneda": info.convertir_moneda,
    "describir_pantalla": vision.describir_pantalla,
    "activar_modo": rutinas.activar_modo,
    "listar_modos": rutinas.listar_modos,
    "crear_documento": documentos.crear_documento,
    "dictar": documentos.dictar,
    "abrir_carpeta": archivos.abrir_carpeta,
    "buscar_archivo": archivos.buscar_archivo,
    "minimizar_todo": archivos.minimizar_todo,
    "enfocar_ventana": archivos.enfocar_ventana,
    "cerrar_ventana": archivos.cerrar_ventana,
    "maximizar_ventana": archivos.maximizar_ventana,
    "vigilar_pantalla": vigilancia.vigilar_pantalla,
    "dejar_de_vigilar": vigilancia.dejar_de_vigilar,
    "encargar_tarea": cerebro_profundo.encargar_tarea,
    "estado_tareas": cerebro_profundo.estado_tareas,
    "guardar_nota": notas.guardar_nota,
    "buscar_notas": notas.buscar_notas,
    "leer_nota": notas.leer_nota,
    "agregar_evento": agenda.agregar_evento,
    "listar_eventos": agenda.listar_eventos,
    "borrar_evento": agenda.borrar_evento,
}


def ejecutar(nombre: str, argumentos: dict) -> str:
    funcion = FUNCIONES.get(nombre)
    if funcion is None:
        return f"No conozco la acción {nombre}."
    try:
        return funcion(**argumentos)
    except Exception:
        # Sin el detalle en la consola, en el PC real solo se oiría "No pude hacer esa acción".
        logging.getLogger(__name__).exception("Falló la acción %s", nombre)
        return "No pude hacer esa acción."
