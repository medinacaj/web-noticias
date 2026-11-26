# Memoria operativa · 26 de noviembre de 2026

Corte de evidencia del 26 de noviembre de 2026 en America/Santiago. Repositorio oficial `github.com/medinacaj/web-noticias`. La referencia de código es el commit, sin versión SemVer acreditada. [Repositorio](https://github.com/medinacaj/web-noticias) · [Sitio de referencia](https://medinacaj.github.io/web-noticias/)

## Identidad y recuperación

| Evidencia | Resultado |
| --- | --- |
| Remoto y rama predeterminada | `origin` de lectura y escritura apunta a `https://github.com/medinacaj/web-noticias.git`. `git ls-remote --symref origin HEAD` y la vista de GitHub confirman `main` en `7dd1bbcf264bc293dadf4185c6d9a095f05e9f98`. |
| Checkout inicial | `/workspace/web-noticias`, un worktree en rama local `work` al mismo SHA que `main`. Sin cambios rastreados, archivos nuevos sin ignorar, stashes o commits exclusivos de `work`. El chequeo de objetos inalcanzables no devolvió hallazgos. Los ignorados observados fueron `public/` y cachés Python. |
| Archivos de la sesión anterior | No se encontraron en esta instancia los dos directorios históricos de `scratch/` ni `/workspace/web-noticias-business`. La sesión anterior reportó estado pendiente, desconexión, fallos del ejecutor y rechazo de escrituras. Sus temporales y su configuración anterior quedan sin verificar. |
| Recuperación documental | GitHub conserva `docs/readme-continuidad-20261121` en `ed8ff3f3afb551418a87423b0e8af4687049a152`, único commit sobre el `main` comprobado y cabecera del PR #263 abierto. El respaldo conserva ese commit como antecesor exacto de la rama `docs/respaldo-transferencia-2026-11-26` y amplía su README. La rama y el PR originales conservan su propia trazabilidad. |
| Trabajo editorial aparte | El PR #211 abierto conserva dos commits en `1dfafe07d909eb2d48c95974e0a977209243602a` para la semana del 2 al 8 de noviembre. Queda en su rama remota y fuera del respaldo documental. |
| Datos operativos | Refs observadas al corte: `news-data` en `eed9626403a67a3a350578ed6e27f6c29207b867` y `events-data` en `1de1649bed8d3d0450b4636ab12853656c38558b`. Pueden avanzar de forma automática. El respaldo conserva las refs de GitHub y no copia sus snapshots al área documental. |

[PR #263](https://github.com/medinacaj/web-noticias/pull/263) · [PR #211](https://github.com/medinacaj/web-noticias/pull/211) · [Rama de respaldo](https://github.com/medinacaj/web-noticias/tree/docs/respaldo-transferencia-2026-11-26)

El 2 de noviembre `fa6246fc4f793b8521f58ecf091beaf078a1fac8` era la base del PR #222, después del #220. La rama `feat/portada-resumen-seguimiento` sigue en GitHub y `refs/pull/222/head` confirmó la cabecera `a468dd2f271e684d82c6c0f93b447f94412d51a3`. Su árbol coincide con la integración `9a5b2f79fe6dfb8b5e346edc28157e30e4f7ac79`, ancestro de la base actual. GitHub confirma los PR #96, #220, #222 y #257 fusionados. La cabecera del #96 ya es ancestro de `main`. [PR #96](https://github.com/medinacaj/web-noticias/pull/96) · [PR #220](https://github.com/medinacaj/web-noticias/pull/220) · [PR #222](https://github.com/medinacaj/web-noticias/pull/222) · [PR #257](https://github.com/medinacaj/web-noticias/pull/257) · [Registro de cambios](../CHANGELOG.md)

## Validación de la base de código

Validaciones locales de esta sesión sobre `7dd1bbcf264bc293dadf4185c6d9a095f05e9f98`, con Python 3.12 y fixture separado del historial operativo:

| Comprobación | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -q` | 518 pruebas, todas aprobadas. |
| `cd eventos && python -m unittest discover -s tests -t . -q` | 123 pruebas, todas aprobadas. |
| `python scripts/render_visual_fixture.py --output <directorio-temporal>` | Generó el sitio con 177 noticias de QA. |
| `python scripts/validate_history.py` | 180 registros válidos del fixture. |
| `python scripts/audit_editorial_quality.py --strict` | Aprobó. Registró 169 entradas sin resumen, 37 sin fotografía y cero enlaces inválidos o fuentes sin nombre. |
| `python scripts/audit_seo.py --site <directorio-temporal>` | Aprobó canónicas, sitemap, metas, datos estructurados, noindex y enlaces internos. |
| `PYTHONPATH=. python tests/reader_ui_browser.py` | 87 pruebas aprobadas. Suite ejecutada en una copia temporal completa de `main` con el sitio de prueba generado y Chromium de la máquina. |
| `scripts.visual_qa.check` | Aprobó en siete anchos, de 320 a 2560 px, con Chromium de la máquina y HTTP local. Generó 42 capturas. |

El HTML público de GitHub mostró los checks de integridad y QA visual exitosos en la cabecera del PR #257 (`a49946fc3971f30601b0512dea16e5976fd622be`). También mostró ambos checks exitosos en el PR #263 para `ed8ff3f`. Cada PR conserva su propia evidencia; la elegibilidad para fusionar, las revisiones bloqueantes, los conflictos y los checks del respaldo se deben confirmar en su propia cabecera. Safari en iPhone físico y axe quedan sin validación nueva. [Checks #257](https://github.com/medinacaj/web-noticias/pull/257/checks) · [Checks #263](https://github.com/medinacaj/web-noticias/pull/263/checks)

Evidencia histórica del 2 de noviembre. El traspaso registró 512 pruebas de noticias, 123 de eventos y 87 de navegador aprobadas, 180 registros válidos, auditorías editorial y SEO, QA visual en siete anchos y revisión de accesibilidad y desbordes. La revisión independiente registró un destello inicial de tema y tamaño, corregido en la cabecera final. GitHub volvió a mostrar éxito para los dos runs históricos de CI de `a468dd2` y para el publicador de `9a5b2f7`. La comprobación HTTP 200 de portada, Hoy, CSS y JS y el `Last-Modified` del 2 de noviembre a las 15:49:44 UTC pertenecen a aquella entrega. [Integridad](https://github.com/medinacaj/web-noticias/actions/runs/41474535153) · [QA visual](https://github.com/medinacaj/web-noticias/actions/runs/41474535158) · [Publicador histórico](https://github.com/medinacaj/web-noticias/actions/runs/41475057283)

## Publicación y configuración

El workflow `update-news.yml` programa `7 * * * *` y permite ejecución manual. GitHub puede demorar o saltar ejecuciones. En `main`, también se activa al cambiar las rutas de código que enumera el workflow. Primero genera con acceso de lectura y valida; después persiste solamente el historial validado en `news-data`; finalmente publica el artefacto en Pages con permisos propios. Eventos tiene cron separado `23 9 * * *` UTC y guarda en `events-data`. Los documentos de este respaldo quedan fuera de los filtros de push del publicador. [Workflow de noticias](../.github/workflows/update-news.yml) · [Workflow de eventos](../.github/workflows/actualizar-eventos.yml)

Al corte, GitHub mostró el publicador programado [45844902995](https://github.com/medinacaj/web-noticias/actions/runs/45844902995) exitoso para `7dd1bbc`, incluida la etapa Pages. La ejecución de [eventos 45880966946](https://github.com/medinacaj/web-noticias/actions/runs/45880966946) también figuró exitosa. El [monitor 45886400900](https://github.com/medinacaj/web-noticias/actions/runs/45886400900) posterior falló y mostró código de salida 1. El proxy bloqueó el acceso a `medinacaj.github.io` en esta sesión, por lo que la respuesta HTTP actual, la frescura de portada y la causa concreta del fallo del monitor requieren confirmación. La REST y GraphQL de `api.github.com` también quedaron bloqueadas por el proxy. La lectura de Git y de páginas públicas de `github.com` funcionó.

Variables vigentes por nombre:

- `SITE_URL` determina la canónica, con deducción desde `GITHUB_REPOSITORY` cuando corresponde. `GSC_VERIFICATION` añade verificación cuando se configura. `GNEWS_API_KEY` es opcional y habilita GNews en las horas elegibles, una de cada tres. El portal mantiene sus rutas RSS. [Generador](../fetch_noticias.py)
- El script de anuncios exige `ADSENSE_READY`, `ADSENSE_PUBLISHER_ID` válido, `ADSENSE_PRIVACY_URL` válida y control declarado de una raíz elegible con `ADSENSE_ROOT_CONTROLLED`. Metadatos, enlace de privacidad y `ads.txt` se rigen por sus propias condiciones. [Configuración de anuncios](ADSENSE.md) · [Código](../scripts/adsense.py)
- El alta externa del boletín exige `NEWSLETTER_READY`, `NEWSLETTER_PROVIDER`, `NEWSLETTER_SUBSCRIBE_URL`, `NEWSLETTER_PRIVACY_URL` y `NEWSLETTER_UNSUBSCRIBE_URL`. El operador debe validar doble opt-in y baja. [Configuración de boletín](NEWSLETTER.md) · [Código](../scripts/newsletter.py)
- `EVENTOS_BIOBIO_URL`, `EVENTOS_NACIONALES_URL` y `EVENTOS_MANUAL_URL` son overrides opcionales. Las rutas por defecto leen los snapshots propios y la agenda manual. [Código de Agenda](../scripts/agenda.py)

Activación real de anuncios/boletín, protecciones administrativas efectivas, cobertura editorial, permisos de fuentes y staging persistente quedan sin comprobar. Los resultados locales muestran la capacidad del entorno. La evidencia de GitHub corresponde a sus refs y ejecuciones observadas.

## Continuidad y prioridades

| Prioridad | Estado y próxima comprobación |
| --- | --- |
| P0 | Ningún hallazgo nuevo demostrado. Las validaciones acotadas dejan pendiente cualquier afirmación general sobre seguridad y datos de producción. |
| P1 | Completar la trazabilidad del respaldo en rama y PR. Registrar SHA remoto, validaciones, revisiones, conflictos y estado de integración en el informe posterior a la publicación. Usar el [issue de auditoría #256](https://github.com/medinacaj/web-noticias/issues/256), abierto, como referencia de continuidad. |
| P1 por contrastar | Validar Safari físico y diagnosticar el fallo observado del monitor en GitHub con información reciente. [Safari #195, abierto](https://github.com/medinacaj/web-noticias/issues/195) · [Monitor 45886400900](https://github.com/medinacaj/web-noticias/actions/runs/45886400900) |
| P2 | Abiertos al corte: [#193 UX](https://github.com/medinacaj/web-noticias/issues/193), [#170 estrenos](https://github.com/medinacaj/web-noticias/issues/170), [#174 Agenda](https://github.com/medinacaj/web-noticias/issues/174), [#177 cadencia](https://github.com/medinacaj/web-noticias/issues/177), [#146 retiro de origen](https://github.com/medinacaj/web-noticias/issues/146), [#84 ejecución programada](https://github.com/medinacaj/web-noticias/issues/84), [#74 fuentes](https://github.com/medinacaj/web-noticias/issues/74), [#65 comercial](https://github.com/medinacaj/web-noticias/issues/65) y [#219 salida de datos](https://github.com/medinacaj/web-noticias/issues/219). Contrastar su alcance con el código y PR existentes. Para el #96, partir de su integración comprobada. Recuperar temporales solo si vuelve a estar disponible su origen. |
| P3 | Servicios con valores actuales, explicaciones editoriales propias y mayor permanencia se mantienen fuera del respaldo. [Decisiones](DECISIONES.md) |

Los issues [#218](https://github.com/medinacaj/web-noticias/issues/218) y [#221](https://github.com/medinacaj/web-noticias/issues/221) siguen cerrados. Para un nuevo traspaso, seguir la [instrucción autónoma](CONTINUIDAD_NUEVA_SESION.md).
