# Prompt de autonomía — Proyecto Jarvis (Alexa inteligente)

## Objetivo
Convertir un Echo Dot 5 en un asistente conversacional tipo Jarvis: conversa con un LLM,
agenda, y controla el PC (música, YouTube, pausar, volumen, abrir cosas).

## Cómo decide el supervisor
1. Avanzar sin esperar al usuario cuando el paso es reversible; anotar la decisión en PROGRESO.md.
2. Preguntar solo lo que sea irreversible o cambie el objetivo.
3. Lo más simple que funcione. Nada de infraestructura de pago si hay alternativa gratis.
4. Código limpio (skill /codigo-limpio): nombres en español, sin comentarios obvios,
   sin código muerto, solo lo necesario.
5. Cada módulo se prueba (pytest) sin red ni Alexa real, con dobles de prueba.
6. Cada avance se resume en una línea en PROGRESO.md.

## Decisiones tomadas
- Todo corre en el PC del usuario: un servidor Flask recibe las peticiones de Alexa
  (Custom Skill con endpoint HTTPS) y se expone con un túnel (ngrok / Cloudflare).
- LLM: Groq (rápido, clave para el límite de ~8 s de Alexa). Respaldo: Gemini.
  Ambos se usan por su API compatible con OpenAI, así hay un solo código (`openai` SDK).
- SO: Windows 11 (confirmado). Soporte Mac/Linux solo si sale barato.
- Todo gratis: plan gratuito de Groq/Gemini, dominio estático gratis de ngrok, skill en modo desarrollo.
- Agenda: archivo local `agenda.json` (Google Calendar queda como mejora futura).
- Seguridad: verificar firma y timestamp de Alexa (flask-ask-sdk) y el ID de la skill; HUD solo en local
  (ngrok añade X-Forwarded-For); freno anti-inyección LECTURA → PELIGROSAS en los dos cerebros.
- Configuración por `.env`: GROQ_API_KEY, GEMINI_API_KEY, PROVEEDOR_LLM, ALEXA_SKILL_ID.

## Equipo
| Rol | Entrega |
|-----|---------|
| Supervisor | Contratos, integración, revisión, PROGRESO.md |
| Dev Alexa | `servidor.py`, `skill/modelo_es.json` |
| Dev Cerebro | `cerebro.py`, `herramientas.py` |
| Dev PC | `acciones/pc.py`, `acciones/agenda.py` |
| QA + Docs | tests, `README.md` (guía paso a paso) |

## Contratos entre módulos
```python
# acciones/pc.py — cada función devuelve un texto corto en español para decir en voz alta
subir_volumen(pasos: int = 5) -> str
bajar_volumen(pasos: int = 5) -> str
fijar_volumen(porcentaje: int) -> str
silenciar() -> str
pausar_reanudar() -> str
siguiente() -> str
anterior() -> str
abrir_youtube(busqueda: str = "") -> str      # sin búsqueda abre la portada
reproducir_en_youtube(busqueda: str) -> str   # reproduce el primer resultado (música o video)
abrir_web(url: str) -> str
# abrir_programa, cerrar_programa: ver acciones/programas.py (cualquier app instalada)
# sistema.py, web.py, recordatorios.py: ver cada módulo

# acciones/agenda.py — guarda en agenda.json
agregar_evento(titulo: str, fecha_hora: str) -> str   # fecha_hora ISO 8601 local
listar_eventos(fecha: str = "") -> str                # fecha YYYY-MM-DD, vacío = próximos
borrar_evento(titulo: str) -> str

# herramientas.py
HERRAMIENTAS: list[dict]          # esquemas de tools formato OpenAI
ejecutar(nombre: str, argumentos: dict) -> str
LECTURA: set[str]                 # devuelven texto de terceros (web, pantalla, notas)
PELIGROSAS: set[str]              # los cerebros no las ejecutan tras una LECTURA en la misma petición (BLOQUEADA)

# cerebro.py
class Cerebro:
    responder(sesion_id: str, texto: str) -> str   # usa tools, máx ~25 s (servidor responde en dos pasos)
    olvidar(sesion_id: str) -> None
```
