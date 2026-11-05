# Ideas de funciones: investigación del 04/11

Leyenda: **Valor** = utilidad para el usuario. **Dific.** = dificultad. Todo lo de la tabla es gratis salvo que se indique otra cosa.

## Primero: el límite de 8 s de Alexa (investigado a fondo)

- **La Progressive Response API NO amplía el plazo.** La skill tiene 8 s en total y las respuestas progresivas deben caber en esos mismos 8 s. Se permiten hasta 5 por petición, como máximo 600 caracteres cada una y siempre envueltas en `<speak>`. Se envían con `POST {context.System.apiEndpoint}/v1/directives`, usando el Bearer `context.System.apiAccessToken`, el `request.requestId` y la directiva `VoicePlayer.Speak`. Si va bien devuelve 204. Si ya se respondió, devuelve 401.
  Para qué sirve: decir "un momento…" mientras el LLM piensa. Así la espera se oye natural, pero el tope sigue siendo 8 s.
- **Patrón recomendado (async + "¿y bien?")**, el mismo que usan alexa-chatgpt y el proyecto Claude-por-Alexa:
  1. Se lanza el LLM en un hilo y se espera unos 6,5 s.
  2. Si termina, se responde normal.
  3. Si no termina, se dice "Sigo pensando, pregúntame *¿y bien?* en un momento" y se guarda el resultado por sesión.
  4. Un intent o tool `ultima_respuesta` lo lee.
  5. Para tareas largas, como un resumen o un documento, el PC lo dice en voz alta con TTS local, sin depender de Alexa.
- Otros límites: `outputSpeech` admite hasta 8000 caracteres. Fuera de la sesión, la skill no puede hablar por iniciativa propia, salvo con la Reminders API o con Proactive Events, que solo admite esquemas fijos y deja un aviso pendiente, no habla.

## Tabla priorizada

| # | Idea | Valor | Coste / requisitos | Dific. | Riesgos |
|---|------|-------|--------------------|--------|---------|
| 1 | Respuesta diferida "¿y bien?" + "un momento" (progressive) | Alto | Gratis | Media | Hilos y sesión; probar con Alexa real |
| 2 | Memoria a largo plazo (`recordar`/`olvidar_dato` → `memoria.json`, inyectada en el prompt) | Alto | Gratis | Baja | Que guarde basura: limitar a hechos explícitos |
| 3 | Búsqueda con respuesta: Wikipedia REST + DuckDuckGo (lib `ddgs`) → el LLM resume | Alto | Gratis, sin clave | Baja | `ddgs` es scraping no oficial y puede romperse; Wikipedia es estable |
| 4 | Modos/rutinas ("modo trabajo" abre apps, webs y volumen) en `config` o `modos.json` | Alto | Gratis | Baja | Ninguno |
| 5 | Noticias (Google News RSS en español + `feedparser`) | Alto | Gratis, sin clave | Baja | Formato RSS sin documentar oficialmente |
| 6 | Archivos: abrir carpeta conocida y buscar archivo por nombre (índice de Usuario; opcional `es.exe` de Everything) | Alto | Gratis | Baja-media | Búsquedas lentas sin índice; limitar a carpetas del usuario |
| 7 | Ventanas: minimizar/maximizar/enfocar/cambiar (`pygetwindow`/`pywinauto`), mostrar escritorio (Win+D) | Medio-alto | Gratis | Baja | Nombres de ventana ambiguos |
| 8 | "¿Qué hay en mi pantalla?": captura → Gemini con visión (plan gratis) → resumen hablado | Alto | Gratis (clave Gemini ya disponible) | Media | Privacidad: la imagen sale a Google; latencia, usar el patrón #1 |
| 9 | Dictado/redacción a Word: el LLM redacta, se crea `.docx` (`python-docx`) y se abre | Alto | Gratis | Baja | Textos largos: usar el patrón #1 |
| 10 | Portapapeles: leer, resumir o traducir lo copiado; copiar texto (`pyperclip`) | Medio | Gratis | Baja | Datos sensibles en el portapapeles |
| 11 | Moneda: open.er-api.com (sin clave, más de 160 monedas, diario) | Medio | Gratis | Baja | Tasa diaria, no en tiempo real. Frankfurter (BCE) no trae muchas monedas latinoamericanas |
| 12 | Calculadora/unidades exactas (evaluador seguro; el LLM suele fallar en aritmética) | Medio | Gratis | Baja | Usar un parser seguro, nunca `eval` |
| 13 | TTS en el PC (respuestas largas por altavoces del PC: SAPI/`pyttsx3`, o `edge-tts`) | Medio | Gratis | Baja | `edge-tts` es no oficial; SAPI suena peor pero es estable |
| 14 | Recordatorios en el propio Echo (Reminders API de Alexa) | Medio | Gratis; permiso del usuario en la app Alexa | Media | Se crea solo dentro de la sesión; a confirmar en modo desarrollo |
| 15 | Brillo de pantalla, modo noche y vaciar papelera (`screen-brightness-control`, PowerShell) | Medio | Gratis | Baja | Monitores externos sin DDC/CI |
| 16 | WhatsApp: abrir chat con texto (`whatsapp://send?phone=…&text=…`) y Enter | Medio | Gratis | Media | Enviar a quien no toca: confirmar siempre en voz antes de enviar |
| 17 | Enchufes/luces desde el PC en local (`python-kasa` TP-Link, `tinytuya` Tuya) | Medio | Gratis si ya tiene esos aparatos | Media | Tuya exige sacar la clave local una vez; depende de la marca |
| 18 | Google Calendar solo lectura por URL iCal secreta (sin OAuth) | Medio | Gratis | Baja | URL secreta = acceso total de lectura; guardarla en `.env` |
| 19 | Gmail / Calendar con escritura (OAuth) | Medio | Gratis, pero app OAuth en "Testing" → el token caduca a los ~7 días | Alta | Re-login semanal o publicar la app; los scopes de Gmail son restringidos |
| 20 | Spotify real (Web API) | Bajo | Controlar la reproducción exige **Premium**; el modo desarrollo tiene un tope de pocos usuarios | Media | De pago. Ya cubierto gratis con URI + teclas multimedia |
| 21 | Disparar rutinas de Alexa / domótica de Alexa (Voice Monkey) | Bajo-medio | Plan gratis sin tarjeta (límites sin detallar) | Media | Servicio de terceros; una Custom Skill no puede controlar dispositivos de Alexa por sí misma |
| 22 | Búsqueda nativa del LLM (Groq `browser_search` / grounding de Gemini) | Medio | Groq cobra unos 5 $/1000 búsquedas; Gemini 3 trae unas 5000/mes gratis, sin confirmar para el plan gratis | Baja | Puede costar dinero: preferir la #3 |

## Notas por idea

1. **Diferida**: es la única forma de hacer tareas lentas sin que Alexa corte. La progressive response es solo cosmética dentro de los 8 s.
2. **Memoria**: guarda frases como "mi ciudad es…", "prefiero Spotify". Es lo que más hace que se sienta como Jarvis.
3. **Búsqueda**: Wikipedia `/{lang}.wikipedia.org/api/rest_v1/page/summary/{título}` para definiciones; `ddgs` para la actualidad. Requiere enviar un User-Agent.
4. **Modos**: un dict `{"trabajo": [...acciones]}` que reutiliza `abrir_programa` y `abrir_web`.
5. **Noticias**: `https://news.google.com/rss?hl=es-419&gl=XX&ceid=XX:es-419` y `/rss/search?q=tema`. Leer 3 titulares.
6. **Archivos**: `os.startfile` sobre Documentos, Descargas o Escritorio; búsqueda por nombre con `rglob` limitada en tiempo.
7. **Ventanas**: complementa abrir/cerrar programa.
8. **Pantalla**: ya existe la captura; solo falta mandarla a Gemini (acepta imagen en el plan gratis).
9. **Word**: responde a "escríbeme una carta para…". Mejor `python-docx` que COM, porque no necesita que Office esté abierto.
10. **Portapapeles**: "tradúceme lo que copié" es muy útil y trivial de hacer.
11-12. **Moneda/cálculo**: dan exactitud; el LLM solo decide la llamada.
13. **TTS PC**: también sirve para que los avisos de recordatorios hablen, no solo se muestren.
14. **Reminders Echo**: el aviso suena en el Echo aunque el PC esté apagado. Necesita activar el permiso en el manifiesto y que el usuario lo acepte.
16. **WhatsApp**: alto riesgo social; siempre confirmar destinatario y texto.
17. **Domótica**: la skill no puede tocar lo que maneja Alexa. La vía gratis es controlar el aparato en local desde el PC.
19-20. Solo si el usuario lo pide: tienen fricción (OAuth semanal) o cuestan dinero (Premium).

## Fuentes
- Progressive Response API: https://developer.amazon.com/en-US/docs/alexa/custom-skills/progressive-response-api-reference.html
- Patrón async en alexa-chatgpt: https://github.com/jackmcguire1/alexa-chatgpt · Claude por Alexa: https://dev.to/_juliantellez/talking-to-claude-code-through-an-alexa-1k71
- Límite de 8000 caracteres de outputSpeech: https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/36557053/alexa-skill-ssml-max-length
- Reminders API de Alexa: https://www.developer.amazon.com/en-US/docs/alexa/smapi/alexa-reminders-overview.html · Proactive Events: https://developer.amazon.com/en-US/docs/alexa/smapi/proactive-events-api.html
- Spotify y Premium: https://www.activepieces.com/blog/spotify-web-api-free-access-modes-scopes-limits.md
- Groq browser_search: https://console.groq.com/docs/tool-use/built-in-tools/browser-search · precios de Groq: https://www.usagepricing.com/blueprint/activity/groq-2026-01-22-built-in-tools-pricing
- Grounding de Gemini: https://discuss.ai.google.dev/t/grounding-free-quota-clarifying-2026-rules-for-gemini-2-5-flash-paid-tier-1/144593
- OAuth en Testing con token de 7 días: https://discuss.google.dev/t/can-a-personal-use-gmail-api-app-be-moved-to-production-without-public-website-urls/406686
- Monedas: https://www.exchangerate-api.com/docs/free · https://frankfurter.app/docs
- Google News RSS: https://newscatcherapi.com/blog/google-news-rss-search-parameters-the-missing-documentaiton
- DuckDuckGo: https://apiserpent.com/blog/free-duckduckgo-api
- Voice Monkey: https://voicemonkey.io/ · tinytuya: https://pypi.org/project/tinytuya
