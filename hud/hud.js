const NOMBRES_ESTADO = {
  espera: "En espera",
  escuchando: "Escuchando",
  pensando: "Pensando",
  hablando: "Hablando",
};
const AMPLITUD = { espera: 0.05, escuchando: 0.2, pensando: 0.5, hablando: 1 };
const MAX_ACCIONES = 4;
const MAX_HISTORIAL = 20;

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

const MS_POR_LETRA = 65;
const reducirMovimiento = matchMedia("(prefers-reduced-motion: reduce)");

let vueltaAEscuchar;
let finAviso;
let escritura;
const historial = [];

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

// La respuesta aparece palabra a palabra al ritmo de la voz, salvo si Windows pide reducir el movimiento.
function escribirPocoAPoco(texto, duracion) {
  clearInterval(escritura);
  const palabras = texto.split(" ");
  if (reducirMovimiento.matches || palabras.length < 4) {
    elementos.respuesta.textContent = texto;
    mostrarFinal();
    return;
  }
  let mostradas = 0;
  escritura = setInterval(() => {
    mostradas += 1;
    elementos.respuesta.textContent = palabras.slice(0, mostradas).join(" ");
    mostrarFinal();
    if (mostradas === palabras.length) clearInterval(escritura);
  }, duracion / palabras.length);
}

function guardarEnHistorial(texto) {
  historial.push({
    hora: new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" }),
    usuario: elementos.usuario.textContent,
    respuesta: texto,
  });
  historial.splice(0, historial.length - MAX_HISTORIAL);
}

function pintarHistorial() {
  const lista = document.getElementById("lista-historial");
  lista.replaceChildren(...historial.map(({ hora, usuario, respuesta }) => {
    const item = document.createElement("li");
    const cabeza = document.createElement("p");
    cabeza.className = "historial-usuario";
    cabeza.textContent = usuario ? `${hora} · ${usuario}` : hora;
    const cuerpo = document.createElement("p");
    cuerpo.textContent = respuesta;
    const copiar = document.createElement("button");
    copiar.type = "button";
    copiar.className = "copiar";
    copiar.textContent = "Copiar";
    copiar.addEventListener("click", async () => {
      await navigator.clipboard.writeText(respuesta);
      copiar.textContent = "Copiado";
    });
    item.append(cabeza, cuerpo, copiar);
    return item;
  }));
  document.querySelector(".historial-vacio").hidden = historial.length > 0;
  lista.lastElementChild?.scrollIntoView({ block: "end" });
}

const botonHistorial = document.getElementById("ver-historial");
botonHistorial.addEventListener("click", () => {
  const panelHistorial = document.getElementById("historial");
  panelHistorial.hidden = !panelHistorial.hidden;
  botonHistorial.setAttribute("aria-expanded", String(!panelHistorial.hidden));
  if (!panelHistorial.hidden) pintarHistorial();
});

function hablar(texto) {
  guardarEnHistorial(texto);
  // Alexa lee unas 15 letras por segundo; al terminar vuelve a escuchar.
  const duracion = Math.max(2000, texto.length * MS_POR_LETRA);
  escribirPocoAPoco(texto, duracion);
  ponerEstado("hablando");
  clearTimeout(vueltaAEscuchar);
  vueltaAEscuchar = setTimeout(() => ponerEstado("escuchando"), duracion);
}

function escucharUsuario(texto) {
  // Los ejemplos solo sirven hasta la primera orden.
  document.getElementById("ejemplos").hidden = true;
  clearTimeout(vueltaAEscuchar);
  clearInterval(escritura);
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

let cuentaAtras;

function contarHasta(que, texto) {
  const cuenta = document.getElementById("cuenta");
  clearInterval(cuentaAtras);
  let quedan = Number(texto);
  cuenta.hidden = !(quedan > 0);
  if (cuenta.hidden) return;
  const pintar = () => {
    const minutos = Math.floor(quedan / 60);
    const segundos = String(quedan % 60).padStart(2, "0");
    document.getElementById("cuenta-texto").textContent = `${que} en ${minutos}:${segundos}`;
  };
  pintar();
  cuentaAtras = setInterval(() => {
    quedan -= 1;
    if (quedan <= 0) {
      clearInterval(cuentaAtras);
      cuenta.hidden = true;
      return;
    }
    pintar();
  }, 1000);
}

const manejadores = {
  apagado: (texto) => contarHasta("Apagando el PC", texto),
  reinicio: (texto) => contarHasta("Reiniciando el PC", texto),
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

for (const ejemplo of document.querySelectorAll("#ejemplos button")) {
  ejemplo.addEventListener("click", () => enviar("/hud/escribir", { texto: ejemplo.textContent }));
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
