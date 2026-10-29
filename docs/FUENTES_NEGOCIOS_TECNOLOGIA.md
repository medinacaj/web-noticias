# Fuentes de negocios, innovación y tecnología

Ampliación solicitada por el usuario el 29-10-2026 (registro técnico UTC). `config/business_sources.json` conserva las 100 propuestas, 14 publicaciones similares y cinco ediciones de Forbes: 118 fichas en total. La interfaz conserva las secciones existentes Economía y negocios / Ciencia y tecnología.

## Qué acredita la revisión

Se contrastaron nombres, dominios, etiquetas de editor y muestras fechadas en respuestas reales del RSS de Google Noticias. 101 fichas tienen atribución directa del editor en ese índice; una es referencia parcial y 16 nombres siguen sin confirmar. Esto **no acredita** licencia, consentimiento editorial, acceso al sitio original, RSS propio ni indexación académica en bases científicas. Las fechas de las muestras proceden del RSS, no de una inspección del artículo.

La red del entorno sólo permite consultar el proveedor y determinados dominios ya autorizados. No se elude ese límite ni se interpreta el bloqueo del proxy como caída de un editor. No se incorporan feeds directos nuevos ni se simulan verificaciones que no se realizaron.

Correcciones respaldadas por el índice: Forbes Chile → `forbes.cl`; América Retail → `americaretail-malls.com`; Wayra → `wayra.com`; South Summit → `southsummit.io`; Gerencia → `gerencia.cl`; GridX como referencia institucional de `gridexponential.com`. En algunos casos se respalda el editor, pero no la URL concreta de la vertical solicitada; la consulta conserva el alcance por ruta cuando está acreditado en la búsqueda.

## Flujo y límites

`scripts/business_sources.py` amplía las búsquedas del **canal RSS Google Noticias que ya utiliza el portal**. El registro de identidades no sustituye los catálogos opt-in mundial/regional: se comprueban sus restricciones antes de planificar consultas y antes de aceptar cada resultado. No se marca ninguna autorización de editores como aprobada ni se activan fuentes pendientes/restringidas de esos catálogos. Tampoco se añaden las nuevas identidades como bloqueos generales de las rutas antiguas.

- Hasta 12 búsquedas agrupadas por ejecución, 12 dominios por búsqueda y tres solicitudes concurrentes. La configuración actual requiere nueve búsquedas; si se supera el presupuesto, las tandas rotan para evitar exclusión permanente.
- Se examinan como máximo 60 resultados por consulta; dos titulares por editor y 80 incorporaciones por ejecución, con una primera vuelta por editor para favorecer diversidad.
- Sólo titular, enlace, fecha original, editor y tipo de fuente. Ventana de 24 horas y tolerancia futura de 15 minutos; nunca renovar una noticia antigua por su fecha de descubrimiento.
- Validación de origen HTTPS y dominio/editor exacto; no promover recursos de otro subdominio como si fueran la redacción. Las cabeceras económicas generales requieren pertinencia tecnológica/empresarial.
- Sin artículos, traducciones, resúmenes, imágenes o cuotas GNews adicionales. No se consulta ningún portal del editor desde este colector. Las URLs ya presentes en la ingesta o historial no se sustituyen por las de descubrimiento.
- Instituciones y análisis se identifican como tales en el pie de su tarjeta. Las revistas académicas se ofrecen para consulta en el directorio, sin convertir estudios antiguos en titulares de actualidad.

La presencia de un medio en el directorio no garantiza que tenga noticias recientes o que se consulte en cada ejecución: siguen aplicándose las restricciones anteriores y la disponibilidad del proveedor. La publicación mantiene las fechas y enlaces que entrega el RSS; no atribuye autoría original del artículo ni permisos de republicación.

## Fuentes por confirmar o en revisión

Sin identidad suficiente: ProCommercio, Distrito Emprendedor, Endeavor España, Startups Real, SaaS Latinoamérica, VC Magazine, TLDR Business Magazine, CIO Advisory Board Latam, Dirigentes Digital, Factor Capital, CIO’s LATAM, InfoWeek, Computerworld México, Harvard Business Review en español, Revista Gestión y Economía y Revista DOS Tecnología y Negocios. GCG queda como referencia parcial.

Startups Chilenas, Red Innova y TyN requieren revisión por resultados ajenos al ámbito propuesto en el índice (apuestas/casinos o anuncios de productos). No se concluye que sus sitios estén comprometidos ni se promueven sus enlaces mientras no se aclare la pertinencia. Las muestras antiguas o de portada no se presentan como prueba de actividad periodística actual.

## Presentación y controles

El directorio se genera desde el mismo registro en `sobre-el-portal.html#fuentes-negocios`: grupos plegables, editor/mercado orientativo y tipo de publicación. Las referencias sin confirmar no reciben un enlace inventado; no se añaden categorías, barras o módulos que ocupen la portada.

Controles: identidad y cada restricción, fechas inválidas/antiguas/futuras, origen suplantado, scopes inseguros, páginas de recursos, presupuesto, diversidad, fallos aislados, duplicados y conservación de registros, persistencia, GNews sin cuota extra, escape HTML y navegación responsive. La evidencia detallada se conserva en cada ficha; el Issue/PR registra comandos y resultados reales. No se declara cumplimiento legal general.
