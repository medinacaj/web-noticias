"""Newsletter editorial seguro: genera vista previa HTML; jamás envía correos.

El alta y la baja pertenecen a un proveedor externo configurado explícitamente.
No almacenar ni solicitar direcciones de correo en GitHub Pages.
"""
import html
import os
from datetime import timedelta
from urllib.parse import urlsplit


def safe_external_url(value):
    value = (value or "").strip()
    parsed = urlsplit(value)
    return (value if parsed.scheme == "https" and parsed.hostname
            and not parsed.username and not parsed.password
            and not any(c.isspace() for c in value) else "")


def newsletter_stories(stories, now, limit=12):
    """Una noticia por tema agrupado; no repetir URLs ni inventar coberturas."""
    cutoff = now - timedelta(hours=24)
    eligible, urls = [], set()
    for story in stories:
        url = safe_external_url(story.get("link"))
        if not url or url in urls or not story.get("title"):
            continue
        from fetch_noticias import story_time, score
        published = story_time(story)
        if not published or not cutoff <= published <= now:
            continue
        urls.add(url)
        eligible.append(story)
    eligible.sort(key=lambda s: (score(s, now), story_time(s)), reverse=True)
    return eligible[:limit]


def render_newsletter(stories, now, site_url, subscribe_url="", unsubscribe_url=""):
    """HTML público informativo (y base futura de email), no correo enviado."""
    from fetch_noticias import CATEGORY_LABELS, TZ_CHILE, story_time
    base_url = safe_external_url(site_url) or "https://medinacaj.github.io/web-noticias"
    subscribe = safe_external_url(subscribe_url)
    unsubscribe = safe_external_url(unsubscribe_url)
    selected = newsletter_stories(stories, now)
    esc = lambda value: html.escape(str(value or ""), quote=True)
    groups = {}
    for item in selected:
        category = CATEGORY_LABELS.get(item.get("category"), "Actualidad")
        groups.setdefault(category, []).append(item)
    pieces = []
    for category, items in groups.items():
        rows = []
        for item in items:
            sources = ", ".join((item.get("sources") or [])[:2])
            moment = story_time(item)
            day = moment.astimezone(TZ_CHILE).strftime("%d/%m/%Y") if moment else ""
            rows.append(
                '<li style="padding:16px 0;border-bottom:1px solid #dbe1e8">'
                f'<a href="{esc(item["link"])}" style="color:#122940;font-size:19px;font-weight:700;text-decoration:none">'
                f'{esc(item["title"])}</a>'
                f'<p style="font-size:12px;color:#657386;margin:5px 0 0">{esc(sources)} · {esc(day)}</p></li>'
            )
        pieces.append(
            f'<section aria-label="{esc(category)}"><h2 style="font-size:20px;color:#183147;border-bottom:2px solid #dbe1e8;padding-bottom:8px">'
            f'{esc(category)}</h2><ul style="list-style:none;margin:0;padding:0">{"".join(rows)}</ul></section>'
        )
    info = ("<p>No hay noticias suficientes de las últimas 24 horas para generar una edición."
            " Consulta la portada para ver las publicaciones disponibles.</p>" if not selected else "".join(pieces))
    cta = (f'<a href="{esc(subscribe)}" style="display:inline-block;background:#182639;color:#fff;'
           'padding:13px 20px;border-radius:6px;text-decoration:none;font-weight:700">'
           'Suscribirme al boletín</a>' if subscribe else
           '<p role="status" style="color:#596677">Suscripciones próximamente. Todavía no se reciben direcciones de correo.</p>')
    footer = (f'<p><a href="{esc(unsubscribe)}">Gestionar o cancelar suscripción</a></p>'
              if unsubscribe and subscribe else
              '<p>Cuando se active el servicio, cada correo incluirá un enlace para cancelar la suscripción.</p>')
    date = now.astimezone(TZ_CHILE).strftime("%d/%m/%Y")
    return f"""<!doctype html>
<html lang="es-CL"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,follow">
<title>Boletín diario · Noticias del Momento</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#eef2f6;color:#182639;font-family:Arial,Helvetica,sans-serif}}
main{{max-width:730px;margin:28px auto;padding:30px;background:white;border-radius:9px}}
a:focus-visible{{outline:3px solid #237bb0;outline-offset:3px}}
@media(max-width:760px){{main{{margin:0;padding:22px 17px;border-radius:0}}}}
</style></head>
<body><main>
<p style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#63758b">Boletín diario · {esc(date)}</p>
<h1 style="font-size:32px;line-height:1.2;margin-bottom:8px">Noticias del Momento</h1>
<p style="color:#63758b">Resumen editorial automatizado de las últimas 24 horas. Titulares y enlaces originales; sin reescrituras inventadas.</p>
<div style="margin:22px 0">{cta}</div>
{info}
<footer style="margin-top:32px;border-top:1px solid #dbe1e8;padding-top:14px;font-size:13px;color:#63758b">
<p>Esta página es una vista previa pública y no representa un correo enviado.</p>
<p><a href="{esc(base_url)}/">Volver a la portada</a></p>
{footer}
</footer></main></body></html>"""
