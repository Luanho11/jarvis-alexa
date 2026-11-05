import logging

import cerebro_profundo
from acciones import (
    agenda,
    aprendizaje,
    archivos,
    calculo,
    documentos,
    google,
    info,
    lectura,
    memoria,
    mouse,
    notas,
    pc,
    portapapeles,
    programadas,
    programas,
    recordatorios,
    resumen,
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
DIRECCION = _parametro("string", "arriba, abajo, izquierda o derecha.")
CLIC = {"boton": _parametro("string", "izquierdo, derecho o medio."), "veces": _parametro("integer", "2: doble clic.")}

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
    _herramienta(
        "mover_mouse",
        "Mueve el mouse en una dirección o a una posición.",
        {"direccion": DIRECCION, "pixeles": _parametro("integer"), "posicion": _parametro("string", "Ej. centro, esquina superior derecha.")},
    ),
    _herramienta("desplazar", "Scroll bajo el mouse.", {"direccion": DIRECCION, "cantidad": _parametro("integer", "Por defecto 5.")}),
    _herramienta("hacer_clic", "Clic donde está el mouse.", CLIC),
    _herramienta(
        "clic_en",
        "Busca en la pantalla lo descrito y le hace clic.",
        {"descripcion": _parametro("string", "Ej. botón Aceptar."), **CLIC},
        ("descripcion",),
    ),
    _herramienta("poner_temporizador", "Temporizador que avisa en el PC.", {"minutos": _parametro("integer"), "motivo": TEXTO}, ("minutos",)),
    _herramienta(
        "agregar_evento",
        "Guarda un evento en la agenda.",
        {"titulo": TEXTO, "fecha_hora": _parametro("string", "ISO 8601 local, ej. 2026-11-05T15:00.")},
        ("titulo", "fecha_hora"),
    ),
    _herramienta("listar_eventos", "Eventos de un día o, sin fecha, los próximos.", {"fecha": _parametro("string", "YYYY-MM-DD")}),
    _herramienta("borrar_evento", "Borra un evento por su título.", {"titulo": TEXTO}, ("titulo",)),
    _herramienta(
        "recordar",
        "Guarda un dato duradero del usuario.",
        {"dato": _parametro("string", "Una frase."), "categoria": {"type": "string", "enum": list(memoria.CATEGORIAS)}},
        ("dato",),
    ),
    _herramienta("olvidar_dato", "Borra un dato guardado del usuario.", {"dato": TEXTO}, ("dato",)),
    _herramienta("que_sabes_de_mi", "Lo que sabes del usuario, para contárselo."),
    _herramienta("olvidar_todo", "Borra todo lo que sabes del usuario si lo confirma diciendo: sí, bórralo todo."),
    _herramienta("buscar_informacion", "Busca en internet información actual para responder.", {"pregunta": TEXTO}, ("pregunta",)),
    _herramienta("noticias", "Titulares de noticias recientes.", {"tema": _parametro("string", "Vacío: generales.")}),
    _herramienta(
        "convertir_moneda",
        "Convierte una cantidad entre monedas.",
        {"cantidad": _parametro("number"), "de": _parametro("string", "Código ISO, ej. USD."), "a": _parametro("string", "Código ISO, ej. MXN.")},
        ("cantidad", "de", "a"),
    ),
    _herramienta("describir_pantalla", "Mira la pantalla del PC y responde sobre ella.", {"pregunta": TEXTO}),
    _herramienta(
        "activar_modo",
        "Activa un modo: rutina (trabajo, estudio) o forma de hablar (profesor, traductor, xara...).",
        {"nombre": TEXTO},
        ("nombre",),
    ),
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
    _herramienta(
        "leer_documento",
        "Lee un PDF, Word, texto o web.",
        {"origen": _parametro("string", "Ruta, nombre de archivo o URL."), "pagina_inicial": _parametro("integer")},
        ("origen",),
    ),
    _herramienta("resumen_del_dia", "Resumen de hoy: clima, citas, avisos y titulares."),
    _herramienta(
        "programar_tarea",
        "Programa un aviso, resumen o encargo recurrente.",
        {
            "que": TEXTO,
            "hora": _parametro("string", "HH:MM"),
            "dias": _parametro("string", "todos, laborables, fines, 'lunes,miércoles' o AAAA-MM-DD."),
            "tipo": {"type": "string", "enum": list(programadas.TIPOS)},
        },
        ("que", "hora"),
    ),
    _herramienta("listar_programadas", "Dice las tareas programadas."),
    _herramienta("borrar_programada", "Borra una tarea programada.", {"que": TEXTO}, ("que",)),
    _herramienta("leer_portapapeles", "Texto copiado por el usuario."),
    _herramienta("copiar_al_portapapeles", "Copia texto al portapapeles.", {"texto": TEXTO}, ("texto",)),
    _herramienta("calcular", "Calcula exacto. Sintaxis Python: 15% de 200 → 200*15/100.", {"expresion": TEXTO}, ("expresion",)),
    _herramienta(
        "convertir_unidad",
        "Convierte unidades (km, millas, °C, °F, kg, libras, litros, tazas...).",
        {"cantidad": _parametro("number"), "de": TEXTO, "a": TEXTO},
        ("cantidad", "de", "a"),
    ),
    _herramienta(
        "leer_correos",
        "Lee correos de Gmail (sin leer por defecto).",
        {"cantidad": _parametro("integer", "Por defecto 5."), "solo_no_leidos": _parametro("boolean")},
    ),
]

# Devuelven texto de terceros (internet, pantalla, notas) que puede esconder órdenes para el LLM.
LECTURA = {
    "buscar_informacion", "noticias", "describir_pantalla", "leer_nota", "buscar_notas", "estado_tareas",
    "leer_documento", "leer_correos", "resumen_del_dia", "leer_portapapeles",
}
# Tras una lectura, en la misma petición estas no se ejecutan: actúan sobre el PC o la memoria y una orden
# inyectada las usaría sin que el usuario lo pida. Si el usuario las pide en su siguiente frase, sí se ejecutan.
PELIGROSAS = {
    "escribir_texto", "atajo_teclado", "cerrar_programa", "cerrar_ventana", "apagar", "reiniciar", "suspender",
    "bloquear", "recordar", "olvidar_dato", "olvidar_todo", "borrar_evento", "programar_tarea", "borrar_programada",
    "encargar_tarea", "hacer_clic", "clic_en",
}
# Acciones cuyo texto ya se puede decir tal cual ("Subí el volumen."): si el LLM solo llama a estas para una
# orden simple, se responde con ese texto sin una segunda llamada. Las que traen datos para que el LLM los
# explique (lectura, clima, agenda, estado...) no están.
DIRECTAS = {
    "subir_volumen", "bajar_volumen", "fijar_volumen", "silenciar", "pausar_reanudar", "siguiente", "anterior",
    "abrir_youtube", "reproducir_en_youtube", "abrir_web", "abrir_programa", "cerrar_programa", "pantalla_completa",
    "adelantar", "retroceder", "siguiente_video", "buscar_en_google", "abrir_en_spotify", "apagar", "reiniciar",
    "cancelar_apagado", "suspender", "bloquear", "captura_pantalla", "escribir_texto", "atajo_teclado",
    "mover_mouse", "desplazar", "hacer_clic", "clic_en", "poner_temporizador", "agregar_evento", "borrar_evento",
    "recordar", "olvidar_dato", "activar_modo", "crear_documento", "dictar", "abrir_carpeta", "buscar_archivo",
    "minimizar_todo", "enfocar_ventana", "cerrar_ventana", "maximizar_ventana", "vigilar_pantalla",
    "dejar_de_vigilar", "encargar_tarea", "guardar_nota", "programar_tarea", "borrar_programada",
    "copiar_al_portapapeles", "calcular", "convertir_unidad",
}
# Herramientas parecidas que el LLM ve como una sola con "accion": cada herramienta enviada cuesta tokens en
# cada petición y el plan gratis de Groq limita los tokens por minuto. Por dentro todo sigue con el nombre
# individual, así que LECTURA, PELIGROSAS, DIRECTAS, la ruta rápida y el aprendizaje no cambian.
GRUPOS = {
    "volumen": ("Volumen del PC.", {
        "subir": "subir_volumen", "bajar": "bajar_volumen", "fijar": "fijar_volumen", "silenciar": "silenciar",
    }),
    "reproduccion": ("Música y videos que suenan en el PC (adelantar y retroceder: YouTube).", {
        "pausar_reanudar": "pausar_reanudar", "siguiente": "siguiente", "anterior": "anterior",
        "pantalla_completa": "pantalla_completa", "adelantar": "adelantar", "retroceder": "retroceder",
        "siguiente_video": "siguiente_video",
    }),
    "ventana": ("Ventanas de Windows (enfocar: trae al frente la del nombre).", {
        "minimizar_todo": "minimizar_todo", "enfocar": "enfocar_ventana", "cerrar": "cerrar_ventana",
        "maximizar": "maximizar_ventana",
    }),
    "mouse": ("Mouse: mover, scroll o clic donde está.", {
        "mover": "mover_mouse", "desplazar": "desplazar", "clic": "hacer_clic",
    }),
    "energia": ("Apagar, reiniciar (tras unos minutos), cancelar eso, suspender o bloquear el PC.", {
        "apagar": "apagar", "reiniciar": "reiniciar", "cancelar_apagado": "cancelar_apagado",
        "suspender": "suspender", "bloquear": "bloquear",
    }),
    "vigilancia": ("Vigila la pantalla y comenta en el panel (o en voz), o deja de hacerlo.", {
        "vigilar": "vigilar_pantalla", "dejar": "dejar_de_vigilar",
    }),
    "modos": ("Modos: activar una rutina (trabajo, estudio) o forma de hablar (profesor, xara...), o listarlos.", {
        "activar": "activar_modo", "listar": "listar_modos",
    }),
}
AGRUPADAS = {original: grupo for grupo, (_, acciones) in GRUPOS.items() for original in acciones.values()}
ESQUEMAS = {h["function"]["name"]: h["function"] for h in HERRAMIENTAS}


def _agrupar(grupo: str) -> dict:
    descripcion, acciones = GRUPOS[grupo]
    parametros = {"accion": {"type": "string", "enum": list(acciones)}}
    for original in acciones.values():
        parametros.update(ESQUEMAS[original]["parameters"]["properties"])
    return _herramienta(grupo, descripcion, parametros, ("accion",))


HERRAMIENTAS = [h for h in HERRAMIENTAS if h["function"]["name"] not in AGRUPADAS] + [_agrupar(g) for g in GRUPOS]


def desagrupar(nombre: str, argumentos: dict) -> tuple[str, dict]:
    """Traduce una llamada de grupo ("volumen", accion="subir") a la individual ("subir_volumen") con solo sus argumentos."""
    if nombre not in GRUPOS:
        return nombre, argumentos
    original = GRUPOS[nombre][1].get(argumentos.get("accion"))
    if original is None:
        return nombre, argumentos
    propios = ESQUEMAS[original]["parameters"]["properties"]
    return original, {clave: valor for clave, valor in argumentos.items() if clave in propios}


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
    "mover_mouse": mouse.mover_mouse,
    "desplazar": mouse.desplazar,
    "hacer_clic": mouse.hacer_clic,
    "clic_en": mouse.clic_en,
    "poner_temporizador": recordatorios.poner_temporizador,
    "recordar": memoria.recordar,
    "olvidar_dato": memoria.olvidar_dato,
    "que_sabes_de_mi": aprendizaje.que_sabes_de_mi,
    "olvidar_todo": aprendizaje.olvidar_todo,
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
    "leer_documento": lectura.leer_documento,
    "leer_correos": google.leer_correos,
    "resumen_del_dia": resumen.resumen_del_dia,
    "programar_tarea": programadas.programar_tarea,
    "listar_programadas": programadas.listar_programadas,
    "borrar_programada": programadas.borrar_programada,
    "leer_portapapeles": portapapeles.leer_portapapeles,
    "copiar_al_portapapeles": portapapeles.copiar_al_portapapeles,
    "calcular": calculo.calcular,
    "convertir_unidad": calculo.convertir_unidad,
    "agregar_evento": agenda.agregar_evento,
    "listar_eventos": agenda.listar_eventos,
    "borrar_evento": agenda.borrar_evento,
}


def ejecutar(nombre: str, argumentos: dict) -> str:
    funcion = FUNCIONES.get(nombre)
    if nombre in GRUPOS:
        return f"Falta una accion válida para {nombre}: {', '.join(GRUPOS[nombre][1])}."
    if funcion is None:
        return f"No conozco la acción {nombre}."
    try:
        return funcion(**argumentos)
    except Exception:
        # Sin el detalle en la consola, en el PC real solo se oiría "No pude hacer esa acción".
        logging.getLogger(__name__).exception("Falló la acción %s", nombre)
        return "No pude hacer esa acción."
