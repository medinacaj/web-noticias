# Recolector de eventos

Rastreo de eventos públicos para la sección «Agenda» de Noticias del Momento.
Integrado desde `medinacaj/eventos-biobio` (solo el rastreo; la app local quedó fuera).

- `actualizar.py`: rastrea las fuentes habilitadas de `config/sources.json` (Biobío) o, con
  `--nacional`, `config/national_sources.json`. En el workflow escribe con `--snapshot` y
  `--estado-fuentes` fuera del código; `config/` solo cambia por PR.
- Solo la lista `events` se publica. `possible_events` y candidatos en cuarentena son para
  revisión manual (ver la tarea programada «Revisión de eventos»).
- Pruebas sin red: `python3 -m unittest discover -s tests -t .` (desde esta carpeta).

Los snapshots viven en la rama `events-data` (`eventos/crawled_events.json`,
`eventos/national_events.json`, estado de fuentes y `coverage.md`).

## Agenda 360° — extracción, continuidad y cobertura

- El rastreador prioriza los enlaces recientes a eventos de la portada antes de las
  URL históricas del sitemap, manteniendo el límite de páginas por fuente.
- Las fichas individuales de fuentes oficiales pueden obtener la fecha desde
  microdatos `<time itemprop="startDate" datetime="...">` cuando no hay JSON-LD.
  No se toman fechas editoriales `article:published_time` como fechas de evento.
  La publicación requiere título, comuna y fecha; los otros textos siguen en
  `possible_events` hasta revisión.
- La base recupera eventos futuros desde los snapshots anteriores. Si una misma
  ficha individual cambia fecha u hora, conserva identidad, registra `changes`
  y señala la reprogramación; las temporadas con funciones distintas no se unen.
  Las actividades ya finalizadas se ocultan automáticamente en la web.
- La portada muestra un desplegable **Cobertura y calidad de la agenda** con
  fuentes consultadas/respuestas, eventos vigentes rastreados en Biobío,
  candidatos pendientes y comunas sin cobertura. Los indicadores pertenecen al
  último snapshot regional y **no incluyen** las fichas manuales ni toda la
  cobertura nacional. Sin snapshot de ejecución reciente, no se muestran cifras
  ficticias.
- La frecuencia efectiva de actualización **sigue siendo diaria** según
  `.github/workflows/actualizar-eventos.yml`. Una fase futura deberá contemplar
  ventanas distintas por tipo de fuente, reintentos con límites y una revisión
  expresa del workflow para cambiar la programación. No se promete tiempo real.

### Control de calidad y alcance

El código lee exclusivamente recursos públicos admitidos; no elude autenticación,
bloqueos 403 ni restricciones de acceso. Ningún evento sin evidencia suficiente
se publica automáticamente. Los reportes indican fallos de rastreo, **no**
incumplimientos de las entidades citadas. Jurisdicción editorial: Chile.
