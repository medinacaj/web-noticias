# Retiro seguro del repositorio `medinacaj/eventos-biobio`

Esta guía prepara la **revisión humana** antes de retirar el repositorio antiguo. No autoriza ni ejecuta su borrado. El PR asociado a esta guía debe permanecer sin fusionar hasta que el responsable lo revise.

## Arquitectura que debe conservarse

- **Código de rastreo:** `web-noticias/eventos/` (`actualizar.py`, `scrapers/`, `config/`, pruebas). Se incorporó en el [PR #96](https://github.com/medinacaj/web-noticias/pull/96).
- **Actualización de eventos:** `.github/workflows/actualizar-eventos.yml` ejecuta el código de la rama principal y escribe los datos validados en la rama **`events-data`**, mediante `scripts/events_data.py`.
- **Lectura de la Agenda:** `scripts/agenda.py` lee por defecto `.events-data/eventos/crawled_events.json`, `.events-data/eventos/national_events.json` y `eventos/agenda_manual.json`. `.github/workflows/update-news.yml` obtiene la rama `events-data` y publica en GitHub Pages.
- **Calidad:** solo los elementos de `events` pueden publicarse. `possible_events` y candidatos no verificados no son publicaciones.
- **Fuera de la migración, deliberadamente:** aplicación local `app.py`, interfaz `static/`, `launcher.py` y lanzadores de Windows/Mac/Linux, así como su operación administrativa local. No hay equivalente de ese backend en GitHub Pages.

Los nombres históricos de `eventos-biobio` en documentación o comentarios no constituyen dependencias de ejecución. Las pruebas de `tests/test_eventos_independencia.py` protegen rutas y workflows relevantes contra regresiones conocidas, pero **no prueban la ausencia de consumidores externos**.

## Verificaciones antes de eliminar el repositorio antiguo

1. **Respaldo:** descargar o clonar un espejo del repositorio antiguo, incluyendo su rama por defecto, historial, aplicación local y datos si se desean conservar. Revisar también artefactos externos que no se versionan.
2. **Dependencias externas:** revisar enlaces `raw.githubusercontent.com`, integraciones, lectores, automatizaciones de correo, variables de entorno, Actions de otros repositorios, páginas web y servicios externos. Una búsqueda de código de `web-noticias` no cubre estos consumidores.
3. **Variables:** confirmar que ninguna configuración operativa sobrescribe `EVENTOS_BIOBIO_URL`, `EVENTOS_NACIONALES_URL` o `EVENTOS_MANUAL_URL` apuntando al repositorio antiguo. Los valores predeterminados son locales; la posibilidad de usar URLs HTTPS sigue existiendo en el código.
4. **Pruebas del PR:** verificar el estado de las dos suites Python de `quality.yml` y revisar el diff/SHA exacto. No interpretar un workflow verde como prueba de cobertura editorial completa.
5. **Comprobar ejecución real:** confirmar una ejecución exitosa reciente de **Actualizar eventos** y una posterior de **Actualizar Noticias del Momento**. Revisar la cobertura de fuentes, la validez y vigencia de los eventos, y que las tarjetas de Agenda se muestren cuando existan eventos elegibles. Si no los hay, es esperable que la sección no aparezca.
6. **Datos propios:** confirmar que la rama `events-data` sigue existiendo y recibe `crawled_events.json`, `national_events.json`, estados y `coverage.md`, sin consumir snapshots del antiguo repositorio.
7. **Retiro manual:** solo después de validar los puntos anteriores, decidir si archivar o eliminar `eventos-biobio` en GitHub. Sus Actions continuarán ejecutándose mientras permanezcan habilitadas. Esta guía no altera workflows, permisos ni repositorios.

## Diferencias entre los catálogos de fuentes

La comparación del 28-10-2026 identificó la misma cantidad de entradas (60 regionales y 10 nacionales) en ambos proyectos. Las diferencias de `notes` y `last_live_check` reflejan observaciones de ejecución y **no deben copiarse** a la configuración estable por el solo hecho de ser posteriores. Revisar estas diferencias puntuales con evidencia HTTP de `web-noticias`:

| Fuente | Diferencia detectada | Acción de revisión |
| --- | --- | --- |
| Municipalidad de Hualqui | `url_evidence` y `url_candidates` no coinciden | Confirmar dominio y procedencia antes de modificar candidatos |
| Municipalidad de Los Ángeles | `verified_live` difiere | Consultar estado generado por el rastreo propio; no forzar `true` por copia |
| Corcudec (Teatro UdeC) | `verified_live` difiere | Consultar estado generado por el rastreo propio; no forzar `true` o `false` por copia |

Los cambios en `actualizar.py` de `web-noticias` agregan las opciones `--snapshot` y `--estado-fuentes` para escribir resultados fuera del código; no se deben reemplazar con la versión del repositorio antiguo.

## Riesgo residual y vuelta atrás

- **Confirmado:** el módulo de rastreo, su almacenamiento y la publicación de Agenda existen dentro de `web-noticias`, y el PR de integración fue fusionado.
- **No verificado automáticamente:** consumidores externos, secretos/variables en todas las cuentas, copias de datos fuera de Git y calidad de los eventos publicados tras eliminar el origen.
- **Si falla la Agenda después del retiro:** no modificar fuentes a ciegas. Inspeccionar `actualizar-eventos.yml`, la rama `events-data`, `update-news.yml`, el estado de fuentes y las variables que sobreescriban rutas. Restaurar el repositorio antiguo solo desde un respaldo si un consumidor externo todavía lo necesita.

Responsable de la decisión destructiva: propietario del repositorio, **fuera de este PR**. Seguimiento y evidencia mutable: [issue #146](https://github.com/medinacaj/web-noticias/issues/146).
