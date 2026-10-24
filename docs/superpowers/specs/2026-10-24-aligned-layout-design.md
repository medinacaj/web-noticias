# Cuadrícula y cabecera alineadas

El usuario detecta que se alargó la cabecera sin acompañar al contenido y exige que todo se alinee perfectamente. Causas confirmadas: `.bar-inner` eliminaba el max-width de `.container`, la cabecera tenía margen negativo para cubrir el lateral y la variante móvil había crecido a 96 px.

Corrección acotada sobre el diseño publicado:
- Una única anchura máxima de 1440 px y los mismos márgenes para cabecera, franja de última hora, contenido, boletín y pie. Ampliar también el contenido de pantallas grandes respecto a los 1240 px anteriores, conservando legibilidad de tarjetas.
- La zona de contenido de la cabecera se mide en la misma columna disponible que el cuerpo. Con lateral abierto, marca y tarjetas empiezan sobre la misma guía; el botón de menú permanece accesible en la zona superior del lateral. Al cerrarlo, todas las bandas se recentran juntas.
- Cabecera compacta: 64 px en escritorio y 76 px en móvil/tablet, más el borde. Conservar fecha a la derecha, contador, botones y menú sin recortes ni solapamientos. Ajustar el lateral a la altura real de la cabecera.
- Unificar a 16 px las separaciones entre tarjetas para que Destacadas y las secciones compartan columnas cuando usan la misma cantidad de columnas.
- Mantener paleta, autoplay/pausa, firma y pie compacto. Sin cambios de fuentes, datos ni workflows.

Validación geométrica en 320/390/768/1024/1440/1920/2560 px, lateral abierto/cerrado, altura, alineación de bordes interiores, fecha y controles. Revisar capturas de portada real generada por el despliegue si está disponible; usar fuente de la versión publicada como respaldo. Suite, QA, revisión independiente, CI y publicación bajo la autorización vigente.
