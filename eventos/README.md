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
