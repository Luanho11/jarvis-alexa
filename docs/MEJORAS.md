# Plan de mejoras tras la autoevaluación 1.3.0 (6,2/10, ahora 6,5)

Cada mejora sale de un punto débil de `docs/EVALUACION.md`. Prioridad: **A** = sube más la nota con menos trabajo, **B** = importante, **C** = después. Lo marcado con ✅ ya está hecho y subido.

## 1. Interactividad (3 → 8)
El HUD solo muestra; no se puede tocar.
- ✅ **A** Barra de botones en el HUD: ⏸ Parar (corta lo que está diciendo/haciendo), 🔁 Repetir, ✕ Cancelar acción pendiente (apagado, programada), 🔇 Silenciar vigilancia. Nuevo `POST /hud/orden` en `panel.py`, solo local, igual que `/hud/eventos`.
- ✅ **A** Caja de texto "Escríbele a Jarvis" en el HUD: misma ruta que la voz (`rapido.py` → `cerebro.py`), útil cuando no quieres hablar o el Echo no entendió.
- ✅ **B** Historial desplegable de la conversación de hoy (las últimas 20 líneas), con botón copiar en cada respuesta.
- **B** Tarjetas de acción clicables: si abrió un vídeo, archivo o web, la tarjeta lo abre otra vez; si creó un recordatorio, botón "borrar".
- **C** Atajos de teclado globales: `Ctrl+Alt+J` muestra/oculta el HUD, `Esc` lo minimiza.

## 2. Intuitividad y UX (sin nota propia, afecta a naturalidad e instalación)
- ✅ **A** Pantalla de bienvenida la primera vez: 5 frases de ejemplo ("pon música de…", "qué hay en mi pantalla", "recuérdame…") que se pueden pulsar para probar.
- ✅ **A** Mensajes de error en lenguaje normal en el HUD y en la voz: hoy "falta la clave de Groq" solo sale en la consola negra. Mostrar qué pasó y qué hacer en una línea.
- **A** Indicador claro de estado: escuchando / pensando / haciendo / hablando, con color distinto y texto; y aviso visible cuando está usando el respaldo (Gemini) porque Groq se agotó.
- **B** Confirmaciones visibles para lo peligroso (apagar, cerrar programa, clic): tarjeta con cuenta atrás y botón Cancelar, además de la voz.
- **B** "¿Qué puedes hacer?" responde con 6 categorías cortas en vez de una lista larga, y el HUD muestra la lista completa agrupada.
- **C** Sonido corto (opcional) al empezar y terminar una acción en el PC.

## 3. Diseño visual / UI (6 → 8)
- **A** Que deje de parecer una ventana de Edge: ventana sin bordes, esquinas redondeadas, fondo translúcido (efecto Mica/acrílico de Windows 11) cuando sea app (ver punto 7).
- **A** Sistema de diseño en `hud.css`: variables para colores, tamaños y espacios en un solo sitio; una sola tipografía (Segoe UI Variable, la de Windows 11); 3 tamaños de texto, no más.
- **B** Modo compacto: una cápsula pequeña en una esquina (orbe + última frase) en vez de la ventana entera, ampliable con clic.
- **B** Tema claro/oscuro según Windows, y color de acento elegible (azul Jarvis, rojo XARA…).
- **C** Revisar contraste y tamaño mínimo de texto (accesibilidad AA).

## 4. Fluidez y animaciones (5 → 8)
- ✅ **A** No abrir Edge en cada orden: abrirlo una vez al arrancar y solo mostrar/ocultar la ventana. Quita el salto y el retraso.
- ✅ **A** Transiciones de entrada y salida (aparecer con fundido + escala 0,96→1 en 200 ms; ocultar en 150 ms) y respetar "reducir movimiento" de Windows (`prefers-reduced-motion`).
- ✅ **B** Texto de la respuesta que aparece al ritmo de la voz en vez de entero de golpe.
- **B** La onda reacciona al estado (plana en espera, viva al hablar) con transición suave, sin saltos de amplitud.
- **C** Medir FPS y CPU del HUD en tu PC; objetivo 60 fps y <3 % de CPU en espera (pausar animaciones cuando está oculto).

## 5. Calidad, simpleza y limpieza del código (7 → 9)
- **A** Menos herramientas para la IA: agrupar las 71 en ~35 (por ejemplo `ventana(accion=minimizar|maximizar|cerrar)`, `mouse(accion=…)`, `memoria(accion=…)`). Menos tokens, menos errores de la IA, Groq dura más.
- **A** `herramientas.py` (319 líneas) partido por área (`herramientas/pc.py`, `herramientas/info.py`…) con el registro en un solo sitio.
- **B** Un único archivo de ajustes (`ajustes.json`) en vez de varios sueltos (`rutinas.json`, `programadas.json`, `echo_uso.json`…), con valores por defecto en código.
- **B** Registro (log) ordenado en `logs/jarvis.log` con rotación, en vez de solo la consola; el HUD puede enseñar los últimos errores.
- **B** Revisar con `ruff` y tipos con `mypy` en la CI; quitar duplicados que dejaron los agentes en paralelo.
- **C** Pruebas de extremo a extremo: petición de Alexa simulada → acción en Windows (en GitHub Actions).

## 6. Velocidad (6 → 8)
- **A** Ampliar la ruta rápida sin IA con lo que más usas (sale de `uso.json` tras una semana de uso real).
- **B** Precalentar la conexión con Groq al arrancar y cada 4 minutos (evita el primer arranque lento).
- **B** Mostrar en el HUD el tiempo real de cada respuesta y avisar si pasa de 3 s.

## 7. Instalación (5 → 8)
Ya detallado en `PENDIENTES.md`, punto 1: app con PyInstaller, icono en la bandeja, ventana de configuración, instalador con Inno Setup y descarga desde GitHub Releases.

## 8. Naturalidad (6 → 7)
- **B** Respuestas que varían más (no repetir la misma frase de confirmación dos veces seguidas).
- **B** Que recuerde de qué se hablaba en la última conversación al volver a abrirlo ("seguimos con lo del código de ayer").
- **C** Voz propia en el PC (no en el Echo) con una voz neural gratis de Windows para los avisos del HUD.

## 9. Seguridad (6 → 8)
- **B** Palabra clave opcional para lo peligroso (apagar, cerrar programas, clics): "Jarvis, código azul, apaga".
- **B** Opción para que las capturas de pantalla se analicen solo cuando lo pides, nunca en la vigilancia, y aviso visible en el HUD cada vez que se envía una a Google.

## 10. Probado en real (3 → 8)
Lo que más sube la nota y no depende de código: configurar la skill de Alexa, seguir la lista de primera prueba de `docs/AUDITORIA.md` y anotar lo que falle.

## Orden recomendado
1. Prueba real (punto 10).
2. Interactividad A + fluidez A (HUD con botones, caja de texto, Edge abierto una vez, transiciones).
3. Agrupar herramientas (calidad A).
4. App instalable (punto 7) con el diseño nuevo.
5. El resto, por prioridad.

Estimación tras los pasos 1–4: **~8/10**.
