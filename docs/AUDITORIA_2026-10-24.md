# Reauditoría de Web Noticias · 24 de octubre de 2026

Base publicada examinada: `3d8642ed7a574d5df874e3fabccfa38d0e70b628`.
Alcance: ingesta, fechas, deduplicación, persistencia, plantillas y seguridad del
navegador, gates comerciales, pipeline, HTTP/SEO/RSS y correcciones preparadas.
Seguimiento: [issue #84](https://github.com/medinacaj/web-noticias/issues/84).

## Defectos demostrados y cambios

| Prioridad | Evidencia | Corrección |
| --- | --- | --- |
| P2 | Opciones empezaba en x=-28 a 320 px, ocultando título y etiquetas aunque no había desborde derecho. | Anclaje móvil a la fila de la barra y comprobación de ambos bordes. Panel x=24..308 a 320 px; cinco anchos y texto al 200 % aprobados. |
| P2 | Fechas `9999-12-31T23:59:59-12:00` y `0001-01-01T00:00:00+12:00` desbordaban UTC y abortaban el colector mundial. | Normalizar/rechazar la fecha antes de devolverla; conservar entradas válidas del mismo feed y otros editores. Ocho reproducciones independientes verificadas después del arreglo. |
| P2 | Un título RSS con `%%REMOTE_MARKER%%` impedía generar el sitio; tokens conocidos en datos también se interpretaban como plantilla. | Validar marcadores de la plantilla original y sustituirlos en una sola pasada. Los datos quedan literales; un marcador estructural desconocido sigue rechazándose sin sobrescribir la edición anterior. |
| P2 | Monitor cada seis horas y umbral de ocho aceptaban la edición observada con 3,3 h sin refrescar y cinco entradas RSS de más de 24 h. | Comprobar cada hora, alertar tras dos horas y conservar la incidencia única, evento pospublicación y permisos mínimos. No se atribuye a este cambio la causa de retrasos del scheduler. |

Los casos de fechas, plantilla y monitor fallaron antes del cambio y pasaron
después. La suite integrada pasó **280 pruebas Python**, además de ocho Node;
el PR registra el SHA final y la CI asociada. No se identificaron otros P0/P1
demostrables en el alcance revisado; esto no certifica ausencia de vulnerabilidades.

## Operación observada y recuperación

A las 04:30 UTC, la edición seguía fechada a 01:13:38. Workflow activo,
programación `7 * * * *`, rama main correcta, pero sin ejecuciones posteriores
registradas; última ejecución de evento schedule a 00:37. Los 19 recursos propios
examinados respondían correctamente y el SEO no tenía errores. El retraso no
era un fallo HTTP ni se demostró una causa en el código del cron.

Se solicitó una ejecución manual autorizada. El
[publicador 40062793405](https://github.com/medinacaj/web-noticias/actions/runs/40062793405)
actualizó a las 04:33:25 y el
[monitor 40062848135](https://github.com/medinacaj/web-noticias/actions/runs/40062848135)
confirmó portada, fecha y sitemap. HTTP posterior: 19 recursos correctos, SEO sin
errores y entradas RSS mayores de 24 h de **cinco a cero**. Main permaneció en
`3d8642ed`; sólo cambió data/historial.json de news-data, commit
`12938cfc03d9ff085774d65dc828eace68c8102b`.

La recuperación manual está comprobada; **la causa de la ausencia de eventos
programados permanece sin identificar**. La programación de GitHub Actions no
equivale a una garantía de entrega puntual. Mantener seguimiento de ejecuciones
programadas posteriores; el endurecimiento del monitor detecta antes la recaída.

## Seguridad, fuentes y límites

Prueba real offline de Chromium con payloads de script, img/onerror y SVG/onload
en título, fuente, resumen, URL, favoritos y diálogo: ninguna ejecución XSS,
nodo inyectado o error JS observado. Un enlace javascript guardado se rechazó.
Con configuración vacía no aparecen script publicitario ni alta de suscripción.
Las cargas de Fonts, favicon y foto del fixture se identificaron y bloquearon en
esa prueba; no se afirma ausencia universal de conexiones de terceros.

La política metadata_only se conservó al importar por CLI, guardar, cargar,
deduplicar y renderizar, sin extractos ni imágenes. Las vías previas de
WORLD/GNews/BBC mantienen su política documentada; no se interpreta como bypass
del catálogo dirigido nuevo ni como licencia sobre el contenido anterior.

Permanecen desactivadas 16 fuentes regionales y 11 candidatas mundiales. Hay
cuatro RSS regionales técnicamente compatibles; ninguna autorización nueva.
La disponibilidad de XML y una prueba técnica no acreditan permiso comercial.
Los detalles están en las verificaciones de fuentes y navegador del mismo día.

Main sigue sin protección administrativa aplicada (#62). La integración devuelve
403 al acceso de Administration pese al rol administrador del usuario. Se
prepara un ruleset importable, sin afirmar que esté activo. AdSense y boletín
requieren datos/cuentas/políticas reales; no se activa ni contrata un servicio.
