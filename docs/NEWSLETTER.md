# Newsletter de Noticias del Momento

## Estado

La web **genera automáticamente una vista previa diaria** en `/boletin-diario.html` al publicarse la página. La vista agrupa un máximo de 12 noticias de las últimas 24 horas disponibles en el historial y enlaza a los medios originales. No existe un servicio de suscripción ni envío conectado por defecto. El boletín **no es un email enviado**.

### Para activar el registro con un proveedor externo

Elegir un servicio que admita confirmación de suscripción (doble opt-in), enlaces de baja individuales por mensaje, protección contra abusos, exportación y eliminación de datos, y política de privacidad clara. Verificar obligaciones aplicables a los destinatarios (incluido Chile), tratamiento de datos y condiciones de titulares/citas. No almacenar direcciones de los suscriptores en el repositorio, en GitHub Actions ni en el navegador para simular registro.

Configurar en GitHub Actions o variables del repositorio:

- `NEWSLETTER_READY=true`: habilita los enlaces de alta *solo* si están presentes todas las demás URLs.
- `NEWSLETTER_SUBSCRIBE_URL=https://...`: URL real, HTTPS, del formulario alojado por el proveedor (el proveedor capta datos y confirmaciones).
- `NEWSLETTER_PRIVACY_URL=https://...`: enlace verificado a la política de privacidad de la suscripción.
- `NEWSLETTER_UNSUBSCRIBE_URL=https://...`: URL pública y verificada para gestionar la baja. **Además**, todo correo debe incluir su enlace de baja individual; una URL general no lo sustituye.

Las tres URLs deben ser HTTPS. El estado predeterminado muestra **«Suscripciones próximamente»** y nunca presenta un formulario falso.

El workflow `.github/workflows/update-news.yml` transmite estas cuatro variables de GitHub Actions al generador. **No tienen valores por defecto y no se activan con la fusión del código**. Para habilitar el enlace real hay que contratar/configurar el proveedor, publicar y revisar las políticas de privacidad y baja, cargar sus URL auténticas en GitHub Actions y decidir expresamente cuándo establecer `NEWSLETTER_READY=true`. Esta configuración no puede hacerse ni validarse usando URL ficticias.

**Importante:** el flujo actual solo genera la página, **no envía emails**. Para activar el envío diario real se necesitan credenciales del proveedor guardadas en GitHub Secrets o, preferiblemente, campañas programadas dentro del proveedor, una lista de destinatarios confirmados y una fase de prueba con un destinatario autorizado. La periodicidad semanal y la segmentación por categorías o regiones deben configurarse en el proveedor o en una etapa posterior, sin afirmar que ya funcionan.

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
