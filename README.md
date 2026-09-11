# Cuatro propuestas de marca — consultora de viajes privados

Cuatro sitios completos y distintos para la misma empresa, cada uno en
**español, inglés y árabe** con maquetación invertida real (RTL) en la versión
árabe. HTML, CSS y JavaScript planos: sin compilar, sin dependencias, sin
claves de API.

**Ver online:** https://2troll.github.io/marsa-propuestas/

| Propuesta | Concepto | Tipografía |
|---|---|---|
| [**MARSA**](marsa.html) | Diez páginas, con tres herramientas que funcionan: calendario hiyrí calculado en el navegador, una jornada comparada y los niveles reales de «halal» | Bodoni Moda · Karla · Reem Kufi · IBM Plex Sans Arabic |
| [**DIWAN**](diwan.html) | Página de manuscrito: caja centrada, epígrafes rubricados en rojo y friso de estrellas de ocho puntas generado por trigonometría | Spectral · Amiri |
| [**MERIDIANO**](meridiano.html) | Retícula suiza de doce columnas a la vista, cifras tabulares, reloj de husos en vivo y fotografía a sangre en la banda inferior | Archivo · IBM Plex Mono · IBM Plex Sans Arabic |
| [**NAWA**](nawa.html) | Nocturna. Mapa de estrellas calculado en canvas con posiciones deterministas y líneas de constelación | Fraunces · Manrope · Aref Ruqaa · Tajawal |

## Cada una resuelve el bilingüismo por una vía distinta

Ese es el argumento técnico de la propuesta, y por eso las cuatro no se parecen:

- **MARSA** — propiedades lógicas de CSS (`margin-inline-start` en vez de
  `margin-left`) más nueve excepciones documentadas una a una, que son los
  sitios donde el árabe necesita algo distinto y no sólo el reflejo.
- **DIWAN** — caja de texto **centrada**. Se lee igual en los dos sentidos, así
  que la versión árabe no es una adaptación de la española.
- **MERIDIANO** — el sistema es la **retícula**. Mandan las columnas, no la
  dirección de lectura.
- **NAWA** — composición **asimétrica** anclada al margen exterior, que se
  refleja entera al pasar a árabe.

## Detalles que un lector nativo sí nota

- **Concordancia de número en árabe**: 1 singular, 2 dual, de 3 a 10 plural
  (`٤ أيام`), y de 11 en adelante singular acusativo (`٤٧ يومًا`). Escribir
  `٤ يومًا` es lo que delata una traducción automática.
- **Dígitos árabe-índicos** pedidos explícitamente (`ar-u-nu-arab`): la
  configuración por defecto de `ar` devuelve dígitos latinos.
- **`letter-spacing: 0`** en todos los rótulos árabes: espaciar las letras
  rompe las ligaduras y descose la palabra.
- **Correo y teléfono en LTR** dentro de páginas RTL, o los puntos salen al
  revés.
- **`background-position` reflejada a mano** en los desplegables: es la única
  propiedad del formulario que no tiene versión lógica.

## Comprobaciones

```
paridad de claves es/en/ar   ✔ en las cuatro
claves sin traducir          0
contraste de texto           AA en tema claro y oscuro
HTML                         doctype, html/head/body, sin etiquetas sin cerrar
formularios                  tres estados por idioma
calendario hiyrí             1 Ramadán 1447 = 19/02/2026, fecha real
paleta del gráfico           los seis controles, en claro y en oscuro
```

---

**Estas páginas son maquetas de propuesta.** No son el sitio público de ninguna
empresa y llevan `noindex` para que no se indexen como si lo fueran.
