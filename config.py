import os

from dotenv import load_dotenv

load_dotenv()

PROVEEDOR_LLM = os.getenv("PROVEEDOR_LLM", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODELO_GROQ = os.getenv("MODELO_GROQ", "openai/gpt-oss-120b")
MODELO_GEMINI = os.getenv("MODELO_GEMINI", "gemini-3.5-flash-lite")
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID", "")
CIUDAD = os.getenv("CIUDAD", "")
PAIS_NOTICIAS = os.getenv("PAIS_NOTICIAS", "MX").strip().upper()
HUD_ACTIVO = os.getenv("HUD_ACTIVO", "si").strip().lower() not in ("no", "0", "false")
URL_GROQ = "https://api.groq.com/openai/v1"
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"
# El cerebro profundo trabaja en segundo plano: puede usar un modelo más listo aunque sea más lento.
MODELO_PROFUNDO = os.getenv("MODELO_PROFUNDO", "gemini-3.8-flash")
NOTAS_CARPETA = os.getenv("NOTAS_CARPETA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "notas"))
# Voice Monkey (opcional) para que el Echo hable por iniciativa propia.
VOICEMONKEY_TOKEN = os.getenv("VOICEMONKEY_TOKEN", "")
VOICEMONKEY_DISPOSITIVO = os.getenv("VOICEMONKEY_DISPOSITIVO", "")
AVISOS_EN_ECHO = os.getenv("AVISOS_EN_ECHO", "si").strip().lower() not in ("no", "0", "false")
# El plan gratis da 200 envíos al mes: el margen cubre pruebas desde la consola de Voice Monkey.
LIMITE_ECHO_MES = int(os.getenv("LIMITE_ECHO_MES", "150"))
