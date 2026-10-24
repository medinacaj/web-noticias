# Preparación de fuentes internacionales

Diseño autorizado de #56, adaptado sobre #83; el PR #57 antiguo no se integra. No cambia la interfaz, proveedores, feeds BBC existentes, GNews, workflows ni configuración comercial.

## Contrato y flujo previsto

`config/world_sources.json` conserva once candidatos: Reuters, AP, Al Jazeera English, NHK World-Japan, NPR World, DW Español, France 24 Español, CNN en Español, El País Internacional, Euronews Español y The Guardian. Todos parten `enabled=false`, sin evidencia de autorización ni verificación técnica. Guardian mantiene `permission_status=restricted`; los demás `pending`. Es una lista de preparación, no una licencia ni una lista de fuentes activas.

El colector realiza, sólo tras activar expresamente todas las condiciones por medio, hasta diez búsquedas Google Noticias por ejecución y cuatro titulares válidos por medio. Requiere simultáneamente `enabled=true`, `permission_status=approved`, `technical_status=verified` y evidencia real de permiso. Una búsqueda fallida no detiene las demás. BBC News Mundo y su RSS existente quedan fuera de este catálogo.

La validación reutiliza los helpers existentes y conserva fecha original explícita con zona (ventana 24 horas y tolerancia futura 15 minutos), origen editorial HTTPS dentro del dominio esperado, y artículo HTTPS del mismo editor o Google Noticias legítimo. La declaración del nombre de un medio no sustituye el dominio. El catálogo nuevo gobierna exclusivamente las búsquedas dirigidas nuevas: no recorta ni audita las rutas genéricas Google/GNews o BBC que ya existían, que conservan su política previa. No se añadirán llamadas GNews. Si el titular aporta evidencia explícita latinoamericana, se conserva la puerta de entrada Latam existente.

Las nuevas entradas aceptadas son `metadata_only`: titular original, enlace, fecha y atribución; sin traducciones, resúmenes, imágenes ni consultas a artículos para enriquecimiento. Se reutilizan validación de fechas/origen, deduplicación canónica y persistencia existentes, sin recuperar el antiguo flag `image_fetch_disabled`. Los registros anteriores conservan su política de datos; esta preparación no implica activar ni volver a consultar esos medios.

## Evidencia y límites

No se acredita permiso editorial/comercial por disponibilidad en Google Noticias, notoriedad del medio, un sitio HTTPS o metadatos técnicamente válidos. Guardian fue identificado en #57 como restringido por sus condiciones: <https://www.theguardian.com/help/terms-of-service>; el estado vigente y una autorización específica deben revisarse antes de considerar cualquier activación. No se inventan feeds Reuters ni se usan feeds directos nuevos. El responsable debe aportar y revisar condiciones/autorización, jurisdicciones aplicables, alcance de uso y evidencia técnica real antes de modificar los gates. Chile y las jurisdicciones de los medios/lectores son pertinentes; no se declara cumplimiento legal.

Pruebas previstas: default-off y cada gate ausente; dominio/enlace/fecha inválidos, publicación sin zona antes de normalización, límites/fallos independientes, integración collect/Latam, GNews sin cuota extra, persistencia load/save/merge/dedupe y ausencia de enriquecimiento metadata_only. Evidencia de ejecución en la entrega `world-*`.
