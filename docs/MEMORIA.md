# Memoria de Jarvis: cómo lo hacen ChatGPT, Gemini y Claude y qué copiamos (05/11/2026)

## Cómo funciona en los grandes

**ChatGPT** (OpenAI)
- Dos capas desde abril de 2025: **memorias guardadas** (frases sueltas que el usuario puede ver y borrar) y
  **referencia al historial** (ideas sacadas de conversaciones pasadas, que no se ven una a una).
- Las memorias guardadas se crean cuando el usuario dice "recuerda que..." y también solas, cuando ChatGPT
  detecta un detalle útil. Avisa con "memoria actualizada". Está entrenado para **no guardar por su cuenta
  datos sensibles** (salud, por ejemplo) salvo que se lo pidan.
- Desde octubre de 2025 **gestiona sola la memoria llena**: ya no hay que borrar a mano; prioriza lo que más
  importa (según la comunidad, lo reciente y lo que se repite) y deja en segundo plano lo demás en vez de
  borrarlo. El usuario puede buscar y ordenar por fecha y repriorizar.
- En junio de 2026 estrenó una arquitectura de memoria nueva con una página de resumen para revisar y corregir
  lo que recuerda; OpenAI publica mejoras en recuerdo de hechos (67,9 % → 82,8 %) y en seguir preferencias.
- Controles: apagar memoria o solo el historial, "olvida esto", ver y borrar memorias, y el **chat temporal**,
  que no usa ni actualiza la memoria. Borrar un chat no borra lo que se aprendió de él.

**Claude** (Anthropic)
- "Generar memoria a partir de los chats": escribe entradas nuevas y **actualiza las que ya tiene** mientras
  hablas; se puede orientar ("céntrate en...", "ignora...").
- "Buscar y consultar chats": busca conversaciones pasadas **cuando hace falta**, aparte de la memoria.
- Todo visible, editable y borrable en Ajustes → Memoria; el modo incógnito no lee ni escribe memoria y cada
  proyecto tiene su memoria propia.

**Gemini** (Google)
- *Personal Intelligence*: aprende detalles y preferencias de conversaciones pasadas automáticamente; aparte,
  "Información guardada" son instrucciones fijas que pone el usuario.
- Borrar una conversación de la actividad deja de usarla para personalizar; el chat temporal no usa historial.
- Google no publica cada cuánto se actualiza la capa automática, y esa capa no es del todo visible.

## Qué hace Jarvis (gratis y en local)

| Idea | En los grandes | En Jarvis |
|---|---|---|
| Memorias explícitas | "Recuerda que..." | Herramienta `recordar(dato, categoria)` |
| Memorias automáticas | El modelo detecta detalles útiles | **Cada frase**, sin LLM: reglas para "me llamo / vivo en / soy de / trabajo en / estudio / tengo N años / me gusta / me encanta / prefiero / no me gusta / odio / mi hermana se llama / mi X favorito es". Y **al cerrar la sesión**, una llamada al LLM saca hasta 5 hechos y hasta 3 que ya no son ciertos |
| Actualizar en vez de duplicar | Claude y ChatGPT actualizan entradas | Un dato más completo sustituye al que contiene; los de un solo valor se sustituyen ("Vive en Cusco" reemplaza "Vive en Lima", "Tiene 31 años" a "Tiene 30"); "ya no vive en Lima" lo borra; "No le gusta el café" corrige "Le gusta el café" |
| Sin "memoria llena" | Gestión automática y prioridades | **Sin límite de datos.** Cada uno guarda categoría, creado, visto (última confirmación), veces confirmado, usado y origen. Al prompt solo van los más útiles para **ese** pedido (ver abajo) |
| Historial de conversaciones | Referencia al historial / búsqueda de chats | `diario.json`: una frase por conversación, 365 días; van al prompt las más relacionadas con el pedido o, si no hay, las más recientes |
| No guardar lo sensible | ChatGPT evita salud salvo petición | Las reglas descartan contraseñas, claves, PIN, tarjetas, cuentas, documentos, números largos y salud; el resumen del LLM tiene la misma orden. Las costumbres no guardan lo que se escribe, busca o anota |
| Chat temporal / incógnito | No usa ni actualiza memoria | `conversacion_privada()`: hasta que termina la sesión no aprende de frases, uso ni resumen (lo que ya sabe lo sigue usando) |
| Ver, corregir y borrar | Página de memoria | "¿Qué sabes de mí?", "olvida que...", "olvida todo" con "sí, bórralo todo"; los archivos se pueden abrir con el Bloc de notas |
| Reentrenar el modelo | Tampoco lo hacen con tu memoria | No. "Aprender" es memoria que se le recuerda en cada respuesta |

### Cómo elige qué datos van al prompt

Con miles de datos guardados el prompt sigue en ~1.500 caracteres (≈ 420 tokens), dentro de la cuota de Groq:

1. Siempre el nombre y, primero, lo que hay que **evitar**.
2. El resto se ordena por puntos: **4 por cada palabra** que comparte con el pedido (sin tildes, recortadas a
   5 letras: "hermano" encuentra "hermana"), más el **peso** de la categoría (personas y datos 2, gustos y
   rutinas 1), más **1 por cada confirmación** extra (hasta 4), más hasta **2 por lo reciente** (baja en un mes).
3. Se añaden en ese orden mientras quepan y se agrupan por categoría.
4. Un dato elegido por coincidir con el pedido queda marcado como **usado** (una escritura al día como mucho).

Con 2.000 datos se elige en ~9 ms; con unos cientos, 1–2 ms. Guardar un dato con 2.000 guardados: ~9 ms.

### Por qué así

- **Reglas por frase en vez de LLM por frase**: cada llamada extra al LLM gratis costaría ~1 s y cuota. Las
  reglas solo aceptan afirmaciones claras: no aprenden de preguntas ("¿qué me gusta?"), condiciones ("si me
  gusta"), cosas del momento ("me gusta esta canción", "trabajo en casa hoy") ni de dictados ("escribe...").
  Lo que se les escapa lo recoge el resumen al final de la sesión.
- **Palabras clave en vez de embeddings**: instantáneo, sin dependencias ni cuota, y funciona sin internet.
- **Correcciones del LLM con cuidado**: "olvidar" solo borra datos casi idénticos (85 % de parecido) a uno
  guardado, para que una respuesta rara no borre de más.

## Fuentes

- [OpenAI: Memory and new controls for ChatGPT](https://openai.com/blog/memory-and-new-controls-for-chatgpt)
- [ChatGPT can now automatically manage saved memories (oct. 2025)](https://www.republicworld.com/tech/openai-announces-auto-manage-saved-memories-for-chatgpt-users-heres-what-it-means)
- [ChatGPT gets smarter memory and a new page to manage it (jun. 2026)](https://techlomedia.in/2026/06/chatgpt-gets-smarter-memory-and-a-new-page-to-manage-what-it-remembers-124338/)
- [OpenAI Community: How does ChatGPT decide which memories to retrieve?](https://community.openai.com/t/how-does-chatgpt-decide-which-memories-to-retrieve/1385823)
- [Claude vs ChatGPT vs Gemini memory: how they compare in 2026](https://blog.memoryplugin.com/claude-vs-chatgpt-vs-gemini-memory/)
