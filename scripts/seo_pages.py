"""Páginas permanentes y recursos SEO del agregador.

No declara noticias ajenas como artículos propios ni envía contenido a buscadores.
"""
import html
import json
from xml.sax.saxutils import escape as xml_escape


def render_about_page(site_url):
    """Página pública atemporal que explica el servicio y sus limitaciones."""
    base = site_url.rstrip("/")
    url = base + "/sobre-el-portal.html"
    esc = lambda value: html.escape(str(value), quote=True)
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": base + "/#website",
                "name": "Noticias del Momento",
                "url": base + "/",
                "inLanguage": "es-CL",
            },
            {
                "@type": "AboutPage",
                "@id": url + "#page",
                "url": url,
                "name": "Sobre Noticias del Momento",
                "description": "Cómo se recopilan y presentan los titulares, las fuentes y los enlaces originales.",
                "inLanguage": "es-CL",
                "isPartOf": {"@id": base + "/#website"},
            },
        ],
    }
    jsonld = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    from scripts.business_sources import render_directory
    directory = render_directory()
    return f"""<!DOCTYPE html>
<html lang="es-CL">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cómo funciona el portal | Noticias del Momento</title>
<meta name="description" content="Conoce cómo Noticias del Momento recopila titulares de Chile y el mundo, agrupa coberturas y enlaza a las fuentes originales de cada publicación.">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_CL">
<meta property="og:site_name" content="Noticias del Momento">
<meta property="og:title" content="Sobre Noticias del Momento">
<meta property="og:description" content="Cómo funciona el agregador, de dónde vienen los titulares y cómo consultar los medios originales.">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(base)}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Sobre Noticias del Momento">
<meta name="twitter:description" content="Cómo funciona el agregador y cómo se atribuyen las noticias a sus fuentes.">
<meta name="twitter:image" content="{esc(base)}/og-image.png">
<meta name="theme-color" content="#282C30">
<link rel="icon" href="{esc(base)}/favicon.svg?v=editorial" type="image/svg+xml">
<link rel="apple-touch-icon" href="{esc(base)}/apple-touch-icon.png?v=editorial">
<script type="application/ld+json">{jsonld}</script>
<style>
:root{{color-scheme:light}}
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;background:#E9E8E2;color:#282C30;font:16px/1.65 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}}
a{{color:#31584A;text-underline-offset:3px}}
a:focus-visible{{outline:3px solid #C04C3E;outline-offset:4px}}
header{{background:#FAFAF7;color:#282C30}}
.wrap{{max-width:900px;margin:0 auto;padding:0 28px}}
header .wrap{{display:flex;align-items:center;justify-content:space-between;gap:20px;padding-top:17px;padding-bottom:17px;flex-wrap:wrap}}
header p{{margin:0;font:700 18px/1.3 Georgia,serif}}
header a{{color:#31584A;font-size:14px}}
main{{max-width:900px;margin:0 auto;padding:50px 28px 56px}}
.eyebrow{{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#626970}}
h1,h2{{font-family:Georgia,"Times New Roman",serif;line-height:1.23;color:#282C30}}
h1{{font-size:clamp(32px,5vw,46px);margin:9px 0 20px;letter-spacing:-.025em}}
h2{{font-size:24px;margin:0 0 11px}}
.intro{{max-width:720px;font-size:19px;line-height:1.55;color:#626970;margin:0 0 36px}}
section{{padding:23px 0;border-top:1px solid #D7DBD4;max-width:760px}}
section p{{margin:0;color:#626970}}
.source-group{{margin-top:16px;padding:10px 0;border-top:1px solid #D7DBD4}}
.source-group summary{{cursor:pointer;font-weight:600}}
.source-group ul{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 20px;list-style:none;margin:16px 0 0;padding:0}}
.source-group li{{min-width:0;overflow-wrap:anywhere}}
.source-group li span{{display:block;font-size:12px;color:#626970}}
@media(max-width:600px){{.source-group ul{{grid-template-columns:minmax(0,1fr)}}}}
footer{{background:#202529;color:#CED1D6;padding:25px 0;font-size:13px}}
footer a{{color:#F7F6F2}}
footer .wrap{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
@media(max-width:600px){{main{{padding:32px 18px 42px}}.wrap{{padding-left:18px;padding-right:18px}}.intro{{font-size:17px}}}}
</style>
</head>
<body>
<header><div class="wrap"><p>Noticias del Momento</p><a href="{esc(base)}/">Volver a la portada</a></div></header>
<main id="contenido">
<p class="eyebrow">Información del portal</p>
<h1>Sobre Noticias del Momento</h1>
<p class="intro">Reunimos titulares de actualidad de Chile y del mundo para facilitar su consulta y el acceso a los medios que publicaron cada noticia.</p>
<section aria-labelledby="origen"><h2 id="origen">Origen de las noticias</h2>
<p>El sitio consulta fuentes RSS de Google Noticias y algunos medios. Cuando está configurado, también utiliza GNews. Los titulares, fechas y enlaces proceden de esas fuentes: no son artículos escritos por este portal.</p></section>
<section aria-labelledby="seleccion"><h2 id="seleccion">Selección y actualizaciones</h2>
<p>Un proceso automatizado agrupa titulares similares, organiza las noticias por categorías y prioriza la actualidad y la cobertura de distintos medios. La publicación está programada aproximadamente cada hora; la disponibilidad depende de las fuentes y del servicio de publicación. La portada muestra una ventana reciente de noticias, no un archivo histórico completo. Para detectar tendencias y coincidencias entre publicaciones se conserva durante un máximo de ocho días un registro acotado de titulares, fechas, enlaces, categorías y medios. No contiene artículos completos, fotografías ni datos personales de lectores; sus resultados se muestran solo cuando existe suficiente información para compararlos.</p></section>
<section aria-labelledby="atribucion"><h2 id="atribucion">Fuentes y responsabilidad editorial</h2>
<p>El título de cada noticia abre la publicación original. El nombre del medio se indica junto al titular y se conserva al agrupar coberturas. Las fotografías y los breves extractos, cuando aparecen, proceden de las fuentes. El portal no sustituye el contenido original ni verifica independientemente cada afirmación de terceros.</p></section>
<section aria-labelledby="agenda"><h2 id="agenda">Agenda de eventos</h2>
<p>La sección Agenda muestra eventos públicos de Chile tomados de fuentes oficiales (municipios, recintos culturales y ticketeras) o revisados a mano desde la publicación del organizador. Solo se publican actividades con fecha, comuna y enlace a la fuente, y cada una se mantiene hasta su fecha de realización. Confirma fecha, hora y acceso con el organizador antes de asistir.</p></section>
<section aria-labelledby="archivo"><h2 id="archivo">Últimos 7 días</h2>
<p>La portada muestra las últimas 24 horas. Los titulares de los siete días anteriores pueden consultarse en el <a href="{esc(base)}/archivo/">archivo por día</a>, ordenados por sección y con enlace a cada medio. Esas páginas no se indexan en buscadores y se eliminan a los siete días.</p></section>
<section aria-labelledby="funciones"><h2 id="funciones">Opciones para lectores</h2>
<p>Puedes cambiar la presentación y marcar noticias como favoritas en este navegador. Para señalar incorporaciones desde tu visita anterior, se recuerda localmente la fecha de la última edición visitada. No se guarda un historial de noticias abiertas ni se envía ese dato a un servidor. La posición, la búsqueda y las secciones desplegadas se conservan en la entrada de navegación de la pestaña para facilitar el botón Atrás, sin enviar ese estado al servidor. La página también ofrece una <a href="{esc(base)}/boletin-diario.html">vista previa del boletín diario</a>, pero la suscripción por correo solo estará disponible cuando se conecte un proveedor de envíos y bajas.</p></section>
{directory}
</main>
<footer><div class="wrap"><span>Noticias del Momento · Agregador informativo</span><a href="{esc(base)}/">Portada</a></div></footer>
</body></html>"""


def render_sitemap(site_url, now_iso):
    """Incluir solo páginas canónicas e indexables que publica nuestro dominio."""
    base = site_url.rstrip("/")
    home, about = xml_escape(base + "/"), xml_escape(base + "/sobre-el-portal.html")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{home}</loc><lastmod>{xml_escape(now_iso)}</lastmod></url>\n'
        f'  <url><loc>{about}</loc></url>\n'
        '</urlset>\n'
    )
