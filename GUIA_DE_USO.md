# Guía de uso de Jarvis

Jarvis convierte tu Echo Dot en un asistente que conversa contigo y controla tu computadora. Esta guía no es técnica: sigue los pasos en orden y no hace falta saber programar.

---

## Antes de empezar: qué necesitas

- Tu computadora con **Windows 11**, encendida y con internet mientras uses Jarvis.
- Tu **Echo Dot**, con la misma cuenta de Amazon que vas a usar en el paso 5.
- Unos **30 minutos** para instalarlo la primera vez. Después solo es un doble clic.
- Todo es **gratis**: no pongas tarjeta en ningún sitio.

> **Importante:** si alguna vez pegaste una clave en un chat o en un mensaje, bórrala y crea una nueva. Las claves son como contraseñas.

---

## Parte 1. Instalación (solo la primera vez)

### Paso 1. Instalar Python

Python es el programa que hace funcionar a Jarvis.

1. Entra en **python.org/downloads** y pulsa el botón amarillo de descarga.
2. Abre el archivo descargado.
3. **Muy importante:** antes de pulsar *Install Now*, marca la casilla de abajo que dice **"Add python.exe to PATH"**.
4. Pulsa *Install Now* y espera a que termine.

### Paso 2. Descargar Jarvis

1. Descarga el archivo **jarvis.zip**.
2. Haz clic derecho sobre él → **Extraer todo**.
3. Mueve la carpeta `jarvis` a un lugar fácil, por ejemplo `C:\jarvis`.

### Paso 3. Conseguir las claves de inteligencia artificial

Son como "llaves" para que Jarvis pueda pensar. Necesitas al menos una; con las dos funciona mejor, porque si una se cansa usa la otra.

- **Groq** (la más rápida):
  1. Entra en **console.groq.com/keys** e inicia sesión (puedes usar tu cuenta de Google).
  2. Pulsa **Create API Key**, ponle de nombre "jarvis" y copia la clave. Guárdala en un lugar seguro.
- **Gemini** (respaldo, y la que deja a Jarvis "ver" tu pantalla):
  1. Entra en **aistudio.google.com/apikey**.
  2. Pulsa **Create API key** y copia la clave.

### Paso 4. Instalar ngrok (el "puente" entre Alexa y tu PC)

1. Crea una cuenta gratis en **dashboard.ngrok.com/signup**.
2. Pulsa la tecla Windows, escribe `cmd` y abre **Símbolo del sistema**.
3. Escribe esto y pulsa Enter: `winget install ngrok.ngrok`
4. En la página de ngrok, abre **Your Authtoken**, copia el comando que aparece, pégalo en la ventana negra y pulsa Enter.
5. En la página de ngrok, abre **Domains** y copia tu dirección (termina en `.ngrok-free.app` o `.ngrok-free.dev`). Esa dirección es tuya y no cambia.

### Paso 5. Crear tu skill en Alexa

Una "skill" es como una app para Alexa. Esta será tu Jarvis.

1. Entra en **developer.amazon.com/alexa/console/ask** con **la misma cuenta de Amazon de tu Echo**.
2. Pulsa **Create Skill**.
3. Nombre: `Jarvis`. Idioma: **el mismo que tiene tu Echo** en la app Alexa (por ejemplo *Spanish (MX)* o *Spanish (US)*).
4. Si pregunta el tipo, elige **Other** → **Custom** → **Provision your own** → **Start from Scratch**. Crea la skill.
5. En el menú de la izquierda: **Interaction Model** → **JSON Editor**.
   - Borra todo lo que haya.
   - Abre el archivo `jarvis\skill\modelo_es.json` con el Bloc de notas, copia todo y pégalo ahí.
   - Pulsa **Save** y luego **Build skill**. Espera a que diga que terminó.
6. En el menú de la izquierda: **Endpoint**.
   - Elige **HTTPS**.
   - En *Default Region* escribe `https://` + tu dirección de ngrok + `/alexa`. Ejemplo: `https://jarvis-feliz.ngrok-free.app/alexa`
   - En el certificado elige la opción que dice **"...wildcard certificate from a certificate authority"**.
   - Pulsa **Save**.
7. Copia el **Skill ID** (empieza por `amzn1.ask.skill.`). Aparece en esa misma página o en la lista de skills con *Copy Skill ID*.
8. Abre la pestaña **Test** de arriba y cambia **Off** por **Development**.

### Paso 6. Poner tus claves en Jarvis

1. Abre la carpeta `jarvis` y haz doble clic en **`iniciar.bat`**.
2. La primera vez se abrirá un Bloc de notas. Rellena estas líneas (sin espacios alrededor del `=`):
   ```
   GROQ_API_KEY=pega_aquí_tu_clave_de_groq
   GEMINI_API_KEY=pega_aquí_tu_clave_de_gemini
   ALEXA_SKILL_ID=pega_aquí_tu_skill_id
   NGROK_DOMINIO=tu-direccion.ngrok-free.app
   CIUDAD=Lima
   ```
   La dirección de ngrok va **sin** `https://`. En `CIUDAD` pon la tuya, para el clima.
3. Guarda (Ctrl + G o Ctrl + S) y cierra el Bloc de notas.

### Paso 7. Encender Jarvis

1. Vuelve a hacer doble clic en **`iniciar.bat`**.
2. La primera vez tarda unos minutos instalando cosas. Es normal.
3. La ventana negra se cierra sola y aparece un **icono redondo azul junto al reloj** de Windows (si no lo ves, pulsa la flechita ^ al lado del reloj). Eso significa que Jarvis está encendido.
4. Clic derecho en ese icono: **Abrir panel**, **Ver registro** (los mensajes de Jarvis, por si algo falla), **Editar claves (.env)** y **Salir** (apaga Jarvis).

¡Listo! A partir de ahora, cada vez que quieras usar Jarvis solo haces doble clic en `iniciar.bat`.

---

## Parte 2. Cómo hablar con Jarvis

### Abrirlo

Di: **"Alexa, abre mi jarvis"**.

Jarvis te saludará y se quedará escuchando. Ya puedes hablarle normal, sin repetir "Alexa", mientras la conversación siga abierta (la luz azul del Echo encendida).

Para una orden rápida sin abrir conversación: **"Alexa, pide a mi jarvis que pause la música"**.

Para terminar: **"adiós"**, **"para"** o **"cancela"**.

### Qué le puedes pedir

**Conversar y aprender**
- "¿Qué opinas de…?", "explícame cómo funciona…", "estoy programando, enséñame qué es una función".
- "Modo profesor", "modo entrenador", "modo traductor", "modo xara" (cambia su forma de hablar). "Modo normal" para volver.

**Preguntas de todo tipo**
- "¿Cuánto es 15 por ciento de 230?" (calcula exacto).
- "¿Cuántas millas son 10 kilómetros?"
- "¿A qué hora juega el Barcelona?", "busca ofertas de laptops en internet".
- "¿Qué noticias hay?", "¿qué clima hace?", "¿cuántos soles son 50 dólares?"
- "Buenos días" o "dame mi resumen del día" (clima, citas y noticias).

**Música y videos**
- "Pon música de Bad Bunny", "reproduce lofi para estudiar", "abre YouTube".
- "Pausa", "sigue", "siguiente canción", "pantalla completa", "adelanta 30 segundos".
- "Sube el volumen", "baja el volumen", "volumen al 30", "silencia".

**Programas y ventanas**
- "Abre Word", "abre Excel", "abre Chrome", "cierra Spotify".
- "Minimiza todo", "maximiza la ventana", "cierra esta ventana".
- "Abre la carpeta de descargas", "busca el archivo contrato".

**Escribir y teclado**
- "Escribe: hola, ya voy en camino" (escribe donde esté el cursor).
- "Crea un documento de Word con una carta de renuncia" y luego "dicta: atentamente, Luis".
- "Pulsa control más zeta".
- "Traduce lo que copié", "resume lo que copié".

**Mouse**
- "Mueve el mouse a la derecha", "haz clic", "doble clic", "baja la página".
- "Haz clic en Aceptar" (mira tu pantalla para encontrar el botón).

**Pantalla**
- "¿Qué hay en mi pantalla?", "¿qué dice este error?".
- "Vigila mi pantalla 10 minutos" (comenta lo que pasa en el panel de la pantalla).

**Documentos y correo**
- "Léeme el PDF del contrato", "resume esta página web".
- "¿Tengo correos nuevos?" (solo si activaste Google, ver más abajo).

**Agenda y recordatorios**
- "Agenda dentista mañana a las 3", "¿qué tengo hoy?", "borra la cita del dentista".
- "Pon un temporizador de 10 minutos para la pizza".
- "Cada día a las 7 dame mi resumen", "todos los lunes recuérdame sacar la basura".

**Encargos largos (segundo cerebro)**
- "Investiga los mejores celulares de 2026 y hazme un resumen en Word". Jarvis te avisa cuando termina.
- "¿Cómo va lo que te pedí?"
- "Guarda una nota: idea para el negocio…", "busca en mis notas lo del viaje".

**Tu PC**
- "Apaga la computadora" (tienes 1 minuto para decir "cancela el apagado").
- "Reinicia", "suspende", "bloquea", "toma una captura de pantalla", "¿cómo está mi PC?".

**Rutinas**
- "Activa el modo trabajo", "modo relax", "¿qué modos hay?".

### Cuando tarda: "y bien"

Si le pides algo largo, Jarvis puede decir **"Sigo con eso, dime 'y bien' en unos segundos"**. Espera un momento y di **"y bien"**: te dará la respuesta. Es porque Alexa corta si alguien tarda más de 8 segundos.

### Cuando la respuesta es larga: "¿Sigo?"

Jarvis responde corto. Si tiene más que decir, pregunta **"¿Sigo?"**. Di **"sí"** o **"sigue"** para oír el resto.

---

## Parte 3. Lo que Jarvis recuerda de ti

- Recuerda tu nombre, gustos, personas importantes y cosas que le cuentes, aunque apagues la PC.
- Aprende de tu uso: qué música pones, qué programas abres, a qué volumen escuchas.
- Al terminar cada conversación guarda un resumen corto.
- Puedes decir: **"Recuerda que mi hermano se llama Pedro"**, **"¿qué sabes de mí?"**, **"olvida que vivo en Lima"**.
- Para borrar todo: **"Sí, bórralo todo"**.

Todo se guarda **solo en tu PC**, en la carpeta de Jarvis. No se sube a ningún lado.

---

## Parte 4. El panel en pantalla

Cuando hablas con Alexa aparece en tu pantalla una ventana con un círculo animado:
- Muestra lo que dijiste, lo que respondió y las acciones que hizo.
- Se esconde sola unos segundos después de terminar. Al encender Jarvis aparece un momento y se minimiza: así luego sale al instante.
- **Puedes escribirle** en la caja de abajo ("Escríbele a Jarvis…") y pulsar Enter, sin hablar con Alexa. La respuesta sale en el panel.
- **Botones**: ⏯ Pausa (música o vídeo), ⏻ Anular apagado, 👁 No vigilar (deja de comentar tu pantalla) y ▾ Ocultar.
- Si pides apagar o reiniciar, sale una cuenta atrás naranja con botón **Cancelar**.
- El reloj 🕘 de arriba muestra la conversación de hoy (las últimas 20 respuestas), con botón para copiar cada una.
- La primera vez muestra frases de ejemplo: púlsalas para probar.
- Si Groq o Gemini fallan, el panel te dice por qué en una línea (cuota agotada, clave mala o sin internet).
- Si no lo quieres, abre el archivo `.env` y pon `HUD_ACTIVO=no`.

---

## Parte 5. Extras opcionales

**Que el Echo hable solo (avisos y recordatorios):** con la app gratuita **Voice Monkey** (200 avisos al mes). Los pasos están en el README, sección "Que el Echo hable solo".

**Gmail y Google Calendar:** gratis con un pequeño script de Google. Pasos en el README, sección "Google". Jarvis solo **lee** tus correos, nunca envía.

**Cambiar su personalidad:** copia el archivo `persona.ejemplo.md`, llámalo `persona.md` y escribe cómo quieres que hable. Se aplica al instante.

---

## Parte 6. Si algo no funciona

| Qué pasa | Qué hacer |
|---|---|
| Alexa dice que la skill no responde | Revisa que el icono de Jarvis esté junto al reloj y que la PC tenga internet. |
| Alexa no encuentra "mi jarvis" | En la consola de Alexa, pestaña Test, debe estar en **Development**. El idioma de la skill debe ser el mismo que el de tu Echo. |
| Sale un aviso "Falta ALEXA_SKILL_ID" o "Falta GROQ_API_KEY" | Jarvis te abre `.env`: revisa que copiaste bien las claves, sin espacios, guarda y vuelve a abrir `iniciar.bat`. |
| Responde "No pude pensar ahora mismo" | Se acabó la cuota gratis del momento. Espera un minuto. Si pasa mucho, pon también la clave de Gemini. |
| No sube el volumen o no hace clic | Asegúrate de no tener la PC bloqueada. Mira el error en el registro (clic derecho en el icono, **Ver registro**). |
| Te entiende mal una frase larga | Dila más despacio o en dos partes. |

Si nada funciona, abre el registro (clic derecho en el icono, **Ver registro**), copia las últimas líneas y envíalas.

---

## Bueno saber

- **La PC debe estar encendida** y con las dos ventanas abiertas para que funcione.
- Tienes que empezar con **"Alexa, abre mi jarvis"**: Alexa no deja reemplazar su cerebro por completo.
- **Cualquiera que hable con tu Echo** puede dar órdenes a tu PC mientras Jarvis esté encendido.
- Cuando le pides ver la pantalla, la imagen se envía a Google para analizarla.
- Las cuotas gratis tienen límites por minuto y por día. Para uso personal normal alcanzan.

---

## Que Jarvis arranque solo al encender el PC

1. En la carpeta `jarvis`, haz doble clic en **`activar_inicio_automatico.bat`**.
2. Desde ahora, cada vez que enciendas el PC, Jarvis se abrirá solo (minimizado).
3. Para quitarlo: doble clic en **`quitar_inicio_automatico.bat`**.

## Lo que Jarvis ya sabe de ti

El archivo `memoria.json` (incluido en el zip, no en GitHub) ya trae tu nombre, que programas, juegas, prefieres lo gratis y respuestas cortas y directas. Lo que no era seguro (si eres peruano, si sigues al Barcelona) está marcado "sin confirmar": corrígelo diciéndole "recuerda que…" u "olvida que…".
