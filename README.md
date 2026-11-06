# Jarvis para Alexa

Convierte tu Echo Dot en un asistente que conversa con una IA y controla tu PC con Windows 11:
música y YouTube, volumen, programas, apagar el PC, Word, archivos y ventanas, el mouse, búsquedas,
noticias, agenda, recordatorios, memoria, modos y una ventana visual que puede mirar tu pantalla.
Todo con planes gratuitos: no hace falta pagar nada.

Versión 1.1.0 (cambios en `CHANGELOG.md`).

Cómo funciona: Alexa envía lo que dices a un pequeño programa en tu PC (a través de ngrok),
el programa se lo pasa a la IA (Groq o Gemini) y Alexa lee la respuesta.

## 1. Instalar Python

1. Descarga Python 3.12 o superior desde [python.org/downloads](https://www.python.org/downloads/).
2. Al instalar, **marca la casilla "Add python.exe to PATH"** antes de pulsar *Install Now*.

## 2. Descargar el proyecto

Copia la carpeta `jarvis` en tu PC, por ejemplo en `C:\jarvis`.

## 3. Conseguir las claves de IA (gratis)

Funciona con una, pero **pon las dos**: los planes gratis tienen límites por minuto (Groq admite
pocas peticiones seguidas con tantas funciones) y, cuando una se agota o falla, Jarvis pasa solo
a la otra. Además, ver la pantalla solo funciona con Gemini.

- **Groq** (la principal, es la más rápida): entra en [console.groq.com/keys](https://console.groq.com/keys),
  inicia sesión y pulsa *Create API Key*. Copia la clave.
- **Gemini** (respaldo): entra en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
  y pulsa *Create API key*. Copia la clave.

## 4. Instalar ngrok (gratis)

ngrok da a tu PC una dirección de internet fija para que Alexa pueda llegar a él.

1. Crea una cuenta gratis en [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup).
2. Abre *Símbolo del sistema* (tecla Windows, escribe `cmd`) e instala ngrok:
   ```
   winget install ngrok.ngrok
   ```
3. En el dashboard, abre *Your Authtoken*, copia el comando que aparece y pégalo en `cmd`.
   Es parecido a:
   ```
   ngrok config add-authtoken TU_TOKEN
   ```
4. En el dashboard, abre *Domains*. Ahí está tu dominio gratis, que no cambia nunca
   (termina en `.ngrok-free.app` o `.ngrok-free.dev`). Cópialo.

## 5. Crear la skill de Alexa

Usa la **misma cuenta de Amazon** de tu Echo.

1. Entra en [developer.amazon.com/alexa/console/ask](https://developer.amazon.com/alexa/console/ask)
   y pulsa *Create Skill*.
2. Nombre: `Jarvis`. Idioma (*Primary locale*): **el mismo que tiene tu Echo** en la app Alexa
   (*Spanish (MX)*, *Spanish (US)* o *Spanish (ES)*).
3. Si te pide tipo de experiencia, elige *Other*. Modelo: **Custom**. Hosting: **Provision your own**.
   Plantilla: **Start from Scratch**. Crea la skill.
4. En el menú izquierdo abre *Interaction Model* → **JSON Editor**. Borra todo, pega el
   contenido de `skill/modelo_es.json`, pulsa *Save* y luego **Build skill**. Espera a que termine.
5. Abre **Endpoint**, elige *HTTPS* y en *Default Region* escribe:
   ```
   https://TU-DOMINIO/alexa
   ```
   (por ejemplo `https://jarvis-feliz.ngrok-free.app/alexa`).
   En el certificado elige:
   **"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"**.
   Pulsa *Save*.
6. Copia el **Skill ID** (empieza por `amzn1.ask.skill.`). Está arriba en la página de Endpoint
   o en la lista de skills (*Copy Skill ID*).
7. Abre la pestaña **Test** y cambia *Off* por **Development**.

## 6. Configurar y arrancar

1. Dentro de la carpeta `jarvis`, haz doble clic en **`iniciar.bat`**. La primera vez crea
   el archivo `.env` y lo abre en el Bloc de notas.
2. Rellena y guarda:
   ```
   GROQ_API_KEY=tu_clave_de_groq
   GEMINI_API_KEY=tu_clave_de_gemini
   ALEXA_SKILL_ID=amzn1.ask.skill....
   NGROK_DOMINIO=jarvis-feliz.ngrok-free.app
   ```
   (`NGROK_DOMINIO` va sin `https://`).
3. Vuelve a abrir `iniciar.bat`. La primera vez instala lo necesario (unos minutos).
   La ventana negra se cierra sola y queda un icono de Jarvis junto al reloj (clic derecho: Abrir panel,
   Ver registro, Editar claves, Salir). Para depurar con consola: `.venv\Scripts\python servidor.py`.

Para probar sin el Echo: en la pestaña *Test* de la consola escribe `abre mi jarvis`.

## 7. Uso

Di **"Alexa, abre mi jarvis"** y, cuando te salude, habla normal. Sigue escuchando después de
cada respuesta; para terminar di "adiós" o "eso es todo". También vale de una vez:
"Alexa, pide a mi jarvis que ponga música".

Qué puede hacer por ti, en resumen:

| Pídele | Cómo lo hace |
|---|---|
| **Escribir lo que dictas** | "Escribe hola mundo" lo teclea donde esté el cursor (`escribir_texto`); "añade al documento: ..." lo dicta al último Word; "escríbeme en Word una carta..." crea el documento y lo redacta. |
| **Asesorarte** | Conversa y da su opinión ("¿qué portátil me compro?"); para algo largo ("investiga y compárame tres opciones") lo encarga al cerebro profundo y te avisa al terminar. |
| **Buscar en internet** | "Busca quién ganó el partido" te responde hablando (`buscar_informacion`); "búscalo en Google" abre la búsqueda en el navegador. |
| **Manejar el mouse** | Lo mueve, hace clic, doble clic o clic derecho, desplaza la página y hace clic en lo que nombres ("haz clic en Aceptar") mirando la pantalla. |

Ejemplos de lo que puedes decir:

- **Conversación**: "Cuéntame un chiste" · "¿Por qué el cielo es azul?" · "Dame una idea para cenar"
- **Música y YouTube**: "Pon música de Bad Bunny" · "Busca recetas de lentejas en YouTube" ·
  "Pausa" · "Siguiente canción" · "Adelanta 30 segundos" · "Pantalla completa" ·
  "Busca a Shakira en Spotify"
- **Volumen**: "Sube el volumen" · "Pon el volumen al treinta por ciento" · "Silencia el ordenador"
- **Programas**: "Abre Word" · "Abre la calculadora" · "Cierra Chrome" · "Abre google.com"
- **Sistema**: "Apaga la computadora" (te da un minuto: "cancela el apagado") · "Reinicia el PC" ·
  "Suspende" · "Bloquea el PC" · "¿Cómo va la batería?" · "Haz una captura de pantalla"
- **Archivos y ventanas**: "Abre la carpeta de descargas" · "Busca el archivo presupuesto" ·
  "Minimiza todo" · "Pon al frente la ventana de Excel" · "Maximiza la ventana" ·
  "Cierra esta ventana" · "Escribe hola mundo" · "Pulsa control más zeta"
- **Mouse**: "Mueve el mouse a la derecha" · "Pon el ratón en el centro" · "Haz clic" ·
  "Dale doble clic" · "Haz clic derecho" · "Baja la página" · "Sube un poco" ·
  "Haz clic en Aceptar" · "Dale doble clic al archivo presupuesto" · "Haz clic en el buscador".
  Para hacer clic en algo por su nombre mira la pantalla con Gemini (necesita su clave, tarda unos
  segundos). Antes de hacer clic o desplazar, la ventana visual se esconde para no tapar nada.
- **Word**: "Escríbeme en Word una carta para mi casero pidiendo arreglar la ducha" ·
  "Añade al documento: un saludo cordial" (se guarda en Documentos, carpeta Jarvis)
- **Información**: "Busca quién ganó el partido de ayer" · "Dame las noticias" ·
  "Noticias de tecnología" · "¿Qué tiempo hace?" · "¿Cuánto son cien dólares en pesos?"
- **Agenda y avisos**: "Agenda dentista mañana a las tres" · "¿Qué tengo hoy?" ·
  "Borra la cita del dentista" · "Pon un temporizador de diez minutos para la pasta".
  El aviso sale en el PC (globo y voz de Windows) a la hora indicada.
- **Memoria**: "Recuerda que mi equipo es el América" · "Olvida lo de mi equipo"
- **Modos**: "Activa el modo estudio" · "¿Qué modos tengo?". Se definen en `rutinas.json`
  (copia `rutinas.ejemplo.json` y cámbialo a tu gusto).
- **Formas de hablar**: "Modo profesor" · "Modo traductor" · "Modo entrenador" · "Modo normal"
  (ver [Formas de hablar](#formas-de-hablar-como-los-gems)).
- **Leer documentos y webs**: "Léeme el contrato" · "¿Qué dice el último PDF de descargas?" ·
  "Resúmeme el contrato en Word" · "¿De qué trata elpais.com/internacional?" · "Sigue desde la página 4".
  Lee PDF, Word (.docx), .txt, .md y .csv de Documentos, Descargas y Escritorio, y páginas web.
  Si hay varios con ese nombre te pregunta cuál. Un PDF escaneado (fotos de páginas) no tiene
  texto: ábrelo y pídele que mire la pantalla. Por seguridad nunca abre direcciones de tu red local
  ni de tu PC (router, la ventana visual...). "Resúmelo entero" lo encarga al cerebro profundo.
- **Correo** (si configuras [Google](#google-gmail-y-calendar-gratis-opcional)): "¿Tengo correos nuevos?" ·
  "Léeme mis últimos correos". Solo lee: no puede enviar ni borrar.
- **Pantalla**: "¿Qué hay en mi pantalla?" · "¿Qué error sale aquí?" ·
  "Vigila mi pantalla diez minutos" · "Deja de vigilar"
- **Resumen del día**: "Buenos días" · "Mi resumen" · "¿Qué hay hoy?" (fecha, clima, citas, avisos y
  titulares, sin esperar a la IA). Para oírlo cada mañana sin abrir la skill, crea en la app de Alexa una
  rutina (*Más → Rutinas → +*): cuando digas "Alexa, buenos días" (o a una hora), acción *Personalizada*
  con el texto **"pide a mi jarvis mi resumen del día"**.
- **Tareas programadas**: "Avísame todos los días a las 7 de tomar la pastilla" · "Cada lunes a las 9 hazme
  un resumen" · "¿Qué tengo programado?" · "Borra el aviso de la pastilla".
- **Portapapeles**: copia un texto y di "tradúceme lo que copié" o "resume lo que copié"; "cópialo" deja la
  respuesta en el portapapeles. Lo copiado **se envía a la IA** (Groq o Gemini) para entenderlo: no lo uses
  con contraseñas ni datos privados.
- **Cálculos**: "¿Cuánto es el 15 % de 200?" · "Convierte 10 kilómetros a millas" · "350 grados Fahrenheit
  en Celsius". Las cuentas se hacen exactas en tu PC, no de cabeza.

**Respuestas largas ("¿Sigo?")**: Jarvis dice como mucho unas 55 palabras de una vez; si hay más, pregunta
*"¿Sigo?"*. Di "sí" o "sigue" para oír el resto, o pregunta otra cosa.

**Respuestas lentas ("y bien")**: Alexa solo espera unos 8 segundos. Si algo tarda más (buscar
en internet, redactar un Word, mirar la pantalla), Jarvis dice *"Sigo con eso, dime 'y bien' en
unos segundos"*. Di **"y bien"** y te da la respuesta. Si en vez de eso pides otra cosa, te dice
las dos respuestas seguidas.

## Segundo cerebro

- **Encargos largos**: "Investiga los mejores portátiles baratos y hazme un resumen en Word" ·
  "Organiza mi semana" · "Compara precios de freidoras de aire". Jarvis contesta al momento
  *"Me pongo con eso, te aviso cuando termine"* y trabaja en segundo plano (hasta unos 3 minutos,
  dos encargos a la vez) con un modelo de Gemini más listo (`MODELO_PROFUNDO`). Al terminar te
  avisa en la ventana visual y con la voz del PC, y te lo cuenta la próxima vez que le hables.
  Pregunta *"¿cómo va lo que te pedí?"* para saber en qué está. Ese modelo gratis da unas 20 peticiones
  al día (un encargo usa varias); cuando se acaban, sigue solo con el Gemini normal y luego con Groq.
- **Notas**: "Apunta en mis notas que la contraseña del wifi de invitados está en la nevera" ·
  "¿Qué tengo en mis notas sobre el viaje?" · "Léeme la nota de compras". Cada nota es un
  archivo `.md` en la carpeta `notas` (con fecha y etiquetas), así que puedes abrirlas con
  [Obsidian](https://obsidian.md) o cualquier editor; para usar tu bóveda pon su ruta en
  `NOTAS_CARPETA` en `.env`. La búsqueda es por palabras, sin tildes: es instantánea, gratis y
  no sale de tu PC.

## Memoria y aprendizaje

Jarvis te va conociendo, sin pagar nada y sin que tus datos salgan de tu PC (salvo lo que ya viaja
en cada conversación al LLM gratis, Groq o Gemini):

- **Perfil** (`memoria.json`): tu nombre, datos personales, gustos, personas importantes, rutinas y
  cosas que prefieres evitar. Lo guarda cuando le cuentas algo duradero ("me llamo Ana", "mi hija se
  llama Lucía", "no me gusta el reguetón") o le dices "recuerda que...". Guarda hasta 50 datos: si
  le dices algo más completo sustituye al dato viejo y, si se llena, olvida primero lo más antiguo de lo
  menos importante (nunca tu nombre). La memoria antigua (una lista de frases) se convierte sola.
- **Costumbres** (`uso.json`): solo contadores de lo que le pides: la música y los artistas, los programas
  que abres, el volumen que sueles poner, tus modos y a qué hora del día le hablas. Así sabe, por ejemplo,
  que sueles escuchar Bad Bunny o poner el volumen al 30 %. **No guarda** lo que le pides escribir o
  dictar, lo que buscas en internet, tus notas ni capturas. Lo reciente pesa más que lo de hace meses.
- **Conversaciones** (`diario.json`): al terminar una conversación de al menos dos frases, en segundo
  plano y con una sola consulta al LLM, apunta de qué hablasteis en una frase y añade al perfil lo nuevo
  que contaste de ti. Guarda los últimos 30 días; así puede decirte "la última vez hablamos de tu viaje".
- En cada respuesta Jarvis lee un resumen corto de todo esto (unos 1.500 caracteres como máximo, para no
  gastar la cuota gratis); leerlo tarda menos de un milisegundo.

Para verlo o borrarlo:

- "¿Qué sabes de mí?" te lo cuenta. Los tres archivos están en la carpeta de Jarvis y se pueden abrir
  con el Bloc de notas (si rompes `memoria.json` al editarlo, Jarvis sigue funcionando sin memoria y no
  lo sobrescribe hasta que lo arregles).
- "Olvida que vivo en Lima" borra ese dato. "Olvida todo lo que sabes de mí" te pide confirmar: di
  **"sí, bórralo todo"** y borra los tres archivos (tus notas y tu agenda no se tocan). También puedes
  borrarlos a mano con Jarvis cerrado.
- Ninguno se sube a Git (están en `.gitignore`).

Qué **no** hace: no se reentrena ni cambia el modelo de IA. "Aprender" aquí es memoria: el perfil, las
costumbres y los resúmenes que se le recuerdan en cada respuesta. Si borras los archivos, empieza de cero.

## Personalidad

Jarvis habla como una persona cercana: ingenioso, leal y con humor sutil, te llama por tu
nombre (dile "me llamo Ana" y lo recuerda), te saluda según la hora y no repite siempre lo mismo.
A veces usa exclamaciones con la entonación propia de Alexa ("¡bravo!", "ajá") y pausas naturales.

Para cambiar su forma de ser, copia `persona.ejemplo.md` como `persona.md` y escribe ahí cómo
quieres que sea (más formal, más bromista, con otro nombre...). Se aplica en la siguiente frase,
sin reiniciar. Si borras `persona.md`, vuelve la personalidad de ejemplo.

### Formas de hablar (como los Gems)

Además de su personalidad, Jarvis puede adoptar un papel durante la conversación: di
**"modo profesor"** (explica paso a paso y te pregunta para comprobar), **"modo entrenador"**
(rutinas sin aparatos), **"modo entrevistador"** (simula una entrevista de trabajo y te corrige),
**"modo cocinero"** (recetas paso a paso con lo que tengas) o **"modo traductor"** (traduce al
inglés lo que digas y el Echo lo pronuncia en inglés; con acento, porque la voz de Alexa en español
no tiene voz inglesa) o **"modo Xara"** (sarcástica, directa y honesta, con jerga peruana cuando encaja;
no te da la razón por darla y te empuja si te estás saboteando). **"Modo normal"** vuelve a lo de
siempre, y también al terminar la conversación.

Cada forma es un archivo de la carpeta `personas` (2-6 líneas). Para crear la tuya, copia uno,
renómbralo (por ejemplo `pirata.md`) y escribe cómo debe hablar; "modo pirata" la activa. Solo se
usan los primeros 800 caracteres. Si una rutina de `rutinas.json` se llama igual, gana la rutina.

## Que el Echo hable solo (opcional, Voice Monkey)

Una skill no puede hablar si no le hablas antes. Con [Voice Monkey](https://voicemonkey.io)
(plan gratis: 200 avisos al mes) el Echo dice en voz alta los recordatorios, los temporizadores
y el final de los encargos largos, además del aviso en el PC. Si no lo configuras, todo sigue igual.

1. En la app Alexa, busca la skill **Mono de Voz** (Voice Monkey) y actívala con tu cuenta.
2. Entra en [app.voicemonkey.io](https://app.voicemonkey.io) con tu cuenta de Amazon.
3. En *Speakers* pulsa *Add New Speaker*, ponle un nombre (por ejemplo `Echo salon`) y créalo.
4. En la app Alexa crea una rutina: *Más → Rutinas → +*. En *Cuando esto pase* elige
   *Casa inteligente → Alexa Voice Monkey v3 → VM Speakers* y tu Speaker; en *Añadir acción*
   elige *Skills → Mono de Voz* y en *Desde* tu Echo. Guárdala y pulsa *Test* en la consola de
   Voice Monkey: el Echo debería hablar.
5. Copia el **ID del Speaker** (botón de copiar junto a él en la consola) y crea un token en
   [app.voicemonkey.io/tokens](https://app.voicemonkey.io/tokens) (*Create Token*).
6. En `.env` pon `VOICEMONKEY_TOKEN=tu_token` y `VOICEMONKEY_DISPOSITIVO=id_del_speaker`, y
   reinicia `iniciar.bat`.

Jarvis lleva la cuenta en `echo_uso.json` y no pasa de **150 avisos al mes** (`LIMITE_ECHO_MES`,
deja margen para tus pruebas); cuando quedan pocos, lo dice al final del aviso. Los comentarios
de "vigila mi pantalla" nunca van al Echo: uno cada 20 segundos gastaría el mes en una tarde.
Para apagarlo sin borrar el token, pon `AVISOS_EN_ECHO=no`.

## Google: Gmail y Calendar gratis (opcional)

Jarvis puede leer tus correos sin leer y usar tu Google Calendar con un pequeño script que corre
en tu propia cuenta de Google (Apps Script): es gratis, no caduca y no necesita tarjeta. Solo lee
Gmail (permiso de solo lectura: **no puede enviar ni borrar correos**; lee remitente, asunto y un
fragmento, nunca adjuntos) y lee o crea eventos en tu calendario principal.

1. Entra en [script.google.com](https://script.google.com) con tu cuenta y pulsa **Nuevo proyecto**.
   Arriba, cambia "Proyecto sin título" por `Jarvis`.
2. En **Configuración del proyecto** (el engranaje de la izquierda), marca **Mostrar el archivo de
   manifiesto "appsscript.json" en el editor**.
3. Vuelve al **Editor** (`< >`). Abre `appsscript.json`, borra todo y pega el contenido de
   `google/appsscript.json` de la carpeta de Jarvis. Si no vives en México cambia `timeZone`
   (por ejemplo `America/Bogota` o `Europe/Madrid`).
4. Abre `Código.gs`, borra todo, pega el contenido de `google/Codigo.gs` y guarda (Ctrl+S).
5. Crea una clave secreta. En la carpeta de Jarvis, en una terminal:
   ```
   .venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
6. En **Configuración del proyecto** → **Propiedades del script** → **Añadir propiedad del script**:
   nombre `CLAVE` y como valor la clave del paso anterior. Guarda.
7. Arriba a la derecha, **Implementar** → **Nueva implementación** → engranaje → **Aplicación web**.
   "Ejecutar como": **Yo**. "Quién tiene acceso": **Cualquier usuario**. Pulsa **Implementar**.
8. Pulsa **Autorizar acceso** y elige tu cuenta. Google avisa de que la aplicación no está verificada
   porque es tuya: **Configuración avanzada** → **Ir a Jarvis (no seguro)** → **Permitir**. Pide ver tu
   correo (solo lectura) y gestionar tu calendario.
9. Copia la **URL de la aplicación web** (termina en `/exec`) y añade a tu `.env`:
   ```
   GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/.../exec
   GOOGLE_SCRIPT_CLAVE=la clave del paso 5
   ```
   Reinicia `iniciar.bat` y prueba: "¿tengo correos nuevos?".

Con Google configurado, "¿qué tengo mañana?" junta tu agenda del PC y la de Google (sin repetir) y
cada evento nuevo se guarda en el PC y, en segundo plano, también en Google. Si Google no responde,
sigue con la agenda del PC sin decir nada. Los avisos a la hora del evento y "borra la cita" solo
funcionan con los eventos guardados por Jarvis en el PC. Para usar Google solo para el correo,
pon `GOOGLE_AGENDA=no`.

- **Seguridad**: cualquiera que tenga la URL recibe solo "clave incorrecta" si no sabe la clave.
  Trátala como una contraseña: si la compartiste, cambia la propiedad `CLAVE` y tu `.env`.
- **Si cambias el script**: **Implementar** → **Gestionar implementaciones** → lápiz → Versión:
  **Nueva versión** → **Implementar**. La URL no cambia.
- **Cuotas gratis de Google**: miles de lecturas de correo y de eventos al día, de sobra para Jarvis.
- **"Google no devolvió datos"**: en el paso 7 "Quién tiene acceso" no quedó en "Cualquier usuario".
  **"Google rechazó la clave"**: la de `.env` y la propiedad `CLAVE` no son iguales (o tiene menos de
  20 caracteres).

## Interfaz visual

Al hablar con Jarvis se abre en tu pantalla una ventana pequeña (Microsoft Edge en modo
aplicación, ya viene con Windows 11) con un orbe animado que cambia según Jarvis esté en
espera, escuchando, pensando o hablando. Muestra lo que dijiste, lo que contesta, las acciones
que ejecuta y los avisos. Mientras hablas se queda encima de las demás ventanas; al terminar la
conversación se minimiza a los pocos segundos y la siguiente vez vuelve a aparecer.

- También puedes abrirla a mano en `http://127.0.0.1:5000/hud`. Solo funciona en tu PC: por
  ngrok no se puede ver.
- **Vigilar la pantalla**: con "vigila mi pantalla diez minutos" Jarvis comenta cada 20 segundos
  (mínimo 15, por el límite gratis de Gemini) lo que pasa, en la ventana visual o, si lo pides,
  también en voz por el PC, hasta 30 minutos seguidos (más gastaría la cuota diaria gratis de Gemini).
  Mientras vigila, la ventana no se esconde.
- Para que no se abra, pon `HUD_ACTIVO=no` en `.env`.
- La onda animada es [SiriWave](https://github.com/kopiro/siriwave) de Flavio De Stefano
  (licencia MIT, ver `hud/NOTICE`); el resto del diseño es propio.

## Velocidad

Lo que pasa desde que terminas de hablar hasta que Alexa empieza a contestar:

| Paso | Tiempo aproximado | ¿Lo controla Jarvis? |
|---|---|---|
| Alexa reconoce tu voz y manda el texto | 0,5–1 s | No |
| Viaje por ngrok (ida y vuelta) | 0,1–0,3 s | No |
| Servidor de Jarvis (decidir y preparar la voz) | ~1 ms (medido; la firma de Alexa suma unos ms) | Sí |
| Ruta rápida: reconocer una orden frecuente | ~0,01 ms (medido) | Sí |
| IA (Groq `gpt-oss-120b` con razonamiento bajo) | ~1 s por llamada | En parte |
| Alexa empieza a leer la respuesta | 0,5–1 s | No |

- **Órdenes frecuentes sin IA** (ruta rápida): pausa/play, siguiente/anterior, subir/bajar/silenciar
  el volumen y "volumen al 30", "pon (música de) X" / "reproduce X", "abre" (programas, webs y carpetas
  conocidas), "cierra" (programas conocidos, la ventana), pantalla completa, adelantar/retroceder,
  clic, doble clic, "haz clic en X", subir/bajar la página, mover el mouse, apagar/reiniciar/cancelar,
  captura, minimizar, bloquear, suspender, y la hora y la fecha. Responden en lo que tarda la propia
  acción (casi nada; "pon X" espera a YouTube, ~0,5 s). Si la frase tiene dos órdenes ("y", "luego",
  comas), una pregunta o un matiz, la decide la IA: es más lenta pero no se equivoca de orden.
- **Órdenes con IA**: una sola llamada. Si la IA solo usó acciones ("pon un temporizador de cinco
  minutos"), Jarvis dice el resultado de la acción sin preguntarle otra vez. Conversar o buscar
  información también es una llamada (dos si busca en internet).
- **Razonamiento bajo**: `gpt-oss` piensa antes de contestar; en "low" la primera palabra llega en
  ~1,1 s frente a ~4,7 s en "high" (medición pública de Artificial Analysis para Groq).
- **Caché de Groq**: las instrucciones y las funciones van siempre iguales y al principio; la hora y lo que
  sabe de ti van al final. Así Groq reutiliza lo repetido: contesta antes y esos tokens no cuentan en sus
  límites (Groq no garantiza que siempre acierte).
- **Respuestas largas**: Jarvis dice como mucho unas 55 palabras (~20 s) de una vez, cortando al final de
  una frase, y pregunta "¿Sigo?". Di "sí" o "sigue" para oír el resto; "no" o cualquier otra pregunta lo
  descarta.

### Cuánto da el plan gratis

Groq gratis da, **por modelo**, 30 peticiones/min, 1.000/día, 8.000 tokens/min y 200.000 tokens/día. Jarvis
usa dos modelos de Groq (`gpt-oss-120b` y, si se agota, `gpt-oss-20b`, cada uno con su cuota) y luego Gemini.
Tras un "límite alcanzado" (429) se salta ese modelo el tiempo que Groq indica, sin perder tiempo en
reintentos. Cifras aproximadas por conversación con la IA (las órdenes de la ruta rápida no gastan nada):

| | Tokens que cuentan | Seguidas por minuto (Groq) | Al día (Groq) |
|---|---|---|---|
| 1.1.0 (dos llamadas por orden, historial sin tope) | ~7.500 | ~1 (la 2.ª ya pasaba a Gemini) | ~27 |
| Ahora (71 funciones), si Groq no usa la caché | ~6.300 | ~2,5 (dos modelos) | ~65 |
| Ahora, con la caché (lo normal al repetir) | ~800 | ~20 (tope de 30 peticiones) | ~500 |

Encima de eso quedan Gemini (unas 500 al día gratis en flash-lite, más lento) y la ruta rápida, sin límite.
`scripts/medir_latencia.py` muestra los tokens reales de cada llamada en tu PC.
- **Mídelo en tu PC**: `.venv\Scripts\python scripts\medir_latencia.py` hace 5 veces una orden directa, una
  orden con IA y una pregunta, con tus claves, y muestra la mediana y el p90 (las acciones se simulan: no
  toca tu PC). En el registro de Jarvis (`logs/jarvis.log`, o clic derecho en el icono → Ver registro) cada petición dice cuánto tardó la IA, cuántos tokens fueron a la
  caché y cuánto las acciones; el HUD lo muestra en pequeño abajo.
- Si una respuesta pasa de 6,5 s (Groq saturado y Gemini lento), Alexa dice "dime 'y bien'" para no
  cortarse a los 8 s.

## Limitaciones

- **Aún no se ha probado en un Windows real**: está probado con pruebas automáticas, pero la
  primera vez puede fallar algún detalle. Los errores salen en el registro (`logs/jarvis.log`).
- Siempre hay que empezar con **"Alexa, abre mi jarvis"** (o "pide a mi jarvis..."): una skill
  propia no puede escuchar sin su nombre.
- **Alexa no habla sola** salvo con Voice Monkey (opcional, ver arriba): sin él, recordatorios,
  temporizadores y comentarios de la pantalla salen solo en el PC.
- El **PC debe estar encendido** con `iniciar.bat` abierto. Las órdenes actúan sobre el PC, no
  sobre el Echo (la música suena por los altavoces del PC).
- **Freno de seguridad**: una web, una nota o algo en pantalla podría traer órdenes escondidas para la
  IA. Por eso, si en la misma petición Jarvis acaba de leer internet, la pantalla o tus notas, no escribe,
  no pulsa teclas, no hace clic, no cierra programas ni ventanas, no apaga ni bloquea el PC, no borra citas y no cambia
  su memoria: te lo dice y basta con que se lo pidas otra vez con tus palabras.
- **Ver la pantalla envía capturas a Google** (Gemini) y gasta su cuota gratis; vigilar la
  pantalla durante mucho rato puede agotarla. No lo uses con datos privados a la vista. "Haz clic en..."
  también envía una captura.
- **El mouse solo usa la pantalla principal**: con dos monitores no se mueve ni hace clic en el segundo.
  Los encargos largos no usan el mouse (actuarían sobre lo que tengas delante mientras trabajas).
- Los planes gratis tienen límites por minuto y por día; con las dos claves casi no se notan.
- En modo desarrollo la skill solo funciona en **tu cuenta de Amazon** y tus dispositivos.
- El **idioma de la skill debe coincidir con el de tu Echo**; si no, Alexa no la encuentra.
- Agenda, memoria, costumbres, modos y notas se guardan solo en tu PC (`agenda.json`, `memoria.json`, `uso.json`, `diario.json`, `rutinas.json`, `notas`).

## Problemas comunes

- **"No encuentro Python"**: reinstala Python marcando *Add python.exe to PATH*.
- **"No encuentro ngrok"**: ejecuta `winget install ngrok.ngrok` y vuelve a abrir `iniciar.bat`.
- **Sale un aviso "Falta ALEXA_SKILL_ID" o "Falta GROQ_API_KEY..."**: Jarvis abre el
  archivo `.env` para que lo revises (sin espacios alrededor del `=`).
- **Alexa dice "Hubo un problema con la respuesta de la skill"**: comprueba que el icono de Jarvis
  está junto al reloj, que el Endpoint termina en `/alexa`, que elegiste la opción de certificado
  *wildcard* y que el Skill ID de `.env` es el de tu skill.
- **ngrok dice que el endpoint ya está en uso** (`ERR_NGROK_334`): ya hay otro ngrok abierto;
  ciérralo y vuelve a abrir `iniciar.bat`.
- **Alexa no encuentra "mi jarvis"**: revisa que la pestaña *Test* esté en *Development* y
  que el idioma de la skill sea el de tu Echo.
- **"Me tardé demasiado"** o **"No pude pensar ahora mismo"**: la IA iba lenta o se agotó el
  límite gratis del minuto; espera un poco y repite. Pon las dos claves para que use la otra.
- **No pausa ni cambia de canción**: actúa sobre lo que esté sonando en el PC; si no suena
  nada, no pasa nada.
- **Groq dice que llegaste al límite (429)**: cada consulta a la IA envía unos 6.000 tokens y el plan gratis
  de Groq da 8.000 por minuto por modelo. La parte repetida suele ir a su caché (no cuenta) y las órdenes
  frecuentes no usan la IA, pero si conversas mucho seguido Jarvis pasa solo a `gpt-oss-20b` y luego a
  Gemini (algo más lento). Es normal; en el registro verás "LLM ... falló: RateLimitError".
- **Cambiaste `requirements.txt`** o falla la instalación: borra la carpeta `.venv` y abre
  `iniciar.bat` otra vez.

## Pruebas automáticas

`python -m pytest -q` prueba todo sin red ni Alexa. Si subes la carpeta a GitHub, el workflow
`.github/workflows/pruebas.yml` repite las pruebas en un Windows 11 real (Python 3.12 y 3.14): instala
`requirements.txt`, comprueba las librerías de Windows (volumen, teclado, ventanas, portapapeles, captura,
registro), arranca `servidor.py` y comprueba que sirve el HUD y rechaza peticiones sin firma de Alexa.
