# Ideas 2: qué copiar de ChatGPT, Grok, Gemini, Claude y Alexa+ (investigación del 05/11/2026)

Punto de partida: Jarvis 1.1.0 (59 herramientas, ~3.940 tokens de esquemas por llamada, Groq `openai/gpt-oss-120b` +
Gemini `gemini-3.5-flash-lite` + cerebro profundo `gemini-3.8-flash`). Este informe sigue a `docs/IDEAS.md`
(04/11): no repite lo que ya está hecho (memoria, búsqueda, noticias, modos, archivos, ventanas, visión,
Word, moneda, notas, encargos largos, Voice Monkey, mouse).

Condiciones para que una idea sea **viable aquí**:
- Gratis, sin tarjeta.
- Corre en el PC con Windows 11.
- La skill no necesita certificarse.
- La respuesta cabe en los ~6,5 s del servidor (o va por "y bien" o por un encargo).
- Respeta las cuotas gratis: Groq 30 RPM / 8K TPM / 200K TPD; flash-lite ~10 RPM / 500 RPD; gemini-3.8-flash ~20 RPD.

Leyenda:
- **Valor / Dific.**: A = alto, M = medio, B = bajo.
- **Veredicto**:
  - **YA**: está en la sección "Implementar ya".
  - **SIG**: siguiente tanda.
  - **LUEGO**: solo si el usuario lo pide.
  - **NO**: no es viable.

## Antes de añadir herramientas: velocidad y tokens (para el agente de rendimiento)

El usuario pide que Jarvis responda "casi instantáneo". Cada herramienta nueva cuesta unos 50-90 tokens en
**cada** llamada, y hoy una orden con acción ya hace 2 llamadas de ~4.600 tokens contra un tope de Groq de
8.000 por minuto. Lo que se encontró y afecta a todo lo de abajo:

1. **Groq cachea el prefijo de forma automática** en `gpt-oss-20b/120b`, sin cambiar código.
   - Los tokens cacheados son más rápidos.
   - Según la página de límites, "no cuentan para los límites" (la de caching matiza que se descuentan
     después de procesarse).
   - Solo acierta si el **comienzo** del prompt es idéntico: el caché caduca a las ~2 h sin uso y exige
     un mínimo de 128-1024 tokens.
   - Hoy `cerebro.prompt_sistema()` mete la hora (`%H:%M`) y `memoria.json` en mitad del mensaje de sistema.
     En el formato *harmony* de gpt-oss, las instrucciones van **antes** que las herramientas, así que es
     probable que el prefijo cambie cada minuto y que los ~3.900 tokens de herramientas nunca se cacheen.
   - **Arreglo**: dejar fijos persona y reglas, y pasar fecha/hora, memoria y persona activa a un mensaje
     `system` final, detrás del historial, o al principio del último mensaje del usuario.
   - Hay que comprobarlo con `respuesta.usage.prompt_tokens_details.cached_tokens`.
2. **`reasoning_effort="low"`** en el cerebro rápido. Groq lo admite en gpt-oss: menos tokens de
   razonamiento y menos latencia. Hoy no se pasa. En Gemini por la API compatible, probar
   `reasoning_effort="none"` o `"low"`.
3. **Atajo local sin LLM** para órdenes fijas: volumen, pausa, siguiente, "y bien", dictado (ver YA-8)
   y resumen del día. Un diccionario de frases normalizadas que llame a `herramientas.ejecutar` directo
   responde en <100 ms y no gasta cuota.
4. **Enrutar herramientas**: mandar solo un subconjunto por categoría (media, sistema, info, agenda...),
   elegido por palabras clave, más un núcleo fijo. Es la única forma de que caben las ~11 herramientas
   nuevas de este informe sin empeorar el 429 de Groq.
   - Ojo: un subconjunto distinto por llamada rompe el caché del punto 1.
   - Por eso el orden debe ser estable: núcleo fijo primero y categoría después; o pocos subconjuntos
     fijos, que se cachean cada uno.

Las especificaciones de abajo están pensadas para sumar pocos tokens: descripciones de ≤8 palabras y
reutilizar herramientas existentes cuando se puede (por ejemplo, las personalidades van dentro de
`activar_modo`).

## Tabla priorizada

| # | Función | De quién viene | Valor | Coste | Dific. | Riesgos | Cómo encaja | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 1 | Resumen del día / briefing ("buenos días": fecha, clima con máx/mín y lluvia, citas de hoy, encargos terminados, 3 titulares) | ChatGPT Pulse, Gemini Daily Brief, briefing de Alexa | A | Gratis, 0 llamadas LLM extra | B | Que tarde: fuentes en paralelo con tope de 4 s | Reutiliza `web.clima`, `agenda`, `info.noticias`, `cerebro_profundo` | **YA** |
| 2 | Tareas programadas y recurrentes ("cada día a las 7 dime el resumen", "los lunes recuérdame la basura", "cada viernes investiga ofertas") | ChatGPT Tasks, Gemini Scheduled actions (de pago en Gemini), Grok Tasks, Claude Cowork | A | Gratis. Al Echo solo con Voice Monkey (150 avisos al mes) | M | Disparar dos veces, disparar tarde tras apagar el PC, gastar las 20 RPD con encargos | Vigilante de `recordatorios` (30 s) + `avisar()` + `cerebro_profundo.encargar_tarea` | **YA** |
| 3 | Leer, traducir y resumir lo copiado en el portapapeles; copiar el resultado | Copilot/ChatGPT de escritorio ("trabajar con apps") | A | Gratis (`pyperclip` ya está) | B | Datos sensibles que salen a Groq o Gemini; inyección (va en LECTURA) | Módulo nuevo; el LLM traduce o resume con el texto devuelto | **YA** |
| 4 | Interpretar documentos locales y webs: "resume este PDF", "¿qué dice el contrato?", "lee esta página". Base de la investigación profunda con fuentes | ChatGPT (archivos), Claude Projects/Research, Gemini Deep Research, NotebookLM | A | Gratis (`pypdf`, `trafilatura`) | M | PDFs escaneados sin texto, PDFs enormes, SSRF a la red local, inyección | Usa la búsqueda de `archivos`; el cerebro profundo lo usa para leer fuentes | **YA** |
| 5 | Cálculos y conversiones exactos con Python, no con el LLM | Code interpreter de ChatGPT, ejecución de código de Gemini, herramienta de análisis de Claude | A | Gratis (`pint`) | B | `eval` inseguro, exponentes gigantes | Complementa `convertir_moneda` | **YA** |
| 6 | Personalidades tipo Gems: profesor, entrenador, traductor, entrevistador, cocinero; el usuario crea las suyas en `.md` | Gems de Gemini, GPTs de ChatGPT, modos y companions de Grok, estilos de Claude | A | Gratis, 0 herramientas nuevas | B | Que una persona relaje las reglas de seguridad; confusión con los modos de `rutinas.json` | Amplía `activar_modo` y `listar_modos`; la persona va al final del prompt | **YA** |
| 7 | Gmail (leer no leídos) y Google Calendar (ver y crear citas) gratis y sin OAuth semanal, con un puente de Google Apps Script | Extensiones de Gemini, conectores de ChatGPT y Claude | A | Gratis (Apps Script consumer: 20.000 lecturas de correo y 5.000 eventos al día) | M | URL del puente + clave = acceso a tu correo; inyección desde correos; arranque en frío de 1-4 s | `listar_eventos` une agenda local y Google; el resumen del día cuenta los correos | **YA** |
| 8 | Dictado continuo: cada frase se escribe tal cual, sin LLM, hasta "fin del dictado", con "punto", "coma" y "nueva línea" | Dictado de Windows, modo voz de ChatGPT | A | Gratis, 0 tokens | M | Alexa corta frases más largas que los ejemplos del modelo; perder el modo al cerrarse la sesión | `servidor.py` hace de atajo; `sistema.escribir_texto` y `documentos.dictar` | **YA** |
| 9 | "Muéstramelo en pantalla": respuestas largas (receta, comparativa, código, tabla) en el HUD, y en voz solo el resumen | Canvas de ChatGPT y Gemini, Artifacts de Claude | M-A | Gratis | B | XSS si el HUD pinta HTML del LLM o de una web: solo `textContent` | `panel.emitir` + HUD | SIG |
| 10 | Investigación profunda con informe y fuentes citadas (Word con lista de URLs) | Deep Research de los cuatro | A | Gratis; ~6-10 de las 20 RPD de 3.8-flash por informe | M | Agota la cuota diaria; fuentes inventadas: citar solo URLs leídas | `cerebro_profundo` + YA-4. Es sobre todo un prompt y un pie de fuentes en `crear_documento` | SIG (tras YA-4) |
| 11 | Memoria que aprende sola (extraer datos y preferencias al final de cada conversación) y diario de conversaciones ("¿qué te pedí ayer?") | Memoria de ChatGPT (historial), memoria de Claude, Grok | A | Gratis, 1 llamada de flash-lite por sesión | M | Guardar basura o inyecciones: solo turnos del usuario | `memoria.py` y `notas` | En curso por otro agente (ver `EVALUACION.md`) |
| 12 | Memoria de proyectos: "proyecto mudanza" con sus notas y un resumen que se inyecta mientras está activo | Projects de ChatGPT y Claude, Notebooks de Gemini | M | Gratis | M | Prompt más largo; rompe el caché si va al principio | Notas con etiqueta `proyecto:X` + persona activa (YA-6) | SIG |
| 13 | Generar imágenes gratis ("hazme una imagen de...") que se abren en el visor o en el HUD | ChatGPT Images, Gemini, Grok Imagine | M | Cloudflare Workers AI gratis: 10.000 neuronas/día; `flux-1-schnell` 1024² ≈ 58 → ~170 imágenes al día. Cuenta gratis y token | B-M | Servicio de terceros; tarda 2-5 s (usar "y bien") | Módulo nuevo, abre con `os.startfile` | SIG |
| 14 | Domótica: disparar rutinas de Alexa (luces y enchufes que ya maneja Alexa) desde Jarvis | Alexa+, Gemini Home, Google Home | M (si tiene aparatos) | Voice Monkey gratis: cada disparo gasta del cupo de 150/mes | M | Cupo compartido con los avisos | `acciones/echo.py` ya habla con Voice Monkey; un "speaker" por rutina | SIG (preguntar si tiene aparatos) |
| 15 | Domótica local sin Alexa (`python-kasa`, `tinytuya`) | Google Home, Alexa | M | Gratis si tiene esas marcas | M | Depende de la marca; Tuya exige sacar la clave local | Módulo nuevo | LUEGO |
| 16 | Mirar por la webcam ("¿qué tengo en la mano?", "¿qué planta es esta?") | Gemini Live con cámara / Project Astra, ChatGPT voz con video, Grok cámara | M | Gratis (`opencv-python`, ~40 MB) + 1 petición de flash-lite | B | Privacidad: la foto va a Google; la luz del LED | `vision.mirar_pantalla` con otra fuente de imagen | SIG |
| 17 | Traducción en vivo frase a frase por el Echo (persona traductor con `<lang xml:lang="en-US">`) | Gemini Live Translate, ChatGPT voz | M | Gratis | B | Acento español al leer inglés (la voz `<voice>` no existe en es-MX) | Dentro de YA-6 | YA (como persona) |
| 18 | Conversación de voz en tiempo real (interrumpir, sin "Alexa") | Modo voz avanzado de ChatGPT, Gemini Live, Grok voz | A | Gemini Live API es gratis (`gemini-3.8-live`), pero no pasa por el Echo | A | Otro programa entero (micrófono, eco, VAD) | No encaja con la Custom Skill | LUEGO (cliente aparte en el PC) |
| 19 | Agente que navega y hace gestiones (rellenar formularios, comprar, iniciar sesión) | ChatGPT Agent/Operator, Claude for Chrome, Gemini Agent | M | Playwright gratis con Edge (`channel="msedge"`), pero cada paso manda miles de tokens | A | Compras o envíos no deseados, credenciales, inyección desde webs; no cabe en 8K TPM ni en 20 RPD | Solo la parte de **leer** (YA-4) | **NO** (gestiones) / YA (leer) |
| 20 | Conectores MCP (Jarvis como cliente de servidores MCP) | Claude, ChatGPT (apps), Groq remote MCP | B-M | SDK `mcp` 2.3 gratis | M-A | El MCP remoto de Groq exige una URL HTTPS pública que Groq llame; cada servidor suma herramientas y tokens | Duplicaría lo que ya hacen los módulos | LUEGO |
| 21 | Jarvis como servidor MCP (que Claude Desktop o Cursor usen sus 59 acciones) | Ecosistema MCP | B | Gratis | M | Otra superficie que controla el PC | Envolver `herramientas.FUNCIONES` | LUEGO |
| 22 | Búsqueda en tiempo real en X | Grok | B | API de X y de Grok de pago | - | - | - | **NO** |
| 23 | Búsqueda nativa del LLM (grounding de Google / `browser_search` de Groq) | Gemini, Groq | M | No hay grounding gratis en Gemini 3.x (solo en 2.5 Flash, cerrado a proyectos nuevos); el de Groq es de pago | - | Coste | `ddgs` + Wikipedia ya lo cubre | **NO** |
| 24 | Imágenes con Gemini (Nano Banana / Flash Image) | Gemini | M | **Sin plan gratis** en la API | - | - | Alternativa: #13 | **NO** |
| 25 | Video generado (Gemini Omni, Grok Imagine video, Sora) | Gemini, Grok, ChatGPT | B | De pago | - | - | - | **NO** |
| 26 | Companions 3D con avatar (Ani, Rudi...) | Grok | B | SuperGrok de pago; no hay pantalla en el Echo Dot | - | Contenido inapropiado | La personalidad ya es configurable (YA-6) | **NO** |
| 27 | Enviar correos o WhatsApp por voz | Gemini, ChatGPT Agent | M | Gratis (Apps Script `GmailApp.sendEmail`) | B | Alto riesgo social: un error de dictado o una inyección escribe a quien no toca | - | LUEGO, con confirmación leída en voz y solo a contactos guardados |
| 28 | Voz más natural en el PC (Gemini TTS) | Gemini | B-M | `gemini-3.8-flash-tts` gratis en la API | B | Cuota y latencia; el Echo sigue usando la voz de Alexa | Avisos del PC (`recordatorios.avisar`) | LUEGO |
| 29 | Alexa+ (Alexa con IA generativa) | Amazon | - | Gratis con Prime en México, acceso anticipado desde enero de 2026 | - | Puede desviar frases a funciones propias en vez de a la skill; no se confirma que llegue al Echo Dot 5 | Las skills siguen siendo compatibles; si algo deja de entrar, "Alexa, termina el acceso anticipado" | Informativo: probar Jarvis primero sin Alexa+ |
| 30 | Disparar el resumen desde una rutina de Alexa (acción "Personalizada": "pide a mi jarvis mi resumen del día" a las 7:00) | Rutinas de Alexa | A | Gratis y sin gastar Voice Monkey | B | No documentado que la acción personalizada abra una skill en desarrollo: **validar en el Echo real** | Plan A de YA-2 para el briefing; plan B, Voice Monkey | YA (validar) |

## Implementar ya

Normas comunes, las de `AUTONOMIA.md`:
- Cada función devuelve un texto corto en español para decir en voz alta.
- Se registra en `HERRAMIENTAS` y `FUNCIONES` de `herramientas.py`.
- Lo que devuelve texto de terceros entra en `LECTURA`; lo que actúa o persiste, en `PELIGROSAS`.
- Pruebas con pytest sin red, con dobles de prueba.
- Las dependencias van en `requirements.txt` con tope de versión mayor y en ASCII.
- Los JSON se escriben de forma atómica (tmp + `os.replace`), bajo candado, y un archivo roto no tumba
  a Jarvis.

### YA-1. Resumen del día (`resumen_del_dia`)

- **Archivo**: `acciones/resumen.py`.
- **Firma**: `resumen_del_dia() -> str`.
- **Herramienta**: `_herramienta("resumen_del_dia", "Resumen de hoy: clima, citas, avisos y titulares.")`.
  Entra en `LECTURA` porque lleva titulares de internet.
- **Qué hace**: lanza en paralelo, con `concurrent.futures.ThreadPoolExecutor(max_workers=4)` y un tope
  total de 4 s (`wait(..., timeout=4)`), estas fuentes:
  1. `web.pronostico_hoy()`: añadir a `web.py`. Es la misma llamada a wttr.in `format=j1`, más
     `weather[0].maxtempC/mintempC` y la probabilidad de lluvia máxima de `hourly[*].chanceofrain`.
  2. `agenda.eventos_de(fecha_hoy)`: helper que devuelve la lista, no el texto, para poder contar.
     Si YA-7 está configurado, se unen los eventos de Google.
  3. `info.titulares(3)`: helper que devuelve una lista; `noticias()` pasa a usarlo.
  4. `cerebro_profundo` (encargos terminados, **sin consumirlos**: contar, no llamar a
     `resultados_pendientes()`), los no leídos de YA-7 y las tareas programadas de hoy de YA-2.
- **Formato**: una fuente que falla o no llega a tiempo se omite sin decir nada. Ejemplo:
  "Hoy es jueves 5 de noviembre. En Monterrey 24 grados, máxima 29 y 10 % de lluvia. Tienes 2 citas:
  dentista a las 15:00 y fútbol a las 19:00. Titulares: ...". Como máximo unos 600 caracteres.
- **Atajo sin LLM**: "buenos días", "resumen del día", "mi resumen" y "¿qué hay hoy?" van directos desde
  el atajo local (punto 3 de velocidad), sin pasar por el LLM. La rutina de Alexa de la fila 30 llama a
  esta frase.
- **Dependencias**: ninguna nueva.
- **Pruebas**:
  - Con todas las fuentes simuladas, el texto contiene clima, citas y titulares.
  - Una fuente que lanza excepción no impide las demás.
  - Una fuente que duerme 5 s se omite y la función devuelve en menos de 4,5 s.
  - Sin citas dice "No tienes citas hoy".
  - Los encargos pendientes no se consumen: una llamada posterior a `resultados_pendientes()` los sigue
    teniendo.
  - Longitud ≤ 600.
  - La herramienta está en `LECTURA`.

### YA-2. Tareas programadas y recurrentes

- **Archivo**: `acciones/programadas.py`. Datos en `programadas.json`; ruta configurable con
  `PROGRAMADAS_ARCHIVO`, como en `memoria.py`.
- **Firmas**:
  ```python
  programar_tarea(que: str, hora: str, dias: str = "todos", tipo: str = "aviso") -> str
  # hora "HH:MM"; dias: "todos" | "laborables" | "fines" | "lunes,miércoles" | "2026-11-20" (una vez)
  # tipo: "aviso" (dice `que`), "resumen" (resumen_del_dia), "encargo" (cerebro_profundo.encargar_tarea(que))
  listar_programadas() -> str
  borrar_programada(que: str) -> str          # por coincidencia normalizada, como borrar_evento
  revisar(ahora: datetime) -> None            # la llama el bucle de recordatorios._vigilar cada 30 s
  ```
- **Herramientas** (3, descripciones cortas): `programar_tarea` y `borrar_programada` entran en
  `PELIGROSAS` (una web no debe poder programar un encargo diario); `listar_programadas` no.
  `programar_tarea` también entra en `cerebro_profundo.EXCLUIDAS`.
- **Registro**: `{"id": uuid4().hex[:8], "que", "hora", "dias", "tipo", "ultima": "YYYY-MM-DD" | null}`.
- **Disparo**: si `dias` incluye hoy, `hora <= ahora < hora + 10 min` y `ultima != hoy`, entonces:
  1. Guardar primero `ultima = hoy`. Así no se repite tras un reinicio, y si el PC estuvo apagado a esa
     hora no se dispara una hora tarde.
  2. Ejecutar en un hilo. `aviso` y `resumen` van por `recordatorios.avisar(texto)` (HUD + voz del PC +
     Echo con Voice Monkey); `encargo` lanza `encargar_tarea`, que ya avisa al terminar.
  3. Una fecha concreta se borra al dispararse.
- **Límites**:
  - Como máximo 20 tareas.
  - Como máximo 3 de tipo `encargo` disparadas al día, por las 20 RPD de `gemini-3.8-flash`. El contador
    va en el mismo JSON.
  - `hora` mal escrita → "Dime la hora como 7:30".
- **Prompt** (una línea en `cerebro.prompt_sistema`): "Para pedidos recurrentes ('cada día', 'todos los
  lunes') usa programar_tarea; para una cita única, agregar_evento".
- **Dependencias**: ninguna.
- **Pruebas**:
  - `dias`: "laborables" no dispara en sábado; la lista con tildes y sin tildes; una fecha única dispara
    y se borra.
  - Dispara una sola vez aunque `revisar` se llame 20 veces en la ventana.
  - Tras "reiniciar", con `ultima` en disco, no repite.
  - Pasados 10 minutos de la hora no dispara.
  - JSON roto: `revisar` no lanza y `programar_tarea` se niega a sobrescribir.
  - El cuarto encargo del día no se lanza.
  - Las dos herramientas están en `PELIGROSAS` y bloqueadas tras una LECTURA.
  - El tope de 20 tareas funciona.
  - Hilos: dos `programar_tarea` simultáneas no pierden datos.
- **Echo**: documentar en el README la rutina de la fila 30 (validar) y, como respaldo, Voice Monkey.
  Un resumen diario son unos 30 avisos al mes del cupo de 150.

### YA-3. Portapapeles

- **Archivo**: `acciones/portapapeles.py`.
- **Firmas**:
  ```python
  leer_portapapeles() -> str        # LECTURA. "Lo copiado: <texto>" recortado a 4.000 caracteres; "El portapapeles está vacío o no tiene texto."
  copiar_al_portapapeles(texto: str) -> str   # "Copiado."
  ```
- **Herramientas**: `leer_portapapeles` ("Texto copiado por el usuario.") y `copiar_al_portapapeles`
  ("Copia texto al portapapeles."). `copiar_al_portapapeles` **no** va en `PELIGROSAS`: "tradúcelo y
  cópialo" es el uso normal en la misma petición y sobrescribir lo copiado es reversible.
- **Detalles**:
  - Importar `pyperclip` dentro de la función, como en `sistema.py`; fuera de Windows devuelve "Solo
    funciona en Windows".
  - No registrar nunca el contenido en logs ni en el HUD (solo "accion leer_portapapeles").
  - Si pasa de 4.000 caracteres, recortar y añadir: "(es largo; para resumirlo entero pídemelo como
    encargo)".
  - Avisar en el README de que lo copiado se envía al LLM.
- **Prompt**: "'traduce, resume o explica lo que copié' → leer_portapapeles".
- **Dependencias**: ninguna (`pyperclip` ya está).
- **Pruebas**: con `pyperclip` simulado; vacío; solo espacios; 10.000 caracteres recortados con el aviso;
  `copiar` llama a `pyperclip.copy`; `leer_portapapeles` en `LECTURA`; sin `pyperclip` da un mensaje
  amable.

### YA-4. Leer documentos y páginas (`leer_documento`)

- **Archivo**: `acciones/lectura.py`.
- **Firma**:
  ```python
  leer_documento(origen: str, pagina_inicial: int = 1) -> str
  # origen: URL ("https://..." o "elpais.com/...") o nombre de archivo ("contrato", "el último pdf de descargas")
  ```
- **Herramienta**: "Lee un PDF, Word, texto o web.", en `LECTURA`.
- **Comportamiento**:
  - **URL**:
    - Solo `http`/`https`. Antes de pedirla, resolver el host con `socket.getaddrinfo` y **rechazar**
      IPs privadas, loopback, link-local y reservadas (`ipaddress.ip_address(...).is_global`). Evita
      que una web inyectada lea el HUD en `127.0.0.1:5000` o el router.
    - `requests.get(timeout=4, stream=True)`, leer como mucho 2 MB y comprobar `Content-Type`.
    - HTML → `trafilatura.extract(html, include_comments=False)`. Un PDF descargado se trata como
      archivo.
  - **Archivo**:
    - Reutilizar `archivos._buscar(normalizar(nombre))` (hacerlo público como `buscar_rutas`) con
      extensiones `.pdf .docx .txt .md .csv`.
    - "Último" o "más reciente" → el de `mtime` mayor en Descargas.
    - Si hay varios, devolver los 3 más recientes y preguntar, como `buscar_archivo`.
  - **Extracción**:
    - PDF: `pypdf.PdfReader`; páginas desde `pagina_inicial` hasta juntar 6.000 caracteres (≈1.700
      tokens, cabe en Groq). Encriptado → "Está protegido con contraseña". Sin texto (escaneado) →
      "Parece escaneado; ábrelo y pídeme que mire la pantalla".
    - `.docx`: `python-docx`.
    - Texto: `read_text(errors="replace")`.
  - **Salida**: "«Contrato.pdf», 12 páginas, págs. 1-3: <texto>…(sigue en la página 4)". El LLM resume
    o responde la pregunta.
  - **Documento largo**: "resúmelo entero" → `encargar_tarea`. El cerebro profundo ya recibe todas las
    herramientas no excluidas y avanza con `pagina_inicial`.
- **Investigación profunda (fila 10)**: añadir al prompt de `cerebro_profundo`: "Busca, abre 3-5 fuentes
  con leer_documento y cita al final solo las URL que leíste".
- **Dependencias**: `pypdf>=6.21,<7` (Python puro); `trafilatura>=2.3,<3` (usa `lxml`, que tiene ruedas
  para Windows con Python 3.12 y 3.14; comprobarlo en el CI de Windows).
- **Pruebas**:
  - PDF de 2 páginas generado en el test (o fixture pequeño en `tests/datos/`) → texto y número de páginas.
  - PDF encriptado (`PdfWriter.encrypt`) da el mensaje de contraseña.
  - PDF sin texto da el mensaje de escaneado.
  - `.docx` creado con `python-docx`.
  - Recorte a 6.000 con "sigue en la página N".
  - URL simulada → `trafilatura`.
  - `http://127.0.0.1:5000/hud`, `http://192.168.1.1` y `file:///C:/` rechazadas.
  - Respuesta de 5 MB cortada a 2 MB.
  - Timeout → "No pude abrir esa página".
  - No encontrado.
  - Varias coincidencias → pregunta.
  - En `LECTURA`.

### YA-5. Cálculos y conversiones exactos

- **Archivo**: `acciones/calculo.py`.
- **Firmas**:
  ```python
  calcular(expresion: str) -> str             # "Da 1.234,56" / "No puedo calcular eso."
  convertir_unidad(cantidad: float, de: str, a: str) -> str   # "5 millas son 8,05 kilómetros."
  ```
- **Herramientas**:
  - `calcular`: "Calcula exacto. Sintaxis Python: 15% de 200 → 200*15/100."
  - `convertir_unidad`: "Convierte unidades (km, millas, °C, °F, kg, libras, litros, tazas...)."
- **`calcular`**:
  - Se analiza con `ast.parse(expr, mode="eval")` y se recorre con una lista blanca, sin `eval`:
    `Constant` (int/float), `BinOp` (`+ - * / // % **`), `UnaryOp` (`+ -`), `Name` (`pi`, `e`) y `Call`
    a {`sqrt`/`raiz`, `sin`, `cos`, `tan`, `log`, `ln`, `log10`, `abs`, `round`, `factorial`}.
  - Antes de analizar, normalizar: `^`→`**`, `×`/`x` entre números → `*`, `÷`→`/`, coma decimal
    "3,5"→"3.5" cuando no es separador de miles.
  - Límites: exponente con `abs ≤ 1000`; `factorial(n)` con `n ≤ 170`; resultado con `abs < 1e100`;
    expresión de ≤ 200 caracteres.
  - División por cero → "No se puede dividir entre cero".
  - Formato: `round(x, 10)`, sin ceros sobrantes, hasta 6 decimales y miles legibles para voz.
- **`convertir_unidad`**:
  - `pint.UnitRegistry()` perezoso y cacheado; la primera carga tarda ~0,3 s, así que conviene hacerla
    al arrancar en un hilo.
  - Alias en español: kilómetros→km, millas→mile, metros→m, pies→ft, pulgadas→inch, kilos→kg,
    libras→lb, onzas→oz, litros→L, galones→gallon, tazas→cup, grados centígrados/celsius→degC,
    fahrenheit→degF, etc.
  - Temperaturas con `Quantity(cantidad, unidad)` (son unidades con desplazamiento).
  - Unidades incompatibles → "No se pueden convertir kilos a metros".
- **Prompt**: "Para cualquier cuenta o conversión usa calcular o convertir_unidad; no calcules de cabeza".
- **Dependencias**: `pint>=0.26,<1`.
- **Pruebas**:
  - `2+2*3` → 8; `0.1+0.2` → 0,3; `sqrt(16)` → 4; `2^10` → 1024; `200*15/100` → 30.
  - `2**100000` y `factorial(10000)` rechazados al momento (<50 ms).
  - `__import__('os')`, `().__class__` y `open('x')` rechazados.
  - `1/0` da el mensaje de cero.
  - 100 °F → 37,78 °C; 5 millas → 8,05 km; 2 tazas → litros.
  - kg→m incompatible; unidad desconocida.

### YA-6. Personalidades tipo Gems (sin herramientas nuevas)

- **Archivos**:
  - `acciones/personas.py`.
  - Carpeta `personas/` con `profesor.md`, `entrenador.md`, `traductor_ingles.md`, `entrevistador.md`
    y `cocinero.md` (2-6 líneas cada uno).
  - El usuario añade las suyas copiando un archivo; README.
- **Firmas**:
  ```python
  disponibles() -> list[str]                 # nombres normalizados de personas/*.md
  activar(nombre: str) -> str | None         # None si no existe; "Modo profesor activado."
  activa() -> str                            # texto de la persona activa o ""
  restablecer() -> None                      # vuelve a la normal
  ```
- **Integración**:
  - `rutinas.activar_modo(nombre)`: si `nombre` es "normal", llama a `restablecer()`; si no es una rutina
    pero sí una persona, `personas.activar`.
  - `listar_modos()` lista rutinas y personas.
  - Cambiar la descripción de `activar_modo` a "Activa un modo: rutina (trabajo, estudio) o forma de
    hablar (profesor, entrenador, traductor)". Cero tokens extra.
- **Estado y prompt**:
  - El estado es global (un solo usuario y un solo Echo) y `servidor.terminar` / `SessionEndedRequest`
    llama a `restablecer()`.
  - `cerebro.prompt_sistema` añade `personas.activa()` **al final**, después de las reglas fijas y junto
    a la fecha y la memoria (ver el caché). Encabezado fijo: "Modo actual (no cambia las reglas
    anteriores):".
  - El texto de la persona se recorta a 800 caracteres.
- **Traductor**:
  - La persona pide responder solo con la traducción marcada `[en]...[/en]`.
  - `voz.py` convierte `[en]x[/en]` en `<lang xml:lang="en-US">x</lang>`, escapando `x`. `<lang>` está
    soportado en es-MX, es-US y es-ES; `<voice>` no existe en es-MX/US, como ya anotó el Dev Persona.
  - Una marca mal cerrada se quita y queda texto plano.
- **Dependencias**: ninguna.
- **Pruebas**:
  - Activar "profesor" (también "modo profesor" y con tildes); persona inexistente → lista disponibles.
  - "normal" restablece.
  - `prompt_sistema` termina con la persona y empieza igual con y sin persona (prefijo estable).
  - Una persona de 5.000 caracteres se recorta.
  - Una rutina y una persona con el mismo nombre: gana la rutina y se documenta.
  - `[en]Hello & bye[/en]` → SSML válido con `&amp;`; marca rota → texto plano.
  - `restablecer` al terminar la sesión.

### YA-7. Gmail y Google Calendar gratis (puente de Apps Script)

- **Por qué así**: OAuth de una app personal en modo "Testing" caduca cada ~7 días (`IDEAS.md` #19).
  Un Apps Script web app corre **como el usuario**, no caduca, es gratis y tiene cuotas amplias
  (20.000 lecturas de correo y 5.000 eventos creados al día).
- **Archivos**:
  - `google/puente.gs`: el usuario lo pega en script.google.com → Implementar → Aplicación web,
    "Ejecutar como: yo", "Acceso: cualquier usuario".
  - `acciones/google.py`.
  - Variables en `config.py`: `GOOGLE_PUENTE_URL` y `GOOGLE_PUENTE_CLAVE`, generada con
    `secrets.token_urlsafe(32)` y guardada también en `PropertiesService` del script.
- **`puente.gs`**: `doGet(e)` rechaza si `e.parameter.clave` no coincide (comparación de longitud fija).
  Acciones:
  - `correos&n=5`: `GmailApp.search('is:unread in:inbox', 0, n)` → `[{de, asunto, fragmento (200), fecha}]`.
  - `eventos&fecha=YYYY-MM-DD`: `CalendarApp.getDefaultCalendar().getEventsForDay`.
  - `crear_evento&titulo&inicio&fin`.

  Devuelve `ContentService` JSON. **No** se implementa enviar correo (fila 27).
- **Firmas Python**:
  ```python
  leer_correos(cantidad: int = 5) -> str      # LECTURA. "Tienes 3 sin leer: de Ana, 'Factura'... "
  eventos_google(fecha: str) -> list[dict]    # helper, no herramienta
  crear_evento_google(titulo: str, fecha_hora: str) -> bool   # helper
  ```
- **Integración**:
  - Una herramienta nueva: `leer_correos`.
  - `agenda.listar_eventos` une la agenda local y `eventos_google` si está configurado (se quitan los
    duplicados por título y hora).
  - `agenda.agregar_evento` también crea en Google si `GOOGLE_AGENDA=si`.
  - `resumen_del_dia` dice cuántos no leídos hay.
  - `requests.get(URL, params, timeout=5)`: Apps Script responde con una redirección 302 a
    googleusercontent, que `requests` sigue sola.
  - Sin configurar → "Para leer tu correo sigue la sección Google del README".
- **Seguridad**:
  - La URL y la clave nunca van a logs ni al HUD.
  - Los correos entran en `LECTURA`, así que el freno anti-inyección se aplica.
  - Solo asunto, remitente y fragmento; nunca adjuntos.
- **Dependencias**: ninguna.
- **Pruebas** (con `requests` simulado):
  - Correos correctos → frase.
  - 0 sin leer.
  - Clave incorrecta (el JSON trae `error`) → mensaje.
  - Timeout → "Google no respondió".
  - JSON roto.
  - Fragmento de 1.000 caracteres recortado.
  - `listar_eventos` sin duplicados.
  - Google caído → `listar_eventos` sigue con la agenda local.
  - `leer_correos` en `LECTURA`.
  - Test de formato: `puente.gs` contiene la comprobación de clave.

### YA-8. Dictado continuo (sin LLM)

- **Archivos**:
  - `acciones/dictado.py`.
  - Atajo en `servidor.py`, coordinado con el agente de servidor.
  - Más ejemplos largos en `skill/modelo_es.json`.
- **Firmas**:
  ```python
  activar_dictado(destino: str = "cursor") -> str   # "cursor" (escribe donde esté el cursor) o "word" (último documento)
  procesar(texto: str) -> str                       # aplica comandos de voz y escribe; devuelve "" o un aviso breve
  terminar_dictado() -> str                         # "Dictado terminado: 214 palabras."
  activo() -> bool
  ```
- **Herramienta**: `activar_dictado` ("Modo dictado: escribe todo lo que diga."), en `PELIGROSAS`
  (escribe en el PC).
- **Servidor**: si `dictado.activo()`, cada frase va a `dictado.procesar` **sin pasar por el cerebro**.
  - La respuesta es mínima: `<break time="200ms"/>`, con `should_end_session(False)` y repregunta
    "Sigo escribiendo".
  - Al salir de la sesión, `terminar_dictado`.
  - "fin del dictado", "termina el dictado", "deja de dictar" y "adiós" terminan.
- **Comandos locales**:
  - "punto", "coma", "dos puntos", "punto y coma", "signo de interrogación", "signo de exclamación".
  - "punto y aparte" / "nueva línea" / "nuevo párrafo".
  - "borra la última frase" (deshace el último trozo escrito: `ctrl+z` en Word; en el cursor, tantos
    `backspace` como caracteres escribió).
  - Mayúscula automática al empezar y tras `.?!`.
  - Alexa entrega minúsculas sin puntuación.
- **Modelo de Alexa**: el auditor anotó que Alexa recorta el comodín a la longitud de los ejemplos
  conocidos (hoy, como mucho 18 palabras). Añadir 5-8 ejemplos de 20-30 palabras y documentar que hay
  que dictar por frases.
- **Dependencias**: ninguna.
- **Pruebas**:
  - Con dictado activo, el cerebro simulado **no** se llama.
  - "hola punto qué tal signo de interrogación" → "Hola. ¿Qué tal?". El signo de apertura ¿/¡ se
    coloca al inicio de la frase.
  - "nueva línea" → `\n` (Word: párrafo nuevo con `documentos.dictar`).
  - "borra la última frase" deshace lo último.
  - Las frases de salida terminan y dan el total de palabras.
  - `SessionEnded` lo apaga.
  - La respuesta tarda menos de 200 ms con dobles.
  - `activar_dictado` bloqueado tras una LECTURA.
  - Destino "word" sin documento → "Primero crea un documento".

**Coste en tokens de "Implementar ya"**: +11 herramientas, unas +650 tokens por llamada (de ~3.940 a ~4.600).
Por eso conviene hacer antes, o a la vez, los puntos 1 y 4 de velocidad (caché del prefijo y enrutado).
Sin ellos, el orden por valor y tokens es: YA-1 (sale gratis por el atajo), YA-6 (0 herramientas),
YA-8 (fuera del LLM), YA-5, YA-3, YA-4, YA-2 y YA-7.

## Lo que NO es viable (y por qué)

- **Agente que hace gestiones en webs** (Operator, ChatGPT Agent, Claude for Chrome):
  - Cada paso manda capturas o árboles DOM de miles de tokens: con 8K TPM de Groq y 20 RPD de
    3.8-flash, una gestión de 15 pasos no cabe.
  - Iniciar sesión o pagar por voz, sin verlo, es un riesgo inaceptable, y las webs pueden inyectar
    órdenes.
  - Sí es viable la parte de leer (YA-4).
- **Voz en tiempo real a través del Echo** (modo voz avanzado de ChatGPT, Gemini Live, Grok voz):
  - Una Custom Skill recibe texto ya transcrito y devuelve SSML; no hay audio en streaming ni
    interrupciones.
  - Gemini Live es gratis, pero solo en un cliente aparte en el PC (fila 18).
- **Búsqueda en X en tiempo real** (Grok): la API de X y la de Grok son de pago.
- **Grounding con Google Search o `browser_search` de Groq**: no hay cupo gratis en Gemini 3.x (ver
  `IDEAS.md` #22); Groq lo cobra.
- **Imágenes con Gemini (Nano Banana / Flash Image)**: la tabla de precios marca "No disponible" en el
  plan gratis. La alternativa gratis es Cloudflare Workers AI (fila 13). Pollinations ya exige clave
  y saldo.
- **Video generado** (Gemini Omni, Grok Imagine, Sora): de pago.
- **Companions 3D** (Grok): exigen SuperGrok y no hay pantalla en el Echo Dot 5. La parte útil, una
  personalidad configurable, ya está y se amplía con YA-6.
- **Controlar desde la skill lo que maneja Alexa** (luces o enchufes de la app Alexa): una Custom Skill
  no tiene acceso. Solo a través de rutinas disparadas con Voice Monkey (fila 14) o en local (fila 15).
- **Que la skill hable sola sin Voice Monkey**: Proactive Events solo admite esquemas fijos y deja un
  aviso pendiente (`IDEAS.md`). La rutina con acción personalizada (fila 30) es la vía gratis a
  validar.
- **MCP remoto de Groq contra herramientas del PC**: Groq llama a una URL HTTPS pública. Exponer el PC
  así es peor que el diseño actual, que ya ejecuta las herramientas en local.

## Fuentes

- ChatGPT, 11 funciones en 2026 (Projects, Tasks, Memory, Deep Research, Voice, Canvas, apps): https://tomsguide.com/ai/chatgpt-isnt-just-a-chatbot-anymore-here-are-11-things-it-can-do-in-2026
- ChatGPT Pulse (briefing diario proactivo): https://www.tomsguide.com/ai/chatgpt-pulse-is-here-now-ai-starts-the-chat-and-curates-your-feed · https://gizmodo.com/chatgpt-pulse-openai-morning-briefing-2000663894
- ChatGPT Atlas y modo agente: https://openai.com/blog/introducing-chatgpt-atlas
- Gemini, 13 funciones en 2026 (Live con cámara y pantalla, Deep Research, Gems, Daily Brief, Scheduled actions de pago, Canvas, Notebooks): https://www.tomsguide.com/ai/gemini-isnt-just-a-chatbot-anymore-here-are-13-things-it-can-do-in-2026
- Scheduled actions de Gemini frente a Tasks de ChatGPT: https://www.tomsguide.com/ai/google-gemini/gemini-now-rivals-chatgpt-in-another-key-feature-heres-how-to-schedule-ai-tasks · https://piunikaweb.com/2026/02/28/google-gemini-goal-scheduled-actions-beta/
- Deep Research en Gemini Live (08/2026): https://jetstream.blog/2026/08/20/gemini-live-deep-research/
- Grok (voz, companions de pago, DeepSearch, Tasks, Imagine, memoria, workspaces): https://suprmind.ai/hub/grok/grok-features/ · voz con búsqueda en web y X: https://aigazine.com/llms/xai-grok-introduces-voice-mode-with-realtime-web-and-x-search--s · companions: https://apidog.com/blog/grok-companion-ani
- Claude 2026 (memoria gratis, Cowork con tareas programadas, conectores, Claude in Chrome, Dispatch): https://www.innobu.com/en/articles/claude-ai-2026-new-features.html · https://its.syr.edu/5-things-claude-can-do-now-that-it-couldnt-6-months-ago/
- Alexa+ en México (acceso anticipado, gratis con Prime, 399 MXN): https://www.xataka.com.mx/home/alexa-plus-llega-a-mexico-su-mejor-caracteristica-que-habla-mexicano-precios-planes · https://expansion.mx/tecnologia/2026/01/22/alexa-ya-esta-mexico-ia-mas-avanzada-amazon-precio · skills en Alexa+: https://support.aiir.com/article/1513-alexa-plus
- Rutinas de Alexa, acción personalizada: https://digprjsurvey.amazon.com/csad/help/node/GLXY7RFX3L5GH2VR · horarios: https://www.androidcentral.com/how-set-routines-your-amazon-echo
- SSML de Alexa (`<lang>` en es-MX/es-US/es-ES, límites de audio): https://developer.amazon.com/en-US/docs/alexa/custom-skills/speech-synthesis-markup-language-ssml-reference.html
- Límites de Groq (gpt-oss 30 RPM / 8K TPM / 200K TPD; los tokens cacheados no cuentan): https://console.groq.com/docs/rate-limits
- Prompt caching de Groq (automático, prefijo, TTL ~2 h, gpt-oss): https://console.groq.com/docs/prompt-caching
- `reasoning_effort` en gpt-oss: https://console.groq.com/docs/reasoning
- MCP remoto de Groq (URL HTTPS que Groq llama): https://console.groq.com/docs/mcp
- Precios y plan gratis de Gemini API (3.8-flash, 3.5-flash-lite, Live y TTS gratis; imagen no disponible; grounding gratis solo en 2.5 Flash): https://ai.google.dev/gemini-api/docs/pricing · https://ai.google.dev/gemini-api/docs/rate-limits
- Cloudflare Workers AI (10.000 neuronas/día gratis; coste de flux-1-schnell): https://developers.cloudflare.com/workers-ai/platform/pricing/
- APIs de imagen gratis (Pollinations ya exige clave): https://apiframe.ai/blog/free-ai-image-generation-api-2026
- Cuotas de Google Apps Script en cuentas consumer: https://developers.google.com/apps-script/guides/services/quotas
- Fin de POP/Gmailify en Gmail (01/2026): https://alternativeto.net/news/2025/10/google-is-ending-support-for-gmailify-and-pop-in-gmail-starting-january-2026
- Comparativa de APIs gratis de 2026: https://toolhalla.ai/blog/best-free-ai-apis-2026
- Versiones en PyPI consultadas el 05/11/2026: pypdf 6.21.4, trafilatura 2.3.1, pint 0.26.2, playwright 1.64.1, mcp 2.3.0, opencv-python 5.0.0.93.
