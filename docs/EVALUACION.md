# Autoevaluación de Jarvis 1.3.0 (05/11/2026)

Nota honesta, antes de la primera prueba real en tu PC y tu Echo. Las pruebas automáticas no cuentan como "funciona": solo dicen que el código hace lo que se espera en un simulador.

| Criterio | Nota | Qué está bien | Qué está mal |
|---|---|---|---|
| Funciones (amplitud) | 9 | 71 acciones: música, volumen, programas, mouse, teclado, Word, web, agenda local y de Google, correo (solo leer), tareas programadas, leer PDF/Word/webs, cálculo, unidades, portapapeles, notas, modos (profesor, entrenador, XARA…), resumen del día | No envía correos; no arrastra con el mouse; ventanas a la derecha/izquierda y modo acompañante están a medias en la rama `trabajo-en-curso` |
| Funciona de verdad (probado en real) | 3 | GitHub arranca el servidor en un Windows real y pasan las pruebas de Windows | Nadie lo ha usado aún con tu Echo ni en tu PC; la skill de Alexa no está configurada; es lo que más baja la nota |
| Velocidad | 6 | ~30 órdenes comunes (pausa, volumen, abre Word, minimiza…) van sin IA en ~1 ms; con IA es una sola llamada con razonamiento bajo y caché | Sin medir en real: Alexa + ngrok + IA pueden sumar 2–4 s; si tarda más de 6,5 s hay que decir "y bien" |
| Memoria y aprendizaje | 7 | Perfil por categorías, aprende costumbres, resume cada conversación sola, "qué sabes de mí", borrado con confirmación | Solo entran ~1.500 caracteres de memoria por respuesta; la memoria sin límite está a medias |
| Estabilidad | 6 | Auditoría con 18 fallos corregidos; archivos rotos no lo tumban; respaldo Groq → Groq 20b → Gemini | Muchos hilos a la vez sin una prueba real de horas |
| Calidad de código | 7 | Módulos pequeños, nombres claros, 904 pruebas, sin código muerto | 71 herramientas son mucho para un LLM gratis; hubo muchos agentes escribiendo en paralelo |
| Seguridad | 6 | Firma de Alexa verificada, panel solo local, freno contra órdenes ocultas en webs/correos, apagado con 1 minuto para cancelar | Cualquiera que hable con tu Echo controla tu PC; las capturas de pantalla van a Google |
| Naturalidad | 6 | Personalidad editable con tu nombre, interjecciones de Alexa, respuestas cortas con "¿Sigo?", modo XARA | Hay que decir "Alexa, abre mi jarvis"; la voz es la de Alexa; el límite de 8 s obliga al "y bien" |
| Diseño visual (HUD) | 6 | Orbe propio + onda tipo Siri, fondo oscuro, muestra lo que oye y responde | No lo he visto en tu pantalla; se ve como una ventana de Edge, no como una app |
| Fluidez y animaciones | 5 | Orbe y onda animados con CSS, se abre al hablar y se minimiza al terminar | No medido en real; abrir Edge cada vez puede dar un salto; pocas transiciones |
| Interactividad | 3 | Todo por voz | El HUD solo muestra: no tiene botones, no puedes escribirle ni pararlo con clic |
| Instalación | 5 | Guía no técnica, `iniciar.bat`, inicio automático con Windows | ~20 minutos con ngrok y la consola de Amazon; es un .bat, no una app; el PC debe estar encendido |
| Coste | 9 | Todo gratis | Las cuotas gratis limitan cuánto lo puedes usar al día |
| Documentación | 9 | Guía de uso no técnica, README, auditoría, pendientes, registro de avances | — |

**Nota global: 6,2 / 10** (promedio de los 14 criterios; antes 5,5 en la 1.1.0).

**Qué lo subiría más rápido a 8+:**
1. La primera prueba real con tu Echo y tu PC (sube "probado en real", velocidad y estabilidad).
2. Convertirlo en app con icono en la bandeja (instalación, diseño).
3. Botones en el HUD (parar, repetir, escribir) y transiciones suaves (interactividad, fluidez).
4. Terminar la rama `trabajo-en-curso` (memoria sin límite, ventanas, modo acompañante).

Todo esto está en PENDIENTES.md.
