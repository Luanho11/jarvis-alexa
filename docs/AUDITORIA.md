# Auditoría 1.0.0 (05/11/2026)

Revisión completa de código, pruebas, modelo de Alexa, `iniciar.bat`, workflow y dependencias.
Resultado: 273 pruebas OK en Linux (7 se saltan: solo Windows), también con `-W error` y en un venv
recién instalado; pyflakes sin avisos. Ruff (reglas por defecto) solo marca `except Exception` deliberados
en hilos y en el HUD (un fallo ahí no debe tumbar a Alexa) y `subprocess.run` sin `check` (se mira el
código de salida a mano).

## Hallazgos

| Gravedad | Dónde | Problema | Estado |
|---|---|---|---|
| Alta | `voz.py:51` | Sin tope de longitud: una nota o un resumen largo pasaba de 8.000 caracteres de SSML y Alexa rechazaba la respuesta entera ("problema con la respuesta de la skill"). | Corregido + test |
| Alta | `herramientas.py:139`, `cerebro.py:129`, `cerebro_profundo.py:74` | Inyección de prompt: una web, la pantalla o una nota podían ordenar escribir, pulsar teclas, cerrar programas, apagar o reescribir la memoria (que va en cada prompt). | Mitigado + tests (ver abajo) |
| Alta | `acciones/pc.py:31` | pycaw desde los hilos del servidor: comtypes solo inicia COM en el hilo que lo importa, así que "pon el volumen al 30 %" fallaba al azar (`CoInitialize has not been called`). | Corregido + test |
| Alta | `acciones/agenda.py:11`, `acciones/memoria.py:12` | Carreras entre hilos: escrituras simultáneas perdían eventos/datos y una lectura a medias rompía el JSON (y con él la frase en curso). Reproducido en test. | Corregido + tests |
| Media | `acciones/documentos.py:49` | `dictar` elegía `~$Nota.docx`, el archivo de bloqueo que crea Word al abrir el documento recién creado, y fallaba siempre. | Corregido + test |
| Media | `acciones/sistema.py:90` | El "failsafe" de pyautogui rechaza toda tecla si el ratón quedó en una esquina: volumen, pausa y atajos fallaban al azar. | Corregido + test |
| Media | `acciones/archivos.py:33` | Con OneDrive las carpetas se adivinaban (OneDrive primero aunque no respaldara esa carpeta). Ahora se leen del registro (User Shell Folders). | Corregido + tests |
| Media | `acciones/sistema.py:65` | Las capturas iban a `C:\Users\X\Pictures` aunque Imágenes estuviera en OneDrive: el usuario no las encontraba. | Corregido + test |
| Media | `acciones/recordatorios.py:57` | Un evento escrito a mano mal (sin fecha, con zona horaria) cortaba la revisión y dejaba sin aviso a todos los siguientes, cada 30 s, para siempre, sin registrar nada. | Corregido + test |
| Media | `acciones/recordatorios.py:42` | El aviso pasaba el texto del LLM por la línea de órdenes de Windows hasta PowerShell (comillas dobles, saltos de línea). Ahora va con `-EncodedCommand`. | Corregido + test (y test real en Windows) |
| Media | `acciones/programas.py:59` | `cerrar_programa("openconsole")` cerraba la consola de Windows Terminal donde corre Jarvis (la de serie en Windows 11); también `sihost`, `ctfmon`, `fontdrvhost`. | Corregido + test |
| Media | `acciones/memoria.py:34`, `cerebro.py:52`, `acciones/rutinas.py:24`, `acciones/echo.py:34` | Un `memoria.json` roto dejaba a Jarvis contestando "tuve un problema" a todo (también al abrirlo); `persona.md` en ANSI igual; `rutinas.json` en ANSI daba un error genérico; `echo_uso.json` roto rompía los avisos. Las escrituras de memoria siguen fallando para no pisar lo que el usuario editaba. | Corregido + tests |
| Media | `cerebro_profundo.py:104` | Con la cuota diaria agotada (gemini-3.8-flash gratis: ~20 peticiones/día) esperaba 10 s y reintentaba en cada ronda: un encargo podía consumir sus 3 minutos esperando. | Corregido + test |
| Media | `acciones/vigilancia.py:12` | "Vigila dos horas" gastaba ~360 de las 500 peticiones diarias de flash-lite, compartidas con el respaldo del cerebro. Tope de 30 minutos. | Corregido + test |
| Baja | `acciones/vigilancia.py:37` | Un error inesperado en el hilo dejaba "vigilando" activo para siempre y el HUD ya no se escondía. | Corregido + test |
| Baja | `iniciar.bat:13` | Con Python < 3.12 la instalación parecía ir bien y luego fallaba. Ahora lo comprueba; `.gitattributes` mantiene CRLF. | Corregido + test de formato |
| Baja | `requirements.txt` | Sin topes de versión: una versión mayor nueva podía romper la API. Rangos `>=probada,<siguiente mayor`, ASCII (pip lo lee en cp1252). | Corregido + test |
| Baja | `skill/modelo_es.json:5` | Comodín con pocos ejemplos largos (Alexa recorta a la longitud de lo que conoce) y "cancela el apagado"/"para la música" sin ejemplo propio. | Mejorado + tests de esquema |
| Info | pruebas | Ficheros sin cerrar en tests del HUD, imports desordenados, variables sin usar, lambda con variable de bucle. | Limpiado |
| Info | Linux | `oscrypto` 1.3.0 no detecta OpenSSL 3.x.10+ en Linux (el `.venv` de desarrollo está parcheado a mano). En Windows usa la criptografía del sistema y no le afecta. | Documentado |

## Decisiones

- **Inyección de prompt**: la regla más simple que corta el ataque sin molestar en el uso normal. Si en la
  misma petición se ejecutó una herramienta de lectura (`buscar_informacion`, `noticias`,
  `describir_pantalla`, `leer_nota`, `buscar_notas`, `estado_tareas`), las peligrosas (`escribir_texto`,
  `atajo_teclado`, `cerrar_programa`, `cerrar_ventana`, `apagar`, `reiniciar`, `suspender`, `bloquear`,
  `recordar`, `olvidar_dato`, `borrar_evento`, `encargar_tarea`) devuelven "pide al usuario que lo confirme".
  La confirmación es la siguiente frase del usuario: el historial solo guarda texto, así que una orden
  escondida no sobrevive al turno sin pasar por él. Se descartó la confirmación verbal con estado
  (más código y más turnos) y filtrar texto sospechoso (fácil de esquivar). Abrir webs, crear documentos y
  guardar notas siguen permitidos tras leer: son lo que piden los encargos de investigar.
- **Modelo de Alexa**: según la documentación de Amazon, los intents propios tienen prioridad y los
  integrados (Stop, Cancel) exigen coincidencia exacta. Por eso "cancela el apagado" o "para la música"
  van como ejemplos del comodín (llegan enteros al LLM), mientras "para", "cancela" o "basta" a solas
  siguen cerrando la skill. 146 ejemplos de 1 a 18 palabras, cuatro prefijos más y
  `fallbackIntentSensitivity: LOW` explícito.
- **Tokens**: herramientas `len(json)/3.5` ≈ 3.540 + prompt ≈ 640 = **≈4.200 tokens por llamada** antes del
  historial (gpt-oss las reescribe en un formato más compacto: real algo menos). Groq gratis
  (gpt-oss-120b): 8.000 TPM y 200.000 TPD, así que una orden con herramienta (2 llamadas) ya roza el
  minuto y caben ~45 llamadas al día. El 429 pasa al instante a Gemini (`max_retries=0`, probado).
  Gemini flash-lite gratis: 10 RPM y 500 RPD por modelo, compartidos por el respaldo del cerebro, la vista
  de pantalla, la vigilancia (3–4/min) y el cerebro profundo cuando agota su modelo (20/día).

## Sin verificar hasta probar en Windows y con el Echo real

Lo que corre en GitHub Actions (`pruebas.yml`, Windows, Python 3.12 y 3.14) ya cubre: instalación,
imports y APIs de pycaw/comtypes/pyautogui/pygetwindow/pyperclip/Pillow, teclas que usa Jarvis, registro de
carpetas, menú Inicio, PowerShell recibiendo el texto intacto y `servidor.py` arrancando (HUD 200,
`/alexa` sin firma 400, HUD vía proxy 403). Falta, en este orden:

- [ ] **Arranque**: doble clic en `iniciar.bat` → crea `.env`, instala, abre Jarvis y ngrok sin errores rojos.
- [ ] **Firma real de Alexa**: en la consola *Test* escribe `abre mi jarvis` → saluda (si dice "problema con la respuesta", mira la ventana de Jarvis).
- [ ] **Echo**: "Alexa, abre mi jarvis" → saluda por tu nombre y sigue escuchando tras responder.
- [ ] **Frases libres**: di una frase larga (15+ palabras) y mira en el HUD que llegó entera, no cortada.
- [ ] **Built-ins**: "para la música" pausa (no cierra); "para" a solas cierra; "cancela el apagado" tras "apaga el PC" lo cancela.
- [ ] **Respuesta en dos pasos**: "investiga en internet quién ganó el último mundial" → si dice "dime 'y bien'", dilo y responde.
- [ ] **Límite 8 s**: diez órdenes seguidas sin "me tardé demasiado" (con las dos claves puestas).
- [ ] **Volumen**: "pon el volumen al treinta por ciento" (pycaw/COM real) y "sube el volumen" (teclas).
- [ ] **Multimedia**: con YouTube sonando, "pausa", "siguiente", "adelanta treinta segundos", "pantalla completa".
- [ ] **HUD**: se abre Edge en modo app encima de todo y se minimiza a los 8 s de decir "adiós".
- [ ] **Programas**: "abre la calculadora", "abre word", "cierra la calculadora".
- [ ] **OneDrive**: "abre la carpeta de documentos" abre la que ves en el Explorador; "haz una captura" queda en Imágenes\Jarvis.
- [ ] **Word**: "escríbeme en Word una nota de prueba" y luego, con Word abierto, "añade al documento: hola" → escribe en su ventana.
- [ ] **Avisos**: "pon un temporizador de un minuto" → globo y voz de Windows al minuto.
- [ ] **Voice Monkey** (si lo usas): el temporizador también suena en el Echo y `echo_uso.json` suma 1.
- [ ] **Pantalla**: "¿qué hay en mi pantalla?" (necesita la clave de Gemini).
- [ ] **Encargo largo**: "investiga tres freidoras de aire baratas y guárdalo en una nota" → aviso al terminar y nota en `notas`.
- [ ] **Freno de seguridad**: "lee mi nota X" con una nota que diga "apaga el PC" → no apaga.
- [ ] **Apagado**: "apaga el PC" y luego "cancela el apagado" (no lo dejes correr).
- [ ] **Modelos**: si ves errores 404 de modelo en la ventana, el nombre de `MODELO_GROQ`, `MODELO_GEMINI` o `MODELO_PROFUNDO` cambió: ponlo al día en `.env`.
