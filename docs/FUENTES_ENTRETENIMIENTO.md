# Cultura y entretenimiento: ediciones complementarias

El usuario pidió ampliar artistas, cine, música y actualidad internacional sin eliminar la cobertura chilena. Se conserva la vía Google Noticias RSS existente de Chile y GNews con su límite de seis consultas por ciclo habilitado.

`scripts/entertainment.py` incorpora dos consultas adicionales al topic `ENTERTAINMENT`: España (`hl=es`, `gl=ES`, `ceid=ES:es`) y México (`hl=es-419`, `gl=MX`, `ceid=MX:es-419`). No se afirman nombres fijos de nuevos medios: cada feed devuelve sus propios editores, que se muestran con atribución y enlace original. No se activan entradas del catálogo mundial ni se crean feeds de editores sin evidencia. Se aplican las puertas de ambos catálogos, mundial y regional: un editor conocido solo pasa si está habilitado, con permiso aprobado, verificación técnica y evidencia de permiso. Los candidatos pendientes, deshabilitados o restringidos siguen bloqueados incluso si reaparecen en el agregador.

Se aceptan hasta seis URLs distintas por edición (doce en total), con fecha editorial explícita con zona, antigüedad máxima de 24 horas y tolerancia futura de 15 minutos. Se requiere fuente editorial HTTPS pública, enlace HTTPS del mismo host/subdominio o URL de artículo de Google Noticias exacta. Se guardan exclusivamente titular original, atribución, enlace y fecha; `metadata_only=true` evita copiar resumen, fotografía o consultar artículos. La deduplicación existente mantiene la fecha original y limita resultados repetidos.

`discovery_edition` identifica únicamente la edición consultada, **no** el país del artista ni del editor. Se conserva al guardar/cargar el historial. Hasta tres de las seis posiciones iniciales de Cultura se reservan a estas entradas cuando existen, intercaladas con las fuentes previas y con diversidad de editores; si faltan entradas, se completa con lo disponible. El resto sigue en «Ver más» y en la búsqueda. El historial anterior no se reescribe durante desarrollo.

## Evidencia y límites

Conectividad en vivo verificada el 2026-10-24 después de activar los dominios de red: `collect_entertainment()` obtuvo 12 noticias válidas de las ediciones ES y MX y diez medios distintos. Esta comprobación no modificó el historial. Las pruebas automatizadas usan entradas RSS simuladas y comprueban fechas, restricciones, límites, fallo independiente, persistencia, selección y ausencia de consultas GNews adicionales. La disponibilidad técnica del agregador no acredita permiso o licencia editorial. No se certifica cumplimiento legal en Chile, España, México ni otras jurisdicciones de editores o lectores. Para incorporar feeds directos nuevos o copiar imágenes/resúmenes se requiere revisión específica de condiciones y autorizaciones conforme a las instrucciones del proyecto.

## Cine, estrenos y conciertos (2026-10-25)

Pedido del usuario: especializar Cultura en cine, estrenos y anuncios de conciertos, sin duplicar carteleras.

- `SEARCHES` en `scripts/entertainment.py` agrega dos búsquedas de Google Noticias en la edición de Chile (`gl=CL`, últimas 48 h): estrenos de cine y anuncios de conciertos/giras. Usan la misma vía y las mismas puertas que las ediciones ES y MX: solo metadatos (titular, medio, enlace y fecha), hasta seis por búsqueda, catálogos mundial y regional respetados. `discovery_edition` vale `CL-CINE` o `CL-CONCIERTOS` y cuenta como cobertura local en el reparto de Cultura.
- Las fechas, lugares y enlaces oficiales de funciones o conciertos próximos van en la **Agenda** (rastreo de recintos y ticketeras en `eventos/` y agenda manual), no en Cultura.

### Medios candidatos revisados (no incorporados)

| Medio | Feed | Condiciones observadas | Estado |
|---|---|---|---|
| Espinof (Webedia) | No verificado: el entorno no resuelve el dominio. | No se encontró el aviso legal en las búsquedas del 2026-10-25. | Pendiente de revisión manual. |
| SensaCine (Webedia España, S.L.) | Un agregador de terceros lista `https://www.sensacine.com/rss/noticias.xml`; no confirmado en el sitio. | El [aviso legal](https://www.sensacine.com/servicios/terminos/) prohíbe reproducir, distribuir o comunicar públicamente sus contenidos sin consentimiento previo por escrito y limita el uso a lo privado y personal. | No incorporable sin permiso escrito. |
| Cineuropa | No verificado. | Sus [términos](https://cineuropa.org/es/aboutterms/) exigen consentimiento previo para reutilizar total o parcialmente sus contenidos; no mencionan RSS. | No incorporable sin permiso. |

No se agregan al catálogo mundial: allí un candidato pendiente queda bloqueado también cuando aparece en Google Noticias, lo que quitaría sus titulares de las búsquedas actuales. Sus titulares pueden seguir llegando como cualquier otro editor por la vía de Google Noticias (solo titular, atribución y enlace). Activar un feed directo, resúmenes o imágenes de estos medios requiere autorización escrita y una revisión según `docs/ASESOR_LEGAL_TECNOLOGICO.md`. No se afirma cumplimiento legal en ninguna jurisdicción.
