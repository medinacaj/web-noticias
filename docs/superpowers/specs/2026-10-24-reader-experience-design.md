# Experiencia de lectura de Noticias del Momento

El usuario delegó la elección de UI/UX y autorizó mejorar navegación, cabecera, actualidad, cultura, tarjetas y firma. Se conserva el generador Python, sitio estático y componentes editoriales existentes.

## Dirección elegida
- Barra lateral de secciones visible por defecto desde 1024 px; botón para ocultarla y recordar la elección. En móvil, panel desplegable cerrado inicialmente, con cierre por Escape, enlace y fondo.
- Una sola cabecera persistente y compacta: monograma N, nombre accesible, actualización, búsqueda, favoritos, tema y opciones. Quitar el lema largo y el carrusel de navegación superior.
- «Lo último»: carrusel manual de hasta seis titulares recientes distintos; tres visibles en escritorio, dos en tablet y uno en móvil. Enlaces disponibles sin JS; controles accesibles, sin movimiento automático.
- Llevar los indicadores de cobertura al pie, dentro de detalles de edición plegados inicialmente.
- Tema automático según el sistema, con selección claro/oscuro/automático y persistencia; mantener la paleta de categorías y contraste.
- Botones redondeados de contorno suave, estados de foco y acciones legibles. Sin fotografía real, composición tipográfica y atribución en lugar de grandes placeholders; conservar los pósteres y fechas de eventos.
- Firma: un único enlace a https://www.linkedin.com/in/medinacaj/, target=_blank y rel=noopener noreferrer. «Diseñado por» tenue, @medinacaj destacado, emoji y flecha; cápsula oscura en claro y blanca en oscuro. URL deducida del identificador entregado; perfil no verificado por restricciones de red.
- Cultura: complementar la edición chilena existente con entretenimiento de ediciones internacionales en español, sin cuotas extra GNews, sin activar catálogos pendientes ni inventar permisos. Las nuevas entradas conservarán solo metadatos y pasarán por deduplicación y validación temporal.

## Alternativas
Carrusel manual recomendado frente al clima: útil para todos sin elegir ciudad, ubicación ni proveedor. Barra lateral plegable frente a doble navegación horizontal: reduce duplicación y movimiento. Tarjeta tipográfica frente a ilustraciones genéricas: evita atribuir una imagen ajena al hecho.

## Integración y límites
PR96 incorporado a la rama de trabajo en SHA 51578c6586a6e0fb08de11290e3f10d1452ad4ef; validado offline antes de cambios (307 + 99 pruebas). No modificar historial vivo ni publicar fixtures. La API GitHub está bloqueada por la política del entorno; no afirmar CI remota ni fusión. Las jurisdicciones y permisos editoriales no se certifican; las nuevas consultas usan la vía Google RSS existente y no habilitan medios restringidos.

## Aceptación
Suite Python y Node, pruebas de navegador reales de navegación/tema/carrusel/firma, generación offline, SEO, controles responsive 320/390/768/1024/1440 y capturas claro/oscuro. Mantener biblioteca, búsqueda, Agenda, favoritos y lectura sin JS.
