# Validación de navegador · 24 de octubre de 2026

Base de la corrección: `main@3d8642ed7a574d5df874e3fabccfa38d0e70b628`.
Se examinó el portal publicado, edición `2026-10-24T01:13:38Z`, y una copia
local con la corrección. Chromium real, anchos 320, 375, 768, 1024 y 1440 px.
Las capturas se revisaron con agentes IA; no se afirma aceptación humana.

## Recorte del panel Opciones

A 320 px, el panel comenzaba en **x=-28 px** y sus controles en x=-12 px,
recortando título y etiquetas. El control previo de desbordamiento derecho no
detectaba el problema: `scrollWidth` seguía siendo 320 px.

La corrección ancla el panel a la fila de la barra en móvil, con márgenes
laterales, conservando el componente y el anclaje de escritorio. La regresión
de navegador falla antes del cambio y pasa después: panel **x=24..308** a
320 px y **x=75..359** a 375 px. Pasan los cinco anchos y texto al 200 % a
320/375 px. `scripts/visual_qa.py` comprueba ahora ambos bordes del panel.

## Siete criterios del sistema visual (#24)

| Criterio | Resultado observado |
| --- | --- |
| Jerarquía fotográfica | Portada y titulares jerarquizados, sin deformación visible en los cinco anchos. |
| Tipografía | Texto legible; panel corregido también cabe con texto aumentado al 200 %. |
| Composición de tarjetas | Secciones y vista compacta conservan su composición; QA comprueba la altura de las miniaturas. |
| Separación de secciones | Encabezados, espacios y divisores visibles. |
| Medios y fallback | Atribución legible; edición examinada con 147 figuras y 29 fallbacks, sin afirmar derechos de uso. |
| Responsive | Cinco anchos; recorte izquierdo confirmado, corregido y añadido a regresión. |
| Interacciones | Búsqueda, filtros, favoritos persistentes y cambio de vista funcionan; contratos de movimiento reducido/teclado conservados por la suite. |

La búsqueda y favoritos se ejercitaron en los cinco anchos, sin errores JS.
Sin JS a 375/1440 px se conservaron 179 enlaces de noticias y se ocultaron los
controles que requieren JS. No se infiere una evaluación estética humana de
animaciones ni adaptación a modo oscuro: la identidad vigente es clara.

## Comparador (#28)

La edición publicada no tenía botones Comparar, porque no había dos enlaces
directos verificables agrupados. Se probó el generador y su JS real con un
fixture local explícitamente sintético, dos medios `.example` y fechas/títulos
originales diferentes, servido en loopback HTTP. Ese fixture no se publica.

**Diez casos: cinco anchos por vista editorial/compacta.** Apertura con Enter,
foco inicial en Cerrar, Escape y restitución del foco al disparador aprobados.
Se preservan exactamente fuente, URL HTTPS, titular y fecha; la altura de la
tarjeta no cambia (delta menor que 1 px). Modal, atribución y foco resultan
legibles en las capturas examinadas.

La secuencia Tab pasa por BODY sólo cuando `document.hasFocus()` es false,
durante el paso al chrome del navegador; no enfoca controles de fondo. No se
considera un fallo. La elegibilidad de dos medios/HTTPS, exclusión de Google,
atribución y escape siguen cubiertos por `tests/test_coverage_comparison.py`.

La aceptación funcional utiliza datos sintéticos para el comparador y datos
reales para el resto; no acredita coberturas inexistentes en la edición viva.
El PR registra el SHA final, CI, publicación y comprobación posterior del panel.
