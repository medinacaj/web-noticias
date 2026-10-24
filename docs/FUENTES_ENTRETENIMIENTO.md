# Cultura y entretenimiento: ediciones complementarias

El usuario pidió ampliar artistas, cine, música y actualidad internacional sin eliminar la cobertura chilena. Se conserva la vía Google Noticias RSS existente de Chile y GNews con su límite de seis consultas por ciclo habilitado.

`scripts/entertainment.py` incorpora dos consultas adicionales al topic `ENTERTAINMENT`: España (`hl=es`, `gl=ES`, `ceid=ES:es`) y México (`hl=es-419`, `gl=MX`, `ceid=MX:es-419`). No se afirman nombres fijos de nuevos medios: cada feed devuelve sus propios editores, que se muestran con atribución y enlace original. No se activan entradas del catálogo mundial ni se crean feeds de editores sin evidencia. Se excluyen los dominios marcados `restricted` en ese catálogo.

Se aceptan hasta seis URLs distintas por edición (doce en total), con fecha editorial explícita con zona, antigüedad máxima de 24 horas y tolerancia futura de 15 minutos. Se requiere fuente editorial HTTPS pública, enlace HTTPS del mismo host/subdominio o URL de artículo de Google Noticias exacta. Se guardan exclusivamente titular original, atribución, enlace y fecha; `metadata_only=true` evita copiar resumen, fotografía o consultar artículos. La deduplicación existente mantiene la fecha original y limita resultados repetidos.

`discovery_edition` identifica únicamente la edición consultada, **no** el país del artista ni del editor. Se conserva al guardar/cargar el historial. Hasta tres de las seis posiciones iniciales de Cultura se reservan a estas entradas cuando existen, intercaladas con las fuentes previas y con diversidad de editores; si faltan entradas, se completa con lo disponible. El resto sigue en «Ver más» y en la búsqueda. El historial anterior no se reescribe durante desarrollo.

## Evidencia y límites

La conectividad en vivo a `news.google.com` está pendiente del cambio de red guardado en el borrador del entorno. Las pruebas usan entradas RSS simuladas y comprueban fechas, restricciones, límites, fallo independiente, persistencia, selección y ausencia de consultas GNews adicionales. La disponibilidad técnica del agregador no acredita permiso o licencia editorial. No se certifica cumplimiento legal en Chile, España, México ni otras jurisdicciones de editores o lectores. Para incorporar feeds directos nuevos o copiar imágenes/resúmenes se requiere revisión específica de condiciones y autorizaciones conforme a las instrucciones del proyecto.
