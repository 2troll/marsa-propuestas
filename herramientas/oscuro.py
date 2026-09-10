#!/usr/bin/env python3
"""Busca reglas de modo oscuro escritas fuera de su @media.

`:root:not([data-theme="light"])` es la forma correcta de decir «oscuro por
defecto del sistema», pero SÓLO dentro de `@media (prefers-color-scheme:dark)`.
Suelta casa también cuando no hay atributo ninguno —es decir, en modo claro— y
además pesa más que dos clases, así que gana a casi todo.

Ese descuido dejó tres portadas con el titular blanco sobre fondo claro. No lo
ve ninguna otra comprobación: la maquetación está bien, las claves están bien,
y la página es ilegible.

    python3 herramientas/oscuro.py <sitio.html> [otro.html ...]
"""
import os, re, sys


def revisar(ruta):
    s = open(ruta, encoding='utf-8').read()
    if '<style>' not in s:
        print(f'{os.path.basename(ruta)}: sin hoja de estilos')
        return 0
    css = s[s.index('<style>'):s.index('</style>')]

    # tramos del CSS cubiertos por un @media de prefers-color-scheme
    cubierto = []
    for m in re.finditer(r'@media[^{]*prefers-color-scheme[^{]*\{', css):
        j, prof = m.end(), 1
        while prof and j < len(css):
            if css[j] == '{':
                prof += 1
            elif css[j] == '}':
                prof -= 1
            j += 1
        cubierto.append((m.start(), j))

    malas = []
    for m in re.finditer(r':root:not\(\[data-theme="light"\]\)', css):
        if not any(a <= m.start() < b for a, b in cubierto):
            linea = s[:s.index('<style>') + m.start()].count('\n') + 1
            regla = css[m.start():css.find('{', m.start())].strip()
            malas.append((linea, regla))

    nombre = os.path.basename(ruta)
    if malas:
        for linea, regla in malas:
            print(f'  ✗ {nombre}:{linea}  {regla}  — fuera de su @media')
    else:
        print(f'  ✔ {nombre}')
    return len(malas)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    total = sum(revisar(a) for a in sys.argv[1:])
    print('\n' + ('ninguna regla de oscuro suelta ✔' if not total
                  else f'{total} reglas sueltas ✗'))
    sys.exit(0 if not total else 1)
