#!/usr/bin/env python3
"""Sonda de maquetación: abre el sitio en Chrome de verdad y lo mide.

Una captura de pantalla no dice si algo desborda tres píxeles ni si una imagen
llegó a cargarse; el DOM sí. Esta sonda recorre cada ruta, en cada idioma y a
cada ancho, y devuelve números:

  · desborde horizontal, y qué elemento concreto lo causa
  · imágenes que no cargaron, o sin texto alternativo
  · ids repetidos (rompen las etiquetas de formulario y el salto por ancla)
  · campos de formulario sin nombre accesible
  · menú lateral recortado
  · fugas de idioma: texto latino dentro de la versión árabe

Sólo biblioteca estándar y el Chrome que ya está instalado. Sin pip, sin red.

    python3 herramientas/sonda.py marsa.html
    python3 herramientas/sonda.py marsa.html --anchos 1440,1100,820,600
"""
import base64, json, os, random, socket, struct, subprocess, sys, time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PUERTO = 9412


# ------------------------------------------------------------ WebSocket mínimo
class WS:
    """Cliente WebSocket de texto, lo justo para hablar con Chrome."""

    def __init__(self, url):
        resto = url.split('://', 1)[1]
        hostport, _, ruta = resto.partition('/')
        host, _, puerto = hostport.partition(':')
        self.sock = socket.create_connection((host, int(puerto or 80)), timeout=120)
        clave = base64.b64encode(bytes(random.getrandbits(8) for _ in range(16))).decode()
        self.sock.sendall((f'GET /{ruta} HTTP/1.1\r\nHost: {hostport}\r\n'
                           f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {clave}\r\n'
                           f'Sec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.sock.recv(4096)
        if b'101' not in buf.split(b'\r\n')[0]:
            raise RuntimeError('Chrome rechazó la conexión: ' + buf[:120].decode('latin1'))
        self.resto = buf.split(b'\r\n\r\n', 1)[1]

    def _leer(self, n):
        datos, self.resto = self.resto[:n], self.resto[n:]
        while len(datos) < n:
            trozo = self.sock.recv(min(1 << 20, n - len(datos)))
            if not trozo:
                raise ConnectionError('Chrome cerró la conexión')
            datos += trozo
        return datos

    def enviar(self, obj):
        carga = json.dumps(obj).encode()
        mascara = bytes(random.getrandbits(8) for _ in range(4))
        n = len(carga)
        cab = bytearray([0x81])
        if n < 126:
            cab.append(0x80 | n)
        elif n < (1 << 16):
            cab.append(0x80 | 126); cab += struct.pack('>H', n)
        else:
            cab.append(0x80 | 127); cab += struct.pack('>Q', n)
        cab += mascara + bytes(b ^ mascara[i % 4] for i, b in enumerate(carga))
        self.sock.sendall(bytes(cab))

    def recibir(self):
        partes = []
        while True:
            b1, b2 = self._leer(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._leer(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._leer(8))[0]
            if b2 & 0x80:
                self._leer(4)
            carga = self._leer(n)
            if opcode == 0x8:
                raise ConnectionError('Chrome cerró la conexión')
            if opcode == 0x9:
                continue
            partes.append(carga)
            if fin:
                return json.loads(b''.join(partes).decode())


def espera_listo(ev, intentos=40):
    """Espera a que el guion de la página esté evaluado.

    Con una espera fija la sonda a veces medía antes de que existiera
    `aplicar`, y entonces daba por buena una página que ni siquiera había
    cambiado de idioma. Mejor esperar a la condición que al reloj.
    """
    for _ in range(intentos):
        if ev('typeof aplicar === "function" && document.readyState === "complete"'):
            return
        time.sleep(0.1)
    raise RuntimeError('la página no terminó de cargar: `aplicar` no existe')


def espera_chrome(puerto, intentos=60):
    for _ in range(intentos):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{puerto}/json/list', timeout=1) as r:
                for t in json.load(r):
                    if t.get('type') == 'page' and t.get('webSocketDebuggerUrl'):
                        return t['webSocketDebuggerUrl']
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError('Chrome no abrió el puerto de depuración')


# ------------------------------------------------------- la medición, en la página
MEDIR = r'''
(function(){
  var PERMITIDAS = __PERMITIDAS__;
  var doc = document.documentElement, out = {};
  out.ruta   = location.hash;
  out.lang   = doc.lang;
  out.dir    = doc.dir;
  out.ancho  = doc.clientWidth;
  out.desborde = Math.max(0, doc.scrollWidth - doc.clientWidth);

  // Quién desborda: sólo lo visible, y sólo si se sale del marco de verdad.
  out.culpables = [];
  if (out.desborde > 0){
    var todos = document.querySelectorAll("body *");
    for (var i=0;i<todos.length;i++){
      var e = todos[i];
      if (e.offsetParent === null && getComputedStyle(e).position !== "fixed") continue;
      var r = e.getBoundingClientRect();
      if (r.width === 0) continue;
      var fuera = doc.dir === "rtl" ? -r.left : r.right - doc.clientWidth;
      if (fuera > 1) out.culpables.push({
        sel: e.tagName.toLowerCase() + (e.id ? "#"+e.id : "") +
             (e.className && typeof e.className === "string" ? "."+e.className.trim().split(/\s+/).join(".") : ""),
        px: Math.round(fuera), ancho: Math.round(r.width)
      });
    }
    out.culpables = out.culpables.slice(0, 6);
  }

  // Imágenes de la ruta visible
  var vis = document.querySelector("[data-ruta]:not([hidden])");
  out.imgs = 0; out.imgsRotas = []; out.imgsSinAlt = [];
  var imgs = document.querySelectorAll("img");
  for (var j=0;j<imgs.length;j++){
    var im = imgs[j];
    if (im.offsetParent === null) continue;
    out.imgs++;
    /* Rota es la que TERMINÓ de cargar sin píxeles. Una imagen con
       loading="lazy" que aún no ha entrado en pantalla no está rota: está
       esperando, y contarla daba doce avisos falsos. */
    if (im.complete && im.naturalWidth === 0) out.imgsRotas.push(im.getAttribute("src"));
    else if (!im.complete) out.imgsLentas = (out.imgsLentas || 0) + 1;
    if (!im.getAttribute("alt")) out.imgsSinAlt.push(im.getAttribute("src"));
  }

  // ids repetidos en todo el documento (también en las rutas ocultas)
  var vistos = {}, rep = {};
  var conId = document.querySelectorAll("[id]");
  for (var k=0;k<conId.length;k++){
    var id = conId[k].id;
    if (vistos[id]) rep[id] = true; else vistos[id] = true;
  }
  out.idsRepetidos = Object.keys(rep);

  // Campos sin nombre accesible, en la ruta visible
  out.camposSinNombre = [];
  var campos = document.querySelectorAll("input,select,textarea,button");
  for (var m=0;m<campos.length;m++){
    var c = campos[m];
    if (c.offsetParent === null) continue;
    var nombre = c.getAttribute("aria-label") ||
                 (c.getAttribute("aria-labelledby") ? "ref" : "") ||
                 (c.id && document.querySelector('label[for="'+CSS.escape(c.id)+'"]') ? "label" : "") ||
                 (c.closest("label") ? "envuelto" : "") ||
                 (c.textContent || "").trim() ||
                 c.getAttribute("title") || "";
    if (!nombre) out.camposSinNombre.push(c.tagName.toLowerCase() + (c.id ? "#"+c.id : "") + "[" + (c.type||"") + "]");
  }

  // Menú lateral recortado
  var lat = document.getElementById("appLateral");
  out.menuRecortado = false;
  if (lat && getComputedStyle(lat).transform === "none" && lat.offsetParent !== null)
    out.menuRecortado = lat.scrollHeight - lat.clientHeight > 4;

  // Fuga de idioma: letras latinas sueltas dentro del árabe visible.
  // Los precios, los códigos y lo marcado .ltr o [dir=ltr] no cuentan.
  out.fugas = [];
  if (doc.lang === "ar" && vis){
    var and = document.createTreeWalker(vis, NodeFilter.SHOW_TEXT);
    var nodo;
    while ((nodo = and.nextNode())){
      var padre = nodo.parentElement;
      if (!padre || padre.offsetParent === null) continue;
      if (padre.closest('.ltr,[dir="ltr"],code,.mono')) continue;
      var txt = (nodo.nodeValue || "").trim();
      /* Una fuga es una PALABRA latina dentro del árabe. Una sigla en
         mayúsculas —HTML, CSS, PDF, JNTO— no lo es: en árabe técnico se
         escribe así a propósito, igual que las unidades y los nombres de
         marca. El filtro exige por tanto alguna minúscula. */
      var m2 = txt.match(/[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}/g);
      if (m2){
        var limpias = m2.filter(function(w){
          if (w === w.toUpperCase()) return false;          // sigla
          return PERMITIDAS.indexOf(w) < 0;
        });
        if (limpias.length) out.fugas.push(limpias.slice(0,3).join(" "));
      }
    }
    out.fugas = out.fugas.slice(0, 5);
  }

  out.alto = document.body.scrollHeight;
  var mainEl = document.getElementById("app");
  out.main = mainEl ? Math.round(mainEl.getBoundingClientRect().width) + "x" +
                      Math.round(mainEl.getBoundingClientRect().height) : "?";
  return out;
})()
'''


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(2)
    archivo = os.path.join(BASE, args[0])
    if not os.path.exists(archivo):
        sys.exit(f'no existe: {archivo}')
    anchos = [1440, 1100, 820, 600]
    if '--anchos' in args:
        anchos = [int(x) for x in args[args.index('--anchos') + 1].split(',')]

    # Palabras latinas que SÍ pueden aparecer dentro del árabe: unidades,
    # nombres propios de producto y órdenes de terminal. Las siglas en
    # mayúsculas ya se descartan solas.
    permitidas = ['km', 'kWh', 'kWp']
    if '--permitir' in args:
        permitidas += [x.strip() for x in args[args.index('--permitir') + 1].split(',')]

    rutas = json.loads(subprocess.run(
        [sys.executable, '-c', RUTAS_PY, archivo], capture_output=True, text=True, check=True).stdout)
    # Las páginas de una sola hoja no tienen rutas: se mide la página entera.
    una_hoja = not rutas
    if una_hoja:
        rutas = ['']

    perfil = '/tmp/.chrome-sonda-marsa'
    proc = subprocess.Popen(
        [CHROME, '--headless=new', f'--remote-debugging-port={PUERTO}',
         f'--user-data-dir={perfil}', '--disable-gpu', '--no-first-run',
         '--no-default-browser-check', '--hide-scrollbars', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fallos = 0
    try:
        ws = WS(espera_chrome(PUERTO))
        n = [0]

        def llama(metodo, **params):
            n[0] += 1
            ws.enviar({'id': n[0], 'method': metodo, 'params': params})
            while True:
                msg = ws.recibir()
                if msg.get('id') == n[0]:
                    if 'error' in msg:
                        raise RuntimeError(f'{metodo}: {msg["error"]}')
                    return msg.get('result', {})

        def ev(expr):
            r = llama('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
            if 'exceptionDetails' in r:
                raise RuntimeError(r['exceptionDetails'].get('text', 'error en la página'))
            return r['result'].get('value')

        llama('Page.enable'); llama('Runtime.enable')

        print(f'{len(rutas)} rutas × 3 idiomas × {len(anchos)} anchos = '
              f'{len(rutas)*3*len(anchos)} medidas\n')
        for ancho in anchos:
            llama('Emulation.setDeviceMetricsOverride', width=ancho, height=900,
                  deviceScaleFactor=1, mobile=False)
            for idioma in ('es', 'en', 'ar'):
                peor = {'desborde': 0}
                aviso = []
                for ruta in rutas:
                    llama('Page.navigate',
                          url=f'file://{archivo}' + (f'#/{ruta}' if ruta else ''))
                    espera_listo(ev)
                    ev(f'aplicar("{idioma}")')
                    time.sleep(0.25)
                    d = ev(MEDIR.replace('__PERMITIDAS__', json.dumps(permitidas)))
                    if d['lang'] != idioma:
                        aviso.append(f'{ruta}: el idioma no cambió ({d["lang"]})'); fallos += 1
                    if d['desborde'] > peor['desborde']:
                        peor = dict(d, ruta=ruta)
                    for campo, etiqueta in (('imgsRotas', 'imagen rota'),
                                            ('imgsSinAlt', 'imagen sin alt'),
                                            ('idsRepetidos', 'id repetido'),
                                            ('camposSinNombre', 'campo sin nombre'),
                                            ('fugas', 'fuga de idioma')):
                        for v in d.get(campo, []):
                            aviso.append(f'{ruta}: {etiqueta} · {v}'); fallos += 1
                    if d.get('menuRecortado'):
                        aviso.append(f'{ruta}: menú lateral recortado'); fallos += 1
                if peor['desborde'] > 0:
                    fallos += 1
                    detalle = ', '.join(f'{c["sel"]} +{c["px"]}px' for c in peor.get('culpables', []))
                    aviso.insert(0, f'{peor["ruta"]}: desborde {peor["desborde"]}px · {detalle}')
                estado = '✔' if not aviso else '✗'
                print(f'{estado} {ancho:>4}px · {idioma}  desborde máx {peor["desborde"]}px')
                for a in dict.fromkeys(aviso):
                    print(f'      {a}')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print('\n' + ('todo en verde ✔' if not fallos else f'{fallos} avisos ✗'))
    sys.exit(0 if not fallos else 1)


RUTAS_PY = r'''
import re, sys, json
s = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"var RUTAS\s*=\s*\[(.*?)\]", s, re.S)
print(json.dumps([x for x in re.findall(r'"([a-z0-9\-]+)"', m.group(1))] if m else []))
'''

if __name__ == '__main__':
    main()
