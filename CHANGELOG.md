# Cambios

## 1.3.0 — 05/11/2026

- Cuota gratis para todo el día: segundo modelo de Groq (`gpt-oss-20b`, con su propia cuota) antes de Gemini;
  tras un 429 se salta ese modelo el tiempo que indica `retry-after` (máx. 1 h) en vez de reintentar en cada
  petición; historial enviado limitado a ~3.000 caracteres. Con la caché de Groq, una conversación gasta
  ~800 tokens de cuota en vez de ~7.500 (1.1.0).
- Respuestas largas: como mucho ~55 palabras (~20 s) por turno, cortando al final de una frase, y "¿Sigo?";
  "sí"/"sigue" dice el resto y "no" u otra pregunta lo descarta. El prompt pide no pasar de 55 palabras.
- Memoria conectada: al terminar la sesión aprende de ella en segundo plano; herramientas `que_sabes_de_mi`,
  `olvidar_todo` (solo con la frase exacta del usuario) y `recordar` con categoría.
- Leer documentos y webs (`leer_documento`) y correos de Gmail (`leer_correos`), con el freno de seguridad
  de lecturas; formas de hablar (profesor, traductor, xara...) al final del contexto y frases en inglés con
  su voz (`<lang>`); al salir vuelve a hablar normal.
- Resumen del día ("buenos días", "mi resumen", sin LLM), tareas programadas, portapapeles y cálculo exacto
  conectados como herramientas (71 en total); programar y borrar tareas frenados tras una lectura.
- Alexa: ejemplos "sigue", "continúa", frases de 23 y 30 palabras (Alexa recorta el comodín a la longitud
  de lo que conoce) y "léeme el contrato", "tengo correos nuevos", "modo traductor", "modo xara".

## 1.2.0 — 05/11/2026

- Velocidad: las órdenes frecuentes (multimedia, volumen, "pon X", abrir/cerrar, pantalla completa,
  adelantar, clic, scroll, mouse, apagar, hora y fecha) se resuelven con reglas locales sin IA (`rapido.py`),
  pasando por la misma ejecución y freno de seguridad; ante cualquier duda decide la IA.
- Una orden simple que la IA resuelve solo con acciones se responde con el texto de la acción, sin segunda
  llamada (la mitad de tiempo y tokens).
- `gpt-oss` con `reasoning_effort="low"` (~1,1 s hasta la primera palabra en vez de varios) y `max_tokens`.
- Prompt fijo al principio y hora/memoria al final del último mensaje: aprovecha la caché de Groq, que
  responde antes y no cuenta esos tokens en el límite por minuto.
- Medición: tiempo de cada llamada al LLM (con tokens en caché), de cada acción y total en la consola y,
  en pequeño, en el HUD; `scripts/medir_latencia.py` da mediana y p90 con tus claves.

## 1.1.0 — 05/11/2026

- Mouse por voz: mover (dirección o posición como "centro" o "esquina superior derecha"), clic, doble clic,
  clic derecho y medio, scroll vertical y horizontal (muescas reales de Windows) y "haz clic en Aceptar":
  Gemini localiza el elemento en una captura (caja `box_2d` normalizada 0–1000 en JSON) y el clic cae bien
  con cualquier escalado DPI. El HUD se esconde antes de hacer clic o desplazar para no tapar ni recibirlo.
- Seguridad: tras leer internet, la pantalla o las notas no hace clic en la misma petición; el cerebro
  profundo no usa el mouse.
- `vision.mirar_pantalla` reutilizable (captura + Gemini) para describir la pantalla y hacer clic.

## 1.0.0 — 05/11/2026

Primera versión estable tras la auditoría completa (detalle en `docs/AUDITORIA.md`).

- Alexa: respuestas largas recortadas bajo el límite de 8.000 caracteres de SSML; modelo de interacción con
  146 ejemplos de 1 a 18 palabras, Fallback poco sensible y frases como "cancela el apagado" o
  "para la música" fuera de los intents integrados.
- Seguridad: tras leer internet, la pantalla o las notas, ningún cerebro escribe, pulsa teclas, cierra,
  apaga ni cambia la memoria en la misma petición.
- Windows: volumen exacto desde cualquier hilo (COM), carpetas reales aunque OneDrive las mueva (registro),
  capturas en la carpeta Imágenes real, `dictar` ignora el archivo de bloqueo de Word, el teclado no falla
  con el ratón en una esquina, avisos de PowerShell sin problemas de comillas, la consola de Windows
  Terminal protegida, `iniciar.bat` comprueba Python 3.12+.
- Robustez: agenda y memoria seguras entre hilos; un evento, `memoria.json`, `persona.md`, `rutinas.json`
  o `echo_uso.json` mal escritos ya no paran avisos ni conversaciones; la vigilancia se apaga sola si falla.
- Pruebas en Windows real con GitHub Actions (Python 3.12 y 3.14), con arranque del servidor.
