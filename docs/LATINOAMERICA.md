# Cobertura de Latinoamérica

El portal único incorpora la sección `latinoamerica` (máximo 24 titulares, seis iniciales y Ver más), sin ediciones por país, geolocalización ni rutas nacionales. Conserva las secciones chilenas. El diseño y los colores reutilizan Internacional.

`coverage_countries` contiene códigos controlados de países mencionados explícitamente en titulares, con alias y gentilicios en español/portugués. No se infiere el país por dominio, idioma, IP ni identidad del editor. Chile solo no mueve una noticia de Nacional a Latinoamérica. `source_country` sigue describiendo al editor, un dato distinto. Un país sin evidencia se omite; la detección conservadora puede perder noticias que sólo mencionan ciudades o personas.

La recolección añade dos búsquedas Google Noticias RSS por ejecución: Brasil (`pt-BR`, `BR`, `BR:pt-419`) y los demás países en español (`es-419`, `CL`, `CL:es-419`). No añade solicitudes GNews ni feeds directos. Una falla se aísla por búsqueda. Las entradas WORLD/GNews ya obtenidas con evidencia regional pasan por la misma puerta de entrada, sin nuevas consultas.

Las entradas nuevas admitidas requieren fecha con zona, antigüedad máxima de 24 horas y tolerancia futura de 15 minutos. Requieren origen editorial HTTPS público declarado en los metadatos y enlace del mismo origen o Google Noticias legítimo; no se reconstruye el origen desde el nombre del medio. Se conservan sólo titular, enlace, fecha y atribución (`metadata_only`): no extractos, fotografías ni consultas de enriquecimiento a artículos.

Un editor identificado por dominio o nombre en el catálogo regional sólo pasa si tiene `enabled=true`, permiso `approved`, estado técnico `verified` y evidencia de permiso. El agregador no evita esa restricción. El catálogo no se activa ni se modifica con esta funcionalidad. El historial anterior conserva su política de datos; una noticia de Internacional de un editor catalogado bloqueado no se mueve de sección. Las URLs iguales (incluido tracking) se consolidan, conservando países y la política más restrictiva; la evidencia regional puede reclasificar Internacional, sin reasignar Nacional, Regiones ni Política.

La búsqueda y favoritos siguen siendo locales y usan las categorías existentes; los resultados muestran las etiquetas de país. `rss/latinoamerica.xml` reutiliza la política del RSS público: sólo enlaces directos con atribución verificable; los enlaces Google sin resolver se omiten del RSS. Canonical, sitemap y JSON-LD siguen describiendo el portal único; no se generan artículos propios ni páginas nacionales.

## Permisos y límites abiertos

Confirmado: se minimizan los datos nuevos, se enlaza al medio y se aplican las restricciones del catálogo; no se consulta el artículo para extraer contenido. No verificado: licencia o autorización contractual suficiente para agregar/publicar metadatos obtenidos de Google Noticias en cada jurisdicción implicada (Chile, Brasil y los demás países latinoamericanos). La disponibilidad pública del RSS no demuestra una licencia. El responsable del portal debe resolver esta revisión antes de considerar autorizado el uso; estas pruebas técnicas no declaran cumplimiento legal ni permisos editoriales. No se añade tratamiento de datos personales, tracking ni almacenamiento del lector.
