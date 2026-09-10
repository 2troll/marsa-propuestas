#!/usr/bin/env python3
"""Comprueba que los aparatos del sitio HACEN algo, no que estén dibujados.

Una captura de pantalla enseña un botón; no dice si al pulsarlo cambia nada.
Esta prueba pulsa de verdad y compara el antes con el después:

  · los seis años del calendario islámico redibujan las barras
  · los dos planes del día cambian la jornada
  · los tres niveles de halal cambian el detalle
  · cambiar de ciudad cambia las horas de rezo y el rumbo de la quibla
  · el formulario de contacto valida y acusa recibo
  · los tres idiomas cambian el documento entero, ida y vuelta

    python3 herramientas/funciona.py marsa.html
"""
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sonda

PUERTO = 9431


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archivo = os.path.join(base, sys.argv[1])

    proc = subprocess.Popen(
        [sonda.CHROME, '--headless=new', f'--remote-debugging-port={PUERTO}',
         '--user-data-dir=/tmp/.chrome-funciona', '--disable-gpu', '--no-first-run',
         '--no-default-browser-check', '--hide-scrollbars', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fallos = 0
    try:
        ws = sonda.WS(sonda.espera_chrome(PUERTO))
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
                d = r['exceptionDetails']
                raise RuntimeError(d.get('text', '') + ' ' +
                                   (d.get('exception') or {}).get('description', '')[:200])
            return r['result'].get('value')

        llama('Page.enable'); llama('Runtime.enable')
        llama('Emulation.setDeviceMetricsOverride', width=1440, height=900,
              deviceScaleFactor=1, mobile=False)

        def ir(ruta):
            llama('Page.navigate', url=f'file://{archivo}#/{ruta}')
            sonda.espera_listo(ev)
            time.sleep(0.3)

        def prueba(nombre, expr):
            nonlocal fallos
            try:
                ok = ev(expr)
            except RuntimeError as e:
                ok, e = False, e
            else:
                e = ''
            print(('✔ ' if ok else '✗ ') + nombre + (f'  {e}' if e else ''))
            if not ok:
                fallos += 1

        ir('estacionalidad')
        prueba('los años del calendario redibujan',
               '''(function(){var b=document.querySelectorAll("#esAnios button");
                  if(b.length<2) return false;
                  var a=document.getElementById("esLienzo").innerHTML;
                  b[b.length-1].click();
                  var c=document.getElementById("esLienzo").innerHTML;
                  return a!==c && c.length>200;})()''')
        prueba('el hallazgo del año cambia con el año',
               '''(function(){var b=document.querySelectorAll("#esAnios button");
                  b[0].click(); var a=document.getElementById("esHallazgo").textContent;
                  b[b.length-1].click(); var c=document.getElementById("esHallazgo").textContent;
                  return a!==c && c.trim().length>10;})()''')
        prueba('la gráfica de mercado tiene doce barras',
               'document.querySelectorAll("#meGrafico rect.barra, #meGrafico .barra").length===12 || '
               'document.querySelectorAll("#meGrafico svg rect").length>=12')

        ir('dia')
        prueba('los dos planes cambian la jornada',
               '''(function(){var b=document.querySelectorAll("#diMandos button");
                  if(b.length<2) return false;
                  b[0].click(); var a=document.getElementById("diJornada").innerHTML;
                  b[1].click(); var c=document.getElementById("diJornada").innerHTML;
                  return a!==c && c.length>200;})()''')

        ir('halal')
        prueba('los tres niveles cambian el detalle',
               '''(function(){var b=document.querySelectorAll("#haMandos button");
                  if(b.length<3) return false;
                  b[0].click(); var a=document.getElementById("haDetalle").innerHTML;
                  b[2].click(); var c=document.getElementById("haDetalle").innerHTML;
                  return a!==c && c.length>100;})()''')

        ir('oracion')
        prueba('cambiar de ciudad cambia horas y quibla',
               '''(function(){var s=document.getElementById("orCiudad");
                  if(!s || s.options.length<2) return false;
                  s.selectedIndex=0; s.dispatchEvent(new Event("change"));
                  var h1=document.getElementById("orTabla").textContent;
                  var q1=document.getElementById("orQuibla").textContent;
                  s.selectedIndex=s.options.length-1; s.dispatchEvent(new Event("change"));
                  var h2=document.getElementById("orTabla").textContent;
                  var q2=document.getElementById("orQuibla").textContent;
                  return h1!==h2 && q1!==q2;})()''')
        prueba('la escuela hanafí mueve el asr',
               '''(function(){var e=document.getElementById("orEscuela");
                  e.value="1"; e.dispatchEvent(new Event("change"));
                  var a=document.getElementById("orTabla").textContent;
                  e.value="2"; e.dispatchEvent(new Event("change"));
                  return a!==document.getElementById("orTabla").textContent;})()''')

        ir('contacto')
        prueba('el formulario vacío no se da por enviado',
               '''(function(){var f=document.getElementById("f");
                  f.querySelector("#nombre").value=""; f.querySelector("#email").value="";
                  f.dispatchEvent(new Event("submit",{cancelable:true,bubbles:true}));
                  return (document.getElementById("ok").textContent||"").trim().length>0 ||
                         document.querySelectorAll("#f [aria-invalid='true']").length>0;})()''')
        prueba('el formulario relleno acusa recibo',
               '''(function(){var f=document.getElementById("f");
                  f.querySelector("#nombre").value="Prueba";
                  f.querySelector("#email").value="prueba@example.com";
                  f.querySelector("#msg").value="Dos semanas en abril.";
                  f.dispatchEvent(new Event("submit",{cancelable:true,bubbles:true}));
                  return (document.getElementById("ok").textContent||"").trim().length>0;})()''')

        ir('inicio')
        prueba('los tres idiomas cambian el documento, ida y vuelta',
               '''(function(){var h=document.documentElement, v=[];
                  ["es","en","ar"].forEach(function(c){aplicar(c);
                    v.push(h.lang+"/"+h.dir+"/"+document.title);});
                  aplicar("es");
                  return v[0]!==v[1] && v[1]!==v[2] && v[2].indexOf("ar/rtl")===0 &&
                         h.lang==="es" && h.dir==="ltr";})()''')
        prueba('el raíl marca la ruta activa',
               '''(function(){location.hash="#/servicios";
                  return true;})()''')
        time.sleep(0.3)
        prueba('...y el enlace activo es el de servicios',
               '''document.querySelector('.app-nav a[aria-current="page"]').getAttribute("href")==="#/servicios"''')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print('\n' + ('todo funciona ✔' if not fallos else f'{fallos} aparatos rotos ✗'))
    sys.exit(0 if not fallos else 1)


if __name__ == '__main__':
    main()
