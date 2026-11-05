# Pendientes

## 1. Convertir Jarvis en aplicación (en vez de .bat)
- Empaquetar con **PyInstaller** (`pyinstaller --noconsole --icon jarvis.ico --name Jarvis lanzador.py`) un `lanzador.py` que arranque servidor y ngrok sin ventanas negras.
- Icono en la **bandeja del sistema** con `pystray` (Abrir panel, Pausar, Ver registro, Salir).
- Primer arranque con una ventana de configuración (claves, Skill ID, dominio ngrok) que escriba `.env`, en vez de editarlo en el Bloc de notas.
- Instalador gratis con **Inno Setup**: acceso directo en el escritorio, opción "Iniciar con Windows" y desinstalador. Sustituye a `iniciar.bat` y `activar_inicio_automatico.bat`.
- Publicar el .exe en *Releases* de GitHub con una Action en windows-latest.

## 2. Trabajo empezado (rama `trabajo-en-curso` en GitHub, sin terminar ni probar)
- **Memoria sin límite** que aprende sola al estilo ChatGPT: datos ilimitados, se envían al LLM solo los relevantes, extracción automática y actualización de datos contradichos.
- **Ventanas**: poner una app a la izquierda/derecha, revisión de foco y teclado, pruebas reales en Windows.
- **Modo acompañante**: vigilar la pantalla con un objetivo ("aconséjame en el juego", "enséñame este código"), sin repetirse y callando si no hay nada útil.

## 3. Falta validar en real
- Lista de primera prueba en `docs/AUDITORIA.md` (Echo, consola Alexa, volumen, clics, panel, Word, Voice Monkey, Google).
- Medir velocidad real con tus claves: `scripts/medir_latencia.py`.
- Comprobar que la prueba de Windows en GitHub Actions pasa en verde.

## 4. Otros
- Plan de mejoras por cada punto débil de la nota (interactividad, UX, diseño, fluidez, calidad): `docs/MEJORAS.md`.
- Configurar la skill en la consola de Alexa (o instalar Claude in Chrome para que Claude lo haga).
- Ideas para después en `docs/IDEAS_2.md` (dictado continuo, imágenes gratis, etc.).
