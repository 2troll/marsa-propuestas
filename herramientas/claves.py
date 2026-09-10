#!/usr/bin/env python3
"""Comprueba los diccionarios de idioma de un sitio de un solo archivo.

Tres comprobaciones, y las tres han hecho falta alguna vez:

  1. Paridad: las mismas claves en es, en y ar. Una clave que falta deja el
     texto en el idioma anterior sin avisar de nada.
  2. Claves usadas en el HTML (`data-t`, `data-t-attr`) que no existen en el
     diccionario. La paridad sola NO las detecta.
  3. Claves duplicadas dentro de un mismo diccionario: JavaScript se queda con
     la última y la primera desaparece en silencio. Así se perdió una vez la
     página de Método entera por un prefijo repetido.

    python3 herramientas/claves.py marsa.html [otro.html ...]
"""
import os, re, sys

IDIOMAS = ("es", "en", "ar")


def bloque_de(s, cod):
    """Devuelve el texto del diccionario `cod` dentro de `var T = {...}`."""
    ini = s.index("var T = {")
    m = re.search(r'^%s\s*:\s*\{' % cod, s[ini:], re.M)
    if not m:
        raise SystemExit(f'no encuentro el diccionario «{cod}»')
    j = arranque = ini + m.end() - 1
    prof = 0
    while True:
        c = s[j]
        if c == '"':
            j += 1
            while s[j] != '"' or s[j - 1] == '\\':
                j += 1
        elif c == '{':
            prof += 1
        elif c == '}':
            prof -= 1
            if prof == 0:
                break
        j += 1
    return s[arranque + 1:j]


def claves(bloque):
    """Claves de primer nivel, en orden y con repeticiones."""
    out, prof, k = [], 0, 0
    while k < len(bloque):
        c = bloque[k]
        if c == '"':
            k += 1
            while bloque[k] != '"' or bloque[k - 1] == '\\':
                k += 1
        elif c in '{[':
            prof += 1
        elif c in '}]':
            prof -= 1
        elif prof == 0 and (k == 0 or bloque[k - 1] in ' \n,'):
            m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', bloque[k:])
            if m:
                out.append(m.group(1))
                k += m.end() - 1
        k += 1
    return out


def revisar(ruta):
    s = open(ruta, encoding='utf-8').read()
    listas = {c: claves(bloque_de(s, c)) for c in IDIOMAS}
    conj = {c: set(v) for c, v in listas.items()}
    fallos = []

    print(f'{os.path.basename(ruta)}: ' +
          '  '.join(f'{c}={len(conj[c])}' for c in IDIOMAS))

    for c in IDIOMAS:
        rep = sorted({k for k in listas[c] if listas[c].count(k) > 1})
        if rep:
            fallos.append(f'  ✗ {c}: claves repetidas — {", ".join(rep)}')

    for otro in IDIOMAS[1:]:
        d = (conj['es'] - conj[otro]) | (conj[otro] - conj['es'])
        if d:
            fallos.append(f'  ✗ paridad es-{otro}: {", ".join(sorted(d))}')

    usadas = set(re.findall(r'data-t="([A-Za-z0-9_]+)"', s))
    for m in re.findall(r'data-t-attr="([^"]+)"', s):
        for par in m.split(','):
            usadas.add(par.split(':')[1].strip())
    faltan = sorted(k for k in usadas if k not in conj['es'])
    if faltan:
        fallos.append(f'  ✗ usadas en el HTML y sin definir: {", ".join(faltan)}')

    vacias = [c for c in IDIOMAS
              if any(v == '' for v in re.findall(r':\s*"([^"]*)"', bloque_de(s, c)))]
    if vacias:
        fallos.append(f'  ✗ traducciones vacías en: {", ".join(vacias)}')

    for f in fallos:
        print(f)
    if not fallos:
        print(f'  ✔ paridad, {len(usadas)} claves usadas en el HTML, ninguna sin definir')
    return len(fallos)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    total = sum(revisar(a if os.path.isabs(a) else os.path.join(base, a))
                for a in sys.argv[1:])
    sys.exit(0 if total == 0 else 1)
