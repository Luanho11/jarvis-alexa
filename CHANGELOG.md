# Cambios

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
