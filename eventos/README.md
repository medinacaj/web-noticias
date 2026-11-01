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

## Fase 2: cadencia y revalidación de eventos vigentes

- Cada ejecución del workflow sigue ocurriendo según su cron actual: una vez por
  día y al fusionar cambios en `eventos/`. Dentro de una ejecución, el motor
  aplica cadencias **por fuente**. La ventana predeterminada es 12 horas para
  recintos y ticketeras; 24 para otras fuentes y municipalidades; 48 para
  radares. Se pueden declarar valores de 6 a 168 horas con
  `refresh_interval_hours` en la configuración de fuentes. Una ventana de
  12 horas **no provoca dos ejecuciones diarias**.
- El último intento, éxito y HTTP de cada fuente se guardan en
  `source_state` dentro de `events-data`. Omitir una fuente por cadencia no
  equivale a volver a verificarla. La opción `--only` y el nuevo `--force`
  pasan por alto la cadencia en ejecuciones manuales.
- Una nueva corrida activada muy pronto después de otra sondea hasta tres
  fuentes adicionales si, de lo contrario, no se comprobaría ninguna.
  `check_snapshot.py` sigue exigiendo al menos una respuesta HTTP real 2xx.
- Hasta cuatro URL HTTPS de fichas **ya publicadas** y aún vigentes por fuente
  se vuelven a revisar aunque no aparezcan en portada, dentro del presupuesto
  normal de páginas rastreadas. No se vuelven a visitar candidatos sin validar.
  El historial de cambios lo conserva `db.py`; las páginas caídas no se
  consideran canceladas automáticamente.
- En carteleras nacionales sin comuna fija, los eventos JSON-LD se publican
  solo cuando `location.address.addressLocality` coincide exactamente con
  una comuna registrada y `addressRegion` declara Biobío. Si hay homónimos,
  dirección insuficiente o una región distinta, permanecen en revisión.
  No se interpreta como autorización para copiar contenidos de terceros.
