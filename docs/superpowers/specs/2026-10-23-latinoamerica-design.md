# Latinoamérica con etiquetas de país

Decisión del usuario 23-10-2026: Brasil es una referencia dentro de Latinoamérica con etiquetas; se cancela el alcance anterior de ediciones/rutas por país de #80.

Objetivo: añadir la sección Latinoamérica al portal actual, con Brasil y los demás países latinoamericanos en una sola cobertura. Conservar Chile/Nacional y el resto de secciones.
Diseño bloqueado: tarjetas, tipografía, paleta, navegación, sombras y componentes existentes. Etiquetas de país en metadatos, texto legible sin depender de banderas; sin selector de ediciones, rutas /brasil/ o /venezuela/ ni redirecciones/geolocalización. Refero live intentado: NO_SUBSCRIPTION; referencias de respaldo: meta_html/source-country existente y craft-details de Refero. El país etiquetado se refiere a una mención explícita en el titular (con alias/demónimos controlados), no al país del editor. Si falta evidencia, omitir etiqueta específica; no inferir por IP, idioma o dominio.

Implementación:
- Nueva categoría latinoamerica, máximo24 historias/sección, seis iniciales y Ver más como hoy.
- Reutilizar ingesta Google RSS existente con dos búsquedas acotadas (Brasil en portugués original y resto Latinoamérica en español). No ampliar cuota GNews, no feeds directos nuevos, no scraping ni enriquecimiento.
- Nuevas entradas de Latinoamérica sólo metadatos (metadata_only): titulares, enlaces, fecha y fuente; resúmenes/imágenes vacíos, image enrichment excluido.
- Verificar origen editorial HTTPS y fechas <=24h con tolerancia futura15min. No inventar source_url. Rechazar editor catalogado sin permiso aprobado/verified/evidencia/enabled, incluso si llega por agregador; no eludir restricciones.
- Etiquetas coverage_countries (códigos controlados) separadas de source_country. Conservar al guardar/cargar y al deduplicar exactURL. Para noticia ya internacional con mismaURL y evidencia de Latinoamérica, reclasificar a latinoamerica; no robar Nacional/Regiones/Política de Chile. No duplicar URL.
- Si un titular Internacional ya menciona países latinoamericanos (no Chile solamente), puede clasificarse en Latinoamérica con las mismas reglas y sin nuevas consultas; conservar política de datos/atribución y no reasignar por país del medio.
- Actualizar selector local de búsqueda y favoritos sólo según metadatos necesarios; etiquetas visibles en cards y resultados si coherente; no añadir tracking/almacenamiento nuevo.
- RSS por latinoamerica y sitemap/canonical siguen rutas del portal único; no crear páginas nacionales indexables ni datos estructurados NewsArticle ajenos.
- Documentar incertidumbre de permisos del agregador sin afirmar licencia.

Pruebas primero:
- Brasil/portugués y Venezuela/Argentina/etc pertenecen a Latinoamérica con etiquetas correctas; un medio brasileño sobre Francia no recibe etiqueta Brasil, y noticia Chile-only no salta de Nacional.
- Tracking/sameURL, historial anterior sin coverage_countries, país múltiple y entrada inválida no pierden/duplican datos; país desconocido no inventado.
- Metadata-only no ejecuta image enrichment ni conserva extractos; fuentes pending/restricted del catálogo no entran por búsquedas nuevas.
- Brasil RSS locale/query, dos requests máximos nuevos, GNews sin duplicación; fallo de un feed no bloquea el otro; fechas sin zona/ausentes/futuras/antiguas se tratan explícitamente.
- HTML, filtros reales, XML RSS, canonical, JSON-LD, suite existente y QA5anchos.

Fuera de alcance: cambios en permisos/workflows/proveedores/comercial, responsabilidad de otros worktrees.

