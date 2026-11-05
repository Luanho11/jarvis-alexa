const NOMBRES_ESTADO = {
  espera: "En espera",
  escuchando: "Escuchando",
  pensando: "Pensando",
  hablando: "Hablando",
};
const AMPLITUD = { espera: 0.05, escuchando: 0.2, pensando: 0.5, hablando: 1 };
const MAX_ACCIONES = 4;

const elementos = {
  estado: document.getElementById("estado"),
  conexion: document.getElementById("conexion"),
  reloj: document.getElementById("reloj"),
  usuario: document.getElementById("usuario"),
  respuesta: document.getElementById("respuesta"),
  acciones: document.getElementById("acciones"),
  comentario: document.getElementById("comentario"),
  aviso: document.getElementById("aviso"),
  latencia: document.getElementById("latencia"),
};

const onda = new SiriWave({
  container: document.getElementById("onda"),
  style: "ios9",
  cover: true,
  amplitude: AMPLITUD.espera,
  speed: 0.08,
});

let vueltaAEscuchar;
let finAviso;

function ponerEstado(estado) {
  document.body.dataset.estado = estado;
  elementos.estado.textContent = NOMBRES_ESTADO[estado];
  onda.setAmplitude(AMPLITUD[estado]);
}

// En ventanas pequeñas la respuesta hace scroll: se deja visible el final, que es lo último que dice.
function mostrarFinal() {
  const respuesta = elementos.respuesta;
  respuesta.scrollTop = respuesta.scrollHeight;
  respuesta.classList.toggle("desborda", respuesta.scrollHeight > respuesta.clientHeight);
}
// Un aviso o comentario que aparece debajo encoge la respuesta y movería lo visible.
new ResizeObserver(mostrarFinal).observe(elementos.respuesta);

function hablar(texto) {
  elementos.respuesta.textContent = texto;
  mostrarFinal();
  ponerEstado("hablando");
  clearTimeout(vueltaAEscuchar);
  // Alexa lee unas 15 letras por segundo; al terminar vuelve a escuchar.
  vueltaAEscuchar = setTimeout(() => ponerEstado("escuchando"), Math.max(2000, texto.length * 65));
}

function escucharUsuario(texto) {
  clearTimeout(vueltaAEscuchar);
  elementos.usuario.textContent = texto;
  elementos.respuesta.textContent = "";
  elementos.acciones.replaceChildren();
  ponerEstado("pensando");
}

function agregarAccion(nombre) {
  const accion = document.createElement("li");
  accion.className = "accion";
  accion.textContent = nombre.replaceAll("_", " ");
  elementos.acciones.append(accion);
  while (elementos.acciones.children.length > MAX_ACCIONES) {
    elementos.acciones.firstElementChild.remove();
  }
}

function avisar(texto) {
  elementos.aviso.textContent = texto;
  elementos.aviso.classList.add("visible");
  clearTimeout(finAviso);
  finAviso = setTimeout(() => elementos.aviso.classList.remove("visible"), 10000);
}

function esperar() {
  clearTimeout(vueltaAEscuchar);
  ponerEstado("espera");
}

const manejadores = {
  usuario: escucharUsuario,
  respuesta: hablar,
  accion: agregarAccion,
  aviso: avisar,
  comentario: (texto) => { elementos.comentario.textContent = texto; },
  espera: esperar,
  latencia: (texto) => { elementos.latencia.textContent = texto; },
};

const fuente = new EventSource("/hud/eventos");
fuente.onopen = () => {
  elementos.conexion.textContent = "en línea";
  elementos.conexion.classList.remove("sin-conexion");
};
fuente.onerror = () => {
  elementos.conexion.textContent = "sin conexión";
  elementos.conexion.classList.add("sin-conexion");
};
fuente.onmessage = (mensaje) => {
  const { tipo, texto } = JSON.parse(mensaje.data);
  manejadores[tipo]?.(texto);
};

// Las órdenes van en JSON: el servidor lo exige para que otra web del PC no pueda enviarlas.
async function enviar(ruta, datos) {
  try {
    const respuesta = await fetch(ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });
    if (!respuesta.ok) avisar("Jarvis no aceptó la orden.");
  } catch {
    avisar("No hay conexión con Jarvis. ¿Está abierto iniciar.bat?");
  }
}

for (const boton of document.querySelectorAll("[data-orden]")) {
  boton.addEventListener("click", () => enviar("/hud/orden", { orden: boton.dataset.orden }));
}

const formulario = document.getElementById("escribir");
const campo = document.getElementById("texto");
formulario.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  enviar("/hud/escribir", { texto });
});

function actualizarReloj() {
  elementos.reloj.textContent = new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
}
actualizarReloj();
setInterval(actualizarReloj, 10000);
