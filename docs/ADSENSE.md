# Preparación de Google AdSense para Web Noticias

**Estado:** integración de código lista para revisión, **publicidad desactivada por defecto**. Sin ingresos, anuncios o aprobación de Google confirmados. Jurisdicción principal: Chile; las normas y consentimientos pueden variar por territorio de audiencia.

## Decisión de diseño

- Usar inicialmente **AdSense Auto Ads**, gestionando los formatos desde la consola de AdSense. No crear tarjetas vacías, bloques promocionales falsos ni scripts con IDs de ejemplo en producción.
- Conservar titulares, tarjetas, menú, navegación y tiempos de carga mientras no esté habilitado.
- Se puede incorporar **solo la metaetiqueta de verificación** con un ID real del editor, sin cargar publicidad ni cookies del script de anuncios.
- El script externo de AdSense se carga únicamente en la portada cuando todas las condiciones explícitas se cumplen.
- No activar formatos que cubran la noticia (anuncios ancla/viñetas) sin evaluar el diseño y la experiencia móvil.

## Limitación del dominio actual

Web Noticias se sirve como proyecto en `https://medinacaj.github.io/web-noticias/`. Su repositorio **no controla** `https://medinacaj.github.io/ads.txt`: generar `/web-noticias/ads.txt` no equivale a un archivo de la raíz del host.

**No es obligatorio comprar un dominio por ahora.** `github.io` está inscrito en la lista pública de sufijos (Public Suffix List) y las normas de AdSense permiten solicitar la revisión de subdominios de esos sufijos. La opción gratuita a evaluar es servir el portal como **sitio de usuario de GitHub Pages** en `https://medinacaj.github.io/`, desde un repositorio llamado `medinacaj.github.io` que el usuario controle. En ese caso la raíz del host podría publicar `https://medinacaj.github.io/ads.txt`, sin cambiar de plataforma. **La aprobación de Google no está confirmada**, y el sitio debe aportar contenido propio de valor suficiente.

**Decisión actual del usuario:** mantener por ahora la URL `https://medinacaj.github.io/web-noticias/`. No mover contenido, no crear el repositorio de raíz ni cambiar `SITE_URL` hasta tener aprobación para esa migración. Con esa URL de proyecto, el generador deja los anuncios deshabilitados para no simular acceso a `/ads.txt` del host. Un dominio propio sigue siendo una alternativa posterior, no un requisito impuesto.

Fuentes: [AdSense: tipos de sitio permitidos](https://support.google.com/adsense/answer/12170421?hl=en), [Public Suffix List actual](https://publicsuffix.org/list/public_suffix_list.dat), [Github Pages: sitios de usuario](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

## Variables de GitHub Actions

En el repositorio `Settings → Secrets and variables → Actions → Variables`, utilizar:

| Nombre | Ejemplo | Propósito |
| --- | --- | --- |
| `ADSENSE_PUBLISHER_ID` | `ca-pub-1234567890123456` | ID real del editor AdSense (16 dígitos). Permite publicar la etiqueta meta de verificación. Es público, no una contraseña. |
| `ADSENSE_READY` | `false` | Solo debe ser `true` después de revisar la aprobación y privacidad. |
| `ADSENSE_PRIVACY_URL` | `https://tudominio.cl/privacidad` | URL pública HTTPS que describa las tecnologías publicitarias, terceros y derechos de los usuarios. |
| `SITE_URL` | `https://medinacaj.github.io` | **Solo si el sitio completo se publica en la raíz del host**; también admite raíz HTTPS de un dominio propio. No cambiar por ahora. |

**Estos son ejemplos, no configuración real.** No ingresar un ID de ejemplo ni afirmar que la aprobación ya existe. Nunca cambiar `SITE_URL` antes de comprobar que la nueva URL raíz contiene realmente el portal y que HTTPS y los enlaces funcionan.

### Dos etapas

**1. Verificación:** definir `ADSENSE_PUBLISHER_ID`; mantener `ADSENSE_READY=false`. El generador incorpora una metaetiqueta de verificación en el `<head>`, pero no carga `adsbygoogle.js`. Google puede aceptar la verificación de propiedad por metaetiqueta según su flujo actual.

**2. Publicidad:** una vez que AdSense marque el sitio como **Listo**, que esté disponible `https://DOMINIO/ads.txt` con el ID verdadero del editor, que se haya publicado una política de privacidad adecuada y que se hayan revisado las opciones de consentimiento aplicables, definir `ADSENSE_READY=true`.

La implementación exige ID válido, `ADSENSE_READY=true`, `ADSENSE_PRIVACY_URL` HTTPS y `SITE_URL` en la raíz de un host admisible: puede ser un dominio propio o el sitio personal `usuario.github.io/`, **pero no** un sitio de proyecto bajo `usuario.github.io/repositorio/`. De lo contrario omite el script y los anuncios.

En una raíz de host admisible se genera `ads.txt` con la directiva de vendedor **DIRECT**; comprobar que está accesible en `https://HOST/ads.txt`. No se publica `ads.txt` desde la subruta GitHub Pages porque no resuelve el requisito real.

El enlace de privacidad se muestra en el pie solo cuando el ID real y la URL HTTPS estén configurados.

## Condiciones legales, editoriales y de experiencia

- **Privacidad:** la política debe identificar al responsable real, qué información y cookies/tratamientos son utilizados por Google, bases y finalidades aplicables, contacto y derechos. No inventar identidad ni el consentimiento; revisar las normas pertinentes de Chile y cualquier otra jurisdicción alcanzada. Configurar, si corresponde, la plataforma de gestión de consentimiento exigida por Google.
- **Contenido:** Google prohíbe monetizar páginas que copian o reproducen contenido de terceros sin comentario, curación u otro valor añadido. La mera agregación y los enlaces no garantizan aprobación. Potenciar explicaciones originales y comparaciones verificadas antes de solicitar la revisión, sin convertir noticias ajenas en propias.
- **Anuncios:** evitar superposiciones intrusivas, anuncios disfrazados de noticias, exceso de anuncios y espacios reservados que deformen la portada. La configuración Auto Ads se controla en la consola de AdSense: revisar formatos, densidad y exclusiones antes de habilitar.
- **Dominio y rendimiento:** verificar el sitio raíz con contenido real, `ads.txt`, HTTPS, Search Console y métricas Core Web Vitals. Ads pueden afectar LCP, CLS e INP una vez activados.
- **Ingresos:** no se pueden estimar sin datos reales de tráfico, país, monetización aprobada, RPM ni demanda publicitaria.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
python3 fetch_noticias.py --solo-render
python3 scripts/audit_seo.py --site public
```

Las pruebas verifican que la configuración incompleta **no** añada solicitudes de Google Ads, etiquetas engañosas ni `ads.txt` ubicado incorrectamente. No sustituyen una revisión de Google, privacidad o licencias de terceros.

### Referencias oficiales

- [Conectar un sitio a AdSense](https://support.google.com/adsense/answer/7584263?hl=es)
- [Añadir un sitio a AdSense](https://support.google.com/adsense/answer/12169212?hl=es-419)
- [Políticas para Editores de Google](https://support.google.com/adsense/answer/10502938)
- [Guía de ads.txt](https://support.google.com/adsense/answer/12171612?hl=es-CL)
- [Cambios en sitios admitidos](https://support.google.com/adsense/answer/12170421?hl=en)

**Puerta de integración GitHub:** este PR modifica el workflow de despliegue y prepara la carga de scripts publicitarios de terceros. El protocolo exige revisión humana antes de fusionarlo, incluso con CI en verde. Mantener el sitio actual y `ADSENSE_READY=false` hasta que el usuario decida si publicar el portal en la raíz `medinacaj.github.io/`.
