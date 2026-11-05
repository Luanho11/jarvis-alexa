MAX_LARGO = 4000


def leer_portapapeles() -> str:
    # Lo copiado puede ser privado: no se registra en logs ni en el HUD.
    try:
        import pyperclip
    except ImportError:
        return "Solo funciona en Windows."
    try:
        texto = pyperclip.paste()
    except pyperclip.PyperclipException:
        return "No pude leer el portapapeles."
    if not isinstance(texto, str) or not texto.strip():
        return "El portapapeles está vacío o no tiene texto."
    texto = texto.strip()
    if len(texto) > MAX_LARGO:
        # Un encargo también lo leería recortado: se avisa en vez de prometer que lo lee entero.
        return f"Lo copiado: {texto[:MAX_LARGO]}... (es largo: solo leí los primeros {MAX_LARGO} caracteres)"
    return f"Lo copiado: {texto}"


def copiar_al_portapapeles(texto: str) -> str:
    if not str(texto).strip():
        return "No hay nada que copiar."
    try:
        import pyperclip
    except ImportError:
        return "Solo funciona en Windows."
    try:
        pyperclip.copy(str(texto))
    except pyperclip.PyperclipException:
        return "No pude copiar al portapapeles."
    return "Copiado."
