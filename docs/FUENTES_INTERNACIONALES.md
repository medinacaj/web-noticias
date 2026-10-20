# Fuentes de referencia global — ampliación de cobertura

**Alcance:** edición internacional de Noticias del Momento. El objetivo no es agregar indiscriminadamente RSS chilenos, sino reflejar actualidad de Europa, América, Asia, África y Oriente Medio desde medios reconocidos. No modifica el menú, número de tarjetas por sección ni la presentación móvil.

## Fuentes añadidas mediante descubrimiento acotado de Google Noticias

| Medio | Región de referencia | Idioma de origen |
| --- | --- | --- |
| Reuters | Cobertura mundial | inglés |
| Associated Press (AP) | Mundial y América | inglés |
| Al Jazeera English | Oriente Medio, África, Asia | inglés |
| NHK World-Japan | Japón y Asia-Pacífico | inglés |
| The Guardian (solo descubrimiento, no RSS directo) | Europa y política mundial | inglés |
| NPR World | Estados Unidos e internacional | inglés |
| Deutsche Welle (DW) | Europa y mundo | español |
| France 24 | Europa, África y mundo | español |
| CNN en Español | América y mundo | español |
| El País Internacional | Europa y América | español |
| Euronews Español | Europa y mundo | español |

La edición ya conserva un feed RSS **directo** de BBC News Mundo. No se requiere acceso privilegiado a editores para generar búsquedas RSS de Google Noticias. Solo se enlaza a artículos originales encontrados y atribuidos a dominios pertenecientes a cada medio. **No** se obtienen artículos completos ni se traducen titulares con IA.

### Controles

- Solo se consulta la sección `internacional`; las categorías nacionales, regionales y temáticas existentes continúan sin cambios.
- Máximo **4 noticias recientes por medio y ejecución**; como máximo 11 consultas adicionales a Google Noticias por hora. Cada consulta se limita a publicaciones de las últimas 24 horas y puede devolver menos o ningún resultado. La cobertura real depende del servicio externo; **las 11 fuentes no se dan por activas en cada hora**.
- Para aceptar un resultado, el RSS debe aportar título, fecha, enlace y un `<source url>` HTTPS cuya raíz corresponda exactamente al dominio autorizado (o a un subdominio auténtico). No confiar únicamente en el texto del título o nombre del editor.
- Cada fallo independiente se registra sin bloquear otros medios ni la generación de la portada.
- Evitar duplicados por URL exacta incluso cuando una fuente publica un titular nuevo para el mismo enlace. Se conserva el primer titular y se suman medios pertinentes.
- Los titulares pueden estar en inglés si son de medios sin edición en español. No asignar falsas traducciones.
- No insertar logos, módulos comerciales, buscadores nuevos ni espacio adicional en la interfaz. La sección muestra como antes máximo 24 noticias, con seis inicialmente visibles.

## Consideraciones comerciales y jurídicas abiertas

La integración está pensada como **selección de enlaces con atribución**, no como autorización general para reproducir titulares, extractos o fotografías con fines comerciales. Hay que revisar las condiciones pertinentes antes de la aprobación final para AdSense o cualquier uso comercial:

- Reuters no mantiene feeds RSS públicos activos; se usa descubrimiento por búsqueda, no URLs antiguas `feeds.reuters.com`.
- **The Guardian** limita sus feeds RSS publicados para uso personal/no comercial; no se consulta su RSS directo. Que exista un enlace en Google Noticias **no equivale** a licencia para republicar fotografías o resúmenes.
- DW ofrece distribución formal de material a terceros mediante acuerdos; no se consume un feed específico de socios que no se haya autorizado.
- AFP requiere servicios/condiciones de licencia para sus contenidos; **no** se agrega un feed no autorizado de AFP como si fuese libre.
- Las fotografías de editores requieren evaluación independiente de permisos. Continuar atribuyendo y enlazando a los originales no acredita licencias de redistribución de imágenes.
- Google puede modificar o restringir resultados y el procesamiento de Google Noticias RSS sin aviso. El recolector debe soportar resultados vacíos.

**Riesgo → evidencia → control → prueba → responsable → estado:** derechos/editorial → fuentes y condiciones identificadas → descubrimiento acotado, enlaces HTTPS y sin contenido íntegro → pruebas de dominios y cuotas → responsable del proyecto → **pendiente de revisión humana**. Según `docs/agent-workflow.md`, no fusionar automáticamente cambios que afecten a fuentes y condiciones de uso.

## Fuentes de verificación

- [The Guardian: política de RSS para uso personal y no comercial](https://www.theguardian.com/help/feeds)
- [DW: opciones de distribución para operadores web](https://amp.dw.com/en/news-from-germany/a-65919184)
- [Reuters: estado de feeds RSS antiguos (independiente)](https://feeder.co/es/knowledge-base/rss-content/reuters-rss-feeds/)
- [RSS de EL PAÍS Internacional (seguimiento)](https://feeder.co/discover/500cfc4da2/elpais-com-rss-internacional-portada-xml)
- [BBC Mundo RSS existente](https://feeds.bbci.co.uk/mundo/rss.xml)
