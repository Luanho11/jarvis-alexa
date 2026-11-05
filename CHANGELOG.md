# Cambios

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
