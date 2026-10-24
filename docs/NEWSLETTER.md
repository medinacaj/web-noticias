# Newsletter de Noticias del Momento

## Estado

La web **genera automáticamente una vista previa diaria** en `/boletin-diario.html` al publicarse la página. La vista agrupa un máximo de 12 noticias de las últimas 24 horas disponibles en el historial y enlaza a los medios originales. No existe un servicio de suscripción ni envío conectado por defecto. El boletín **no es un email enviado**.

### Para activar el registro con un proveedor externo

Elegir un servicio que admita confirmación de suscripción (doble opt-in), enlaces de baja individuales por mensaje, protección contra abusos, exportación y eliminación de datos, y política de privacidad clara. Verificar obligaciones aplicables a los destinatarios (incluido Chile), tratamiento de datos y condiciones de titulares/citas. No almacenar direcciones de los suscriptores en el repositorio, en GitHub Actions ni en el navegador para simular registro.

Configurar en GitHub Actions o variables del repositorio:

- `NEWSLETTER_PROVIDER`: nombre del proveedor realmente contratado/configurado. No escribir un proveedor de ejemplo ni «pendiente» para completar el gate.
- `NEWSLETTER_READY=true`: habilita los enlaces de alta *solo* con proveedor y las tres URLs válidas. Expresa que el responsable ya probó y revisó el flujo de consentimiento, privacidad y baja; el código no puede comprobarlo por formato.
- `NEWSLETTER_SUBSCRIBE_URL=https://...`: URL real, HTTPS, del formulario alojado por el proveedor (el proveedor capta datos y confirmaciones).
- `NEWSLETTER_PRIVACY_URL=https://...`: enlace verificado a la política de privacidad de la suscripción.
- `NEWSLETTER_UNSUBSCRIBE_URL=https://...`: URL pública y verificada para gestionar la baja. **Además**, todo correo debe incluir su enlace de baja individual; una URL general no lo sustituye.

Las tres URLs deben ser HTTPS. El estado predeterminado muestra **«Suscripciones próximamente»** y nunca presenta un formulario falso.

### Si todavía no hay cuenta o proveedor

Mantener `NEWSLETTER_READY` vacío o `false` y publicar únicamente la vista previa. El responsable debe elegir y abrir una cuenta, revisar sus condiciones y tratamiento de datos, identificar al responsable de la lista y aportar un contacto real. Crear dentro del proveedor un formulario alojado con doble confirmación, una política que refleje el servicio real y una página pública para gestionar bajas. Probar con una dirección propia autorizada: alta pendiente → confirmación → alta efectiva → baja → exclusión de siguientes campañas. Conservar allí la evidencia de consentimiento, sin subir direcciones o tokens de confirmación al repositorio.

No se selecciona ni crea una cuenta automáticamente, no se inventa contacto y no se publica una política rellenada con datos ficticios. La ausencia de esos datos mantiene la suscripción desactivada. Elegir un proveedor no activa envíos: faltan lista confirmada, contenido final de campaña y validación de entregabilidad.

### Interfaz del generador

`configured_newsletter(environ=None)` centraliza el estado y devuelve `enabled`, `requested`, `provider`, `subscribe_url`, `privacy_url`, `unsubscribe_url` y `signup_html`. `None` lee `os.environ`; `{}` fuerza estado desactivado. Los tres enlaces retornan vacíos cuando falta cualquier gate. No hace solicitudes ni envíos, almacena correos ni verifica que el servicio de la URL funcione.

Usar `signup_html` para sustituir `%%NEWSLETTER_SIGNUP%%` y pasar el mismo resultado a `render_newsletter(stories, now, SITE_URL, configuration=newsletter)`. La vista previa vuelve a validar los campos; pasar sólo las dos URLs posicionales de la firma antigua ya no permite activar su llamada al alta. Así portada y boletín comparten el mismo estado. El boletín muestra también los enlaces de privacidad y baja cuando la configuración está completa.

**Importante:** el flujo actual solo genera la página, **no envía emails**. Para activar el envío diario real se necesitan credenciales del proveedor guardadas en GitHub Secrets o, preferiblemente, campañas programadas dentro del proveedor, una lista de destinatarios confirmados y una fase de prueba con un destinatario autorizado. La periodicidad semanal y la segmentación por categorías o regiones deben configurarse en el proveedor o en una etapa posterior, sin afirmar que ya funcionan.

Los correos y registros de consentimiento deben circular entre lector y proveedor, con acceso del responsable real de la lista; GitHub Pages sólo enlaza al servicio externo. Acordar y documentar con el proveedor qué datos recoge, finalidades, acceso, terceros, país de almacenamiento, retención, exportación y eliminación. No afirmar cumplimiento de la legislación chilena u otras jurisdicciones sin revisión vigente. Ni el nombre del proveedor ni una URL HTTPS prueban consentimiento o adecuación legal. Estos puntos siguen pendientes mientras no exista un proveedor y flujo real revisados.

## Política editorial

- Titulares y enlaces a los artículos de medios originales; sin republicar cuerpos completos.
- Una noticia agrupada por tema y por enlace; la selección prioriza cobertura y actualidad sin afirmar veracidad absoluta.
- Una edición diaria contiene únicamente noticias del historial de 24 h; no atribuirle cobertura semanal.
- No inventar imágenes, resúmenes ni interpretaciones.
- Si hay 0 notas verificadas en la ventana, mostrar un estado vacío correcto.

## QA

`python3 -m unittest discover -s tests -v`

`python3 fetch_noticias.py --solo-render`

Revisar `public/index.html` y `public/boletin-diario.html` en desktop y móvil antes de integrar. Verificar que sin configuración la página nunca simula envíos ni exige emails. Riesgos abiertos: proveedor, legislación aplicable, licencias editoriales, entregabilidad, SPF/DKIM/DMARC, consentimiento y cancelación individual.
