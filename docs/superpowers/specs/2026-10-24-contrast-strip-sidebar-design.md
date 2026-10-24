# Revisión visual: contraste, franja y control lateral

El usuario rechaza la predominancia azul y el aspecto monótono del PR98; pide colores modernos agradables, más separación de las tarjetas, «Lo último» nuevamente en una línea y una flecha visible en el borde lateral. Su delegación previa de las decisiones UI/UX sigue vigente. Esta revisión corrige esos puntos sobre la versión publicada sin cambiar fuentes, lógica editorial ni procesos de datos.

## Decisiones
- Paleta clara neutra cálida: fondo #F2F1ED, superficie #FAFAF7, tarjetas #FFFFFF, texto #282C30 y secundarios #626970. Acentos coral #C04C3E y verde #31584A; conservar identidad de categorías.
- Tema oscuro automático: fondo grafito #111315, superficies #1C1F23, tarjetas claramente más claras #343A43, texto #F7F6F2 y secundarios #C4C7CC. Bordes #66717D, acentos menta #B4DCC8 y coral suave. Evitar paneles azules grandes y sombras densas.
- Mantener tarjetas editoriales y su geometría, con elevación sutil y contraste de texto >=4.5:1; la luminancia de la tarjeta oscura debe separarse del fondo >=1.5:1.
- «Lo último»: una única línea de 52–60 px, titular truncado visualmente pero completo en el enlace y tooltip, antigüedad en escritorio y flechas manuales. Se conservan hasta seis noticias distintas, de una en una; swipe/teclado y lectura sin JS. Sin scrollbar visible ni bloque de tres columnas.
- Añadir control de borde con chevrón al lateral: pliega hacia la izquierda y permite abrir de nuevo desde el borde de la pantalla. Estado accesible sincronizado con el menú y persistido. En móvil, flecha para cerrar al abrir el panel; conservar Escape, fondo y enlaces.
- Armonizar logo, botones, boletín y pie con neutros y verde/coral; mantener firma LinkedIn y selección de temas.

## Alternativas descartadas
Forzar el tema claro ocultaría el problema en dispositivos oscuros. Mantener tres tarjetas de última hora conservaría el espacio excesivo que el usuario rechaza. Usar solo el botón hamburguesa no satisface su petición de una flecha en el borde.

## Validación y entrega
Pruebas reales de colores computados en ambos temas, altura de la franja en 320/390/768/1024/1440 px, un titular por paso, chevrón y persistencia, búsqueda y favoritos. Revisar capturas de escritorio/móvil en claro/oscuro. Suite Python/Node, generación, SEO, CI, PR y despliegue. No publicar fixtures ni modificar historial o workflows. El pedido de corrección se ejecuta y publica siguiendo el flujo ya autorizado de esta sesión.
