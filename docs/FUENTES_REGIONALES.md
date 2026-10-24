# Fuentes latinoamericanas y venezolanas

La incorporación regional conserva titulares originales, enlaces HTTPS del medio, fecha y atribución textual. No copia descripciones, fotografías ni artículos, y no consulta las páginas de las notas para enriquecer imágenes. El país mostrado corresponde al **medio**, no necesariamente al país donde ocurrió el hecho.

El registro operativo es `config/regional_sources.json`: dieciséis candidatos de siete países, incluidos seis medios venezolanos. Los campos `permission_status` y `technical_status` son independientes. La revisión del 23 de octubre de 2026 conserva todos con `enabled: false`: cero autorizadas, once restringidas y cinco pendientes; ningún XML se declara validado. Las consultas de comprobación y condiciones están registradas en [la evidencia por fuente](EVIDENCIA_FUENTES_2026-10-23.md); el recolector no consulta candidatas desactivadas.

## Activación por fuente

Para activar una fuente después de revisar sus condiciones y autorización aplicable:

1. Verificar un feed RSS HTTPS oficial, que entregue XML y enlaces a artículos del editor; registrar `feed_url` y `technical_status: "verified"`.
2. Resolver las condiciones de sindicación para este portal y su eventual uso comercial. Registrar la evidencia pertinente en `permission_evidence` y `permission_status: "approved"`. La existencia de RSS no prueba una licencia.
3. Revisar los ítems reales y su clasificación. El adaptador excluye opinión, editoriales y publicidad cuando están identificados en categorías o rutas; no garantiza detectar contenidos mal etiquetados.
4. Cambiar `enabled` a `true` mediante un PR revisado. Un booleano por sí solo no activa una fuente pendiente o restringida.

No hay un interruptor global que omita estos controles. Los feeds observados con una herramienta de navegación no se marcan como XML validado si no se pudieron leer sus entradas. Un 403 o un timeout dejan la disponibilidad sin confirmar. `technical_evidence` registra la URL intentada, fecha UTC, resultado y si se validó XML; `conditions_evidence` conserva el enlace y observación de condiciones. Los códigos internos del conector no se registran como HTTP del editor. `permission_evidence` se reserva para una autorización demostrada.

La evidencia previa de [Efecto Cocuyo](https://efectococuyo.com/terminos-de-uso-y-politica-de-pagos/) registra restricciones explícitas de agregación y enlaces profundos; la reconsulta del 23 de octubre devolvió 429 y no demuestra un cambio de condiciones. [El Universal Venezuela](https://www.eluniversal.com/st-condiciones-de-uso.html) establece una condición específica para enlaces entrantes. [El Tiempo](https://www.eltiempo.com/rss) limita su RSS a uso personal y no comercial. El catálogo conserva estos casos como restringidos. La revisión también documenta condiciones de autorización o uso personal/no comercial de Runrun.es, Infobae, El Espectador, El Comercio, La República, Milenio, El País Uruguay y Folha; permanecen restringidos sin autorización adicional. Los demás casos siguen pendientes. Estas clasificaciones operativas no afirman una prohibición legal universal ni autorizaciones por el mero acceso al RSS.

Este control se aplica al nuevo recolector dirigido. No acredita los derechos de todo el contenido que el portal obtenía previamente por Google Noticias o GNews.

## Límites y tratamiento

- Hasta dieciséis feeds y cuatro notas por medio por ejecución; cada respuesta está limitada a 450.000 bytes y ocho segundos de espera de red.
- Solo noticias de las últimas veinticuatro horas, con tolerancia de quince minutos para desfase de la fuente.
- URLs de notas HTTPS, sin credenciales, puertos ajenos a 443 ni destinos fuera del dominio editorial. Las peticiones y sus redirecciones rechazan destinos no públicos.
- Nacional, Política o Regiones de otro país se presentan en Internacional; Economía, Ciencia, Tecnología, Deportes, Cultura y Clima se clasifican por categorías RSS.
- `metadata_only` se conserva al fusionar y normalizar el historial. Impide fotografías, extractos y consultas de enriquecimiento incluso en ediciones posteriores.
- Se conservan los parámetros semánticos de una URL; solo se eliminan parámetros de tracking conocidos de las claves de deduplicación.
- No se recogen datos de lectores, no se activa publicidad y no se configura ningún servicio de correo.

## Diversidad de portada

La noticia principal conserva el criterio de actualidad/relevancia existente. Las destacadas priorizan editores distintos de los ya presentes, comprobando antes que no se vacíe otra sección. Si faltan alternativas, completan los espacios con los candidatos disponibles.

Las seis noticias iniciales de cada sección comparten hasta dos espacios por editor cuando existe oferta suficiente. La identidad usa el dominio editorial y alias conocidos (por ejemplo BBC/BBC News Mundo); el resto de notas conserva su acceso mediante «Ver más». No se excluye BioBioChile ni se garantiza una cuota de países sin noticias pertinentes.

## Verificación

`python3 -m unittest discover -s tests -q` comprueba atribución, bloqueo de fuentes pendientes, límites, exclusión de opinión identificada, fechas, URLs y preservación de políticas tras normalizar. Las pruebas de selección cubren alias, poca oferta, protección de secciones con una sola noticia y conservación de candidatos.

La activación de nuevas fuentes queda sujeta a la revisión específica de lógica editorial/fuentes/licencias establecida en `docs/agent-workflow.md`. No se cambian workflows, secretos, dominios ni permisos del repositorio.
