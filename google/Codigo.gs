// Puente gratis entre Jarvis y tu cuenta de Google. Pasos en la sección "Google" del README.
// Solo lee Gmail (permiso gmail.readonly: no puede enviar ni borrar correos) y lee o crea eventos
// en tu calendario principal. Jarvis le habla por POST con una clave que solo conocen tu PC y este script.

var MAX_CORREOS = 10;
var MAX_EVENTOS = 50;
var MAX_TITULO = 200;
var MAX_FRAGMENTO = 300;

function doPost(e) {
  var pedido;
  try {
    pedido = JSON.parse(e.postData.contents);
  } catch (error) {
    return responder({error: 'pedido'});
  }
  if (!claveCorrecta(pedido.clave)) {
    return responder({error: 'clave'});
  }
  try {
    if (pedido.accion === 'correos') return responder(correos(pedido));
    if (pedido.accion === 'eventos') return responder(eventos(pedido));
    if (pedido.accion === 'crear_evento') return responder(crearEvento(pedido));
    return responder({error: 'accion'});
  } catch (error) {
    return responder({error: 'google', detalle: String(error).slice(0, 200)});
  }
}

// Abrir la URL en el navegador no debe revelar nada.
function doGet() {
  return responder({error: 'usa POST'});
}

function responder(datos) {
  return ContentService.createTextOutput(JSON.stringify(datos)).setMimeType(ContentService.MimeType.JSON);
}

function huella(texto) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(texto), Utilities.Charset.UTF_8);
}

// Compara las huellas SHA-256 byte a byte sin salir antes: así el tiempo no revela cuánto acierta la clave.
function claveCorrecta(recibida) {
  var guardada = PropertiesService.getScriptProperties().getProperty('CLAVE');
  if (!guardada || guardada.length < 20 || typeof recibida !== 'string') return false;
  var a = huella(guardada);
  var b = huella(recibida);
  var diferencia = 0;
  for (var i = 0; i < a.length; i++) {
    diferencia |= a[i] ^ b[i];
  }
  return diferencia === 0;
}

function cabecera(mensaje, nombre) {
  var cabeceras = mensaje.payload.headers || [];
  for (var i = 0; i < cabeceras.length; i++) {
    if (cabeceras[i].name.toLowerCase() === nombre) return cabeceras[i].value;
  }
  return '';
}

function correos(pedido) {
  var cantidad = Math.min(Math.max(parseInt(pedido.cantidad, 10) || 5, 1), MAX_CORREOS);
  var consulta = pedido.solo_no_leidos === false ? 'in:inbox' : 'is:unread in:inbox';
  var lista = Gmail.Users.Messages.list('me', {q: consulta, maxResults: cantidad}).messages || [];
  // format "metadata": solo cabeceras y el fragmento de Gmail; nunca el cuerpo ni los adjuntos.
  var resultado = lista.map(function (item) {
    var mensaje = Gmail.Users.Messages.get('me', item.id, {format: 'metadata', metadataHeaders: ['From', 'Subject']});
    return {
      de: cabecera(mensaje, 'from'),
      asunto: cabecera(mensaje, 'subject').slice(0, MAX_TITULO),
      fragmento: (mensaje.snippet || '').slice(0, MAX_FRAGMENTO),
      fecha: new Date(Number(mensaje.internalDate)).toISOString(),
      no_leido: (mensaje.labelIds || []).indexOf('UNREAD') !== -1
    };
  });
  var bandeja = Gmail.Users.Labels.get('me', 'INBOX');
  return {correos: resultado, no_leidos: bandeja.messagesUnread || 0};
}

function fecha(texto) {
  var valor = new Date(texto);
  if (isNaN(valor.getTime())) throw new Error('fecha no valida');
  return valor;
}

function eventos(pedido) {
  var calendario = CalendarApp.getDefaultCalendar();
  var zona = calendario.getTimeZone();
  var lista = calendario.getEvents(fecha(pedido.desde), fecha(pedido.hasta)).slice(0, MAX_EVENTOS);
  return {
    eventos: lista.map(function (evento) {
      return {
        titulo: evento.getTitle().slice(0, MAX_TITULO),
        inicio: evento.getStartTime().toISOString(),
        todo_el_dia: evento.isAllDayEvent(),
        dia: Utilities.formatDate(evento.getStartTime(), zona, 'yyyy-MM-dd')
      };
    })
  };
}

function crearEvento(pedido) {
  var titulo = String(pedido.titulo || '').trim().slice(0, MAX_TITULO);
  if (!titulo) throw new Error('falta el titulo');
  var evento = CalendarApp.getDefaultCalendar().createEvent(titulo, fecha(pedido.inicio), fecha(pedido.fin));
  return {ok: true, id: evento.getId()};
}
