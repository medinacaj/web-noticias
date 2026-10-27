# Evaluación de diseño e interfaz de Web Noticias

Fecha: 26 de octubre de 2026. Petición y seguimiento: Issue #134.

El portal tiene una base coherente: papel cálido, tarjetas blancas, tema oscuro con superficies diferenciadas, categorías reconocibles y navegación persistente. La mejora con más valor es reducir la competencia entre controles, bloques de contexto y noticias. Añadir más componentes aumentaría el ruido sin resolver los problemas observados.

## Alcance y método

- Código publicado de `medinacaj/web-noticias`, base `e59663d`, y edición real del 26 de octubre, 07:16 hora de Chile: 157 noticias publicadas y 75 medios. Se incorporaron además los snapshots reales de Agenda: 19 eventos próximos en seis regiones.
- Ocho anchos: 320, 375, 390, 768, 1024, 1440, 1920 y 2560 px. Temas claro y oscuro; barra lateral abierta y plegada mediante las pruebas de interacción.
- Revisión visual de portada, secciones, menú móvil, búsqueda, preferencias y guardadas; contraste, lectura, foco, áreas de interacción, estados y recuperación de contexto.
- Chromium, axe-core 4.14.0 con reglas WCAG A/AA y pruebas funcionales existentes. Tipografías Inter y Source Serif 4 cargadas localmente para comprobar la geometría con las familias del sitio.
- Dos escenarios de imágenes: fallo de recursos externos y conservación de su espacio mediante rectángulos técnicos locales. Estos rectángulos se usan solo en QA; no se publican ni representan fotografías. La captura del usuario aporta la referencia de la portada con fotografía real.

La red del entorno bloquea el acceso directo a Pages y a los servidores de fotografías. Se reprodujeron localmente el código y el historial publicados; la publicación final se comprueba mediante GitHub Actions y el monitor del sitio. No se midieron Core Web Vitals de producción, ni se probó esta revisión en un iPhone físico o con VoiceOver. Esta evaluación combina pruebas técnicas y revisión heurística, sin atribuir resultados a estudios con usuarios que no se realizaron.

## Correcciones aplicadas

| Prioridad | Problema y evidencia | Cambio |
| --- | --- | --- |
| P2 | En escritorio aparecían hamburguesa y flecha para la misma acción. | Desde 1024 px se muestra únicamente la flecha. En móvil se conserva la hamburguesa para abrir el menú. |
| P2 | La flecha de 32 px y borde gris de 1 px se confundía con el límite lateral. | Flecha de 40 × 48 px, borde verde suave de 2 px, fondo tenue y área de interacción ampliada. Conserva el centro del borde y permanece visible al plegar. En móvil mantiene 44 × 44 px. |
| P1 | Con el menú móvil abierto se podía tabular hasta el contenido oculto detrás de la superposición. | El foco entra en las secciones al abrir. Al pasar con Tab al contenido, se cierra el menú y desaparece la superposición. Escape y la flecha devuelven el foco al control de apertura. |
| P1 | Cinco números pequeños de sección no alcanzaban 4,5:1 en modo claro. | Se ajusta solo el color del número, conservando la identidad de cada categoría y los colores de las tarjetas. |

Contraste medido de los números de sección sobre el fondo claro:

| Sección | Antes | Después |
| --- | ---: | ---: |
| Nacional | 3,93:1 | 5,05:1 |
| Deportes | 4,08:1 | 5,24:1 |
| Regiones | 4,29:1 | 5,32:1 |
| Política | 4,44:1 | 5,56:1 |
| Medioambiente | 3,73:1 | 4,75:1 |

Los diez números de las secciones de la edición comprobada quedan entre 4,75:1 y 7,40:1 en claro y entre 9,83:1 y 12,47:1 en oscuro. El ajuste procede de los tokens existentes, sin añadir una paleta nueva.

## Mejoras prioritarias de estructura

### 1. Plegar el seguimiento histórico y dar paso a las secciones — P2

En la edición revisada, «Seguimiento de publicaciones» muestra tres veces el mismo titular entre Destacadas y las secciones, con fechas históricas en UTC. El componente ocupa espacio de lectura sin explicar una evolución apreciable en ese ejemplo.

Recomendación: convertirlo en un bloque plegado de forma predeterminada o mostrarlo al consultar una noticia relacionada. La portada mantendría Portada → Destacadas → secciones. Si se conserva visible, exigir una diferencia informativa entre sus entradas y utilizar la misma presentación horaria de Chile que la cabecera. Esta propuesta no altera las fechas originales de las fuentes.

Con tipografías cargadas y espacio de fotografías reservado, la primera sección comienza aproximadamente en y=1937 px a 390 px de ancho y en y=1056 px a 1440 px. Es el resultado combinado de portada, destacadas y contexto; no se atribuye todo ese recorrido al seguimiento. Plegarlo es la primera intervención que conviene evaluar antes de reducir arbitrariamente todas las tarjetas.

### 2. Mostrar el modo de lectura activo en «Vista» — P2

El botón muestra «Compacta» cuando está activa la vista editorial, «Solo titulares» cuando está activa la compacta y «Editorial» cuando están activos los titulares. El texto describe la siguiente acción. En el mismo panel, Tema y Texto muestran sus valores actuales, por lo que existe una inconsistencia comprobable.

Recomendación: sustituir el ciclo por un selector que muestre el valor activo: Normal, Compacta o Solo titulares. Mantener la preferencia guardada y el resto del panel; no añadir un nuevo ajuste ni otra barra de controles.

### 3. Dar una proporción estable a las miniaturas — P2

Las imágenes de las tarjetas de sección tienen ancho de 104 px en escritorio y 92 px en móvil, pero se estiran al alto que determine cada titular. En noticias largas pueden convertirse en recortes verticales muy estrechos, aunque la fotografía original sea horizontal.

Recomendación: probar miniaturas de proporción estable, aproximadamente 4:3, alineadas al inicio, y reservar 16:9 para la fotografía principal. Comparar retratos, fotografías de grupo y titulares largos antes de fijar el recorte. Las fotos originales y sus enlaces se mantienen; las ausencias no deben sustituirse por imágenes que aparenten documentar el hecho.

## Mejoras de lectura e interacción

| Prioridad | Observación | Propuesta y criterio de aceptación |
| --- | --- | --- |
| P2 | La portada puede retrasar la atribución al medio en pantallas bajas. A 1440 px, en la geometría revisada, sus metadatos comienzan alrededor de y=759 px. | Ensayar una imagen principal algo menos alta en escritorio y tablet, conservando el titular completo. A 1366/1440 × 768 debería verse el medio sin desplazar la página en titulares habituales. Comparar también titulares excepcionalmente largos. |
| P2 | Guardar y compartir compiten con la etiqueta de categoría en cada tarjeta. Los nombres largos pueden envolver esa fila. | Probar la colocación de acciones junto a los metadatos o una fila compacta consistente. Mantener acceso directo y foco visible; no introducir un menú adicional para dos acciones ni esconderlas en móvil. |
| P2 | Algunas acciones de tarjeta tienen 36 px y varios controles de cabecera 36–40 px. El tamaño resulta menos cómodo para el pulgar. | Llevar los objetivos táctiles relevantes hacia 44 × 44 px, evitando áreas superpuestas y sin aumentar indiscriminadamente la altura de todas las tarjetas. Es una mejora de comodidad; el tamaño observado no implica por sí solo una infracción del mínimo WCAG 2.2 AA de 24 px. |
| P2 | La fecha de cabecera baja a 9 px en móvil; los metadatos de tarjetas son de 12 px. | Mantener Texto normal como valor inicial y probar fecha de 11 px y metadatos de 13 px con ajuste de línea. Validar especialmente 320 y 375 px para que no crezca la cabecera ni se pierdan controles. |
| P3 | «Vista» queda representado solo por un icono en parte del escritorio; su significado es menos inmediato que el de Buscar. | Comprobar si la etiqueta puede mostrarse desde un ancho menor sin romper la alineación. No añadir otra fila ni ensanchar la cabecera. |
| P3 | «Lo último» permite pausar mediante el propio rótulo y su tooltip, pero esa posibilidad puede pasar inadvertida. | Conservar el control integrado y el movimiento solicitado. Verificar con lectores que se entiende la pausa; no reintroducir botones de pausa/adelante/atrás, rechazados por el usuario. |
| P3 | El selector de tema usa glifos de luna/sol, mientras el resto de controles utiliza iconos de línea. | Unificar en una futura pasada con SVG del mismo peso visual y conservar los nombres accesibles. No cambiar su ubicación exterior al panel. |
| P3 | Las miniaturas genéricas del editor pueden confundirse con fotos de una noticia si el editor las declara como imagen social. | Revisar casos reales de imágenes repetidas o genéricas, conservando un respaldo discreto. No declarar que todo `og:image` es necesariamente una fotografía del hecho. |

## Comportamientos comprobados que conviene conservar

| Área | Evaluación |
| --- | --- |
| Alineación | Cabecera, franja de titulares, contenido y pie mantienen guías compartidas. No se detectó desborde horizontal entre 320 y 2560 px, ni con las tipografías cargadas. |
| Cabecera | Conserva 65 px de alto real en escritorio y 77 px en móvil/tablet, contando el borde. La fecha continúa a la derecha y el contador sigue visible. |
| Identidad y temas | El símbolo editorial es compacto. Las tarjetas se separan del fondo claro y del oscuro. El tema claro inicial y las preferencias manuales guardadas permanecen. |
| Navegación | La barra lateral permanece abierta por defecto en escritorio; la flecha pliega y reabre, conserva la preferencia y mantiene su centro vertical. Las categorías corresponden al contenido publicado. |
| Lectura | Texto normal y recientes por sección siguen siendo valores iniciales. El orden incluye la primera tarjeta. No se reintroducen líneas divisorias entre secciones. |
| Búsqueda | Se comprobaron combinaciones de texto, fuente y categoría, resultados vacíos, conteos y reapertura. Debe seguir siendo local, sin enviar las consultas del lector. |
| Guardadas | Las acciones y el panel conservan su estado y funcionamiento. No conviene añadir cuentas, gamificación o recordatorios para resolver los problemas de interfaz observados. |
| Volver al portal | Los enlaces a noticias siguen en la misma pestaña; las pruebas de Atrás conservan contexto, filtros, expansión y posición. |
| Movimiento | La franja conserva deslizamiento, pausa por interacción y navegación por teclado. Movimiento reducido evita el avance automático. |
| Agenda | Sus 19 eventos se comprobaron adicionalmente a 390, 768 y 1440 px, en ambos temas, con navegación y filtros combinados de región y gratuidad. |
| Pie y archivo | Mantener el pie breve, la firma y el acceso al archivo de siete días. No duplicar fecha, contador o navegación principal. |
| Fallos y accesibilidad | Controles operativos con almacenamiento bloqueado; enlaces y lectura disponibles sin depender de las fotos. Se mantienen enlaces de salto, nombres accesibles y foco visible. |

## Verificación y límites de las conclusiones

- Suite del proyecto: 351 pruebas aprobadas.
- Chromium: 44 pruebas aprobadas, incluidas plegado/reapertura, persistencia, móvil, teclado, Atrás, temas, filtros, orden y guías compartidas.
- La revisión independiente añadió dos verificaciones: reabrir un menú desplazado en móvil horizontal mantiene el foco visible, y el área efectiva de la flecha alcanza 44 px también al plegarla contra el borde de la pantalla. Ambas se reproducen antes y después de la corrección.
- Matriz geométrica: ocho anchos × dos temas; sin desbordes, con Inter y Source Serif 4 cargadas localmente. Las capturas de portada y de paneles se revisaron junto con la captura del usuario.
- Axe: antes había cinco infracciones de contraste, reproducidas en claro a 390 y 1440 px. Después no detectó infracciones en las cuatro combinaciones de tema y esos anchos.
- Axe también devuelve comprobaciones de contraste inconclusas: entre 108 y 130 nodos en la matriz sin recursos externos, principalmente por fondos afectados por pseudoelementos o glifos. «Sin infracciones detectadas» no equivale a certificar conformidad total. Se midieron adicionalmente los números de sección; las pruebas existentes comprueban texto y metadatos de tarjetas en ambos temas.
- No hay mediciones válidas de LCP, CLS o INP de producción en esta revisión. Antes de una optimización de rendimiento deben medirse en el sitio real con imágenes, fuentes, red móvil y caché normales. Los tiempos locales no se presentan como velocidad real del portal.
- Queda pendiente una comprobación breve en Safari/iPhone y VoiceOver con el menú, las preferencias y Atrás. La emulación responsive no sustituye a ese dispositivo.

## Orden recomendado de continuación

1. Plegar el seguimiento histórico y probar el recorrido hasta las primeras secciones.
2. Hacer explícito el modo activo en «Vista».
3. Prototipar una sola mejora de tarjetas que combine miniatura estable, acciones y objetivos táctiles.
4. Afinar portada y metadatos según esos resultados, preservando la cabecera compacta y las guías existentes.
5. Validar Safari/VoiceOver y medir rendimiento de producción antes de añadir funciones o componentes.

Los cambios publicados en esta entrega se limitan al control del menú, su visibilidad, la navegación por teclado y el contraste de los números. Las demás filas son recomendaciones evaluadas, no funcionalidades que se declaren implementadas.

## Aplicación autorizada de las recomendaciones — 27 de octubre de 2026

El usuario pidió aplicar las mejoras sugeridas (Issue #137). El seguimiento pasa a un desplegable cerrado inicialmente, accesible con teclado y sin JavaScript, con fechas de Chile y valores `datetime` intactos. «Vista» muestra el modo actual mediante un selector nativo, compatible con las preferencias anteriores.

Las fotografías de sección usan miniaturas 4:3 estables; las fichas gráficas de país y fecha son cuadradas para no cortar sus textos. Guardar y compartir pasan a un pie de tarjeta con los metadatos, fuera de las categorías, con botones independientes de 44×44 px. La portada se alinea arriba en lugar de estirarse al alto de Destacadas, y limita su imagen a 280 px en escritorio/tablet; móvil mantiene 16:9. Los metadatos tienen 13 px y la actualización móvil 11 px. Se conserva la cabecera de 65/77 px reales, las guías y los temas. En móviles estrechos se priorizan el nombre en dos líneas y controles separados de 36/40 px de ancho por 44 px de alto; forzar cinco botones de 44 px de ancho no cabe junto a la marca a 320 px. «Vista» presenta etiqueta desde 1180 px y el tema usa SVG de línea también en el archivo.

En la misma geometría y edición del informe, con las fuentes cargadas y las imágenes reservadas, la atribución de portada a 1440 px pasa de aproximadamente y=759 a y=657; la primera sección queda alrededor de y=909 (antes y=1056). A 390 px pasa de y=1937 a y=1439 aproximadamente. Son medidas locales de recorrido, no métricas de rendimiento real.

La pausa sigue integrada en «Lo último», con foco, nombre accesible y ayuda al pasar el cursor. No se añaden los controles que el usuario rechazó. Se conserva la protección ante imágenes repetidas; no se incorpora un clasificador especulativo de fotografías genéricas. La disponibilidad y pertinencia de cada imagen depende de lo que declare el editor. Safari/iPhone, VoiceOver y las métricas de producción continúan como comprobaciones que requieren el dispositivo o datos reales; no se presentan como realizadas.
