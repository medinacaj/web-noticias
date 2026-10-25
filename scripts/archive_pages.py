"""Archivo «Últimos 7 días»: una página por día con los titulares ya registrados.

Decisión del usuario (2026-10-25): la portada sigue mostrando 24 horas; los siete
días anteriores se consultan aquí, una página por día y con `noindex, follow`
(se borran a los siete días y solo contienen titulares enlazados a otros medios).
Los datos salen del registro interno de ocho días (`editorial_signals`): titular,
enlace, sección, fecha y medios. Sin fotografías, resúmenes ni texto de terceros.
"""
from datetime import datetime, timedelta
import html
from zoneinfo import ZoneInfo

TZ_CHILE = ZoneInfo("America/Santiago")
ARCHIVE_DAYS = 7
DIR = "archivo"
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")

esc = lambda value: html.escape(str(value), quote=True)


def _moment(value):
    try:
        moment = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def archive_days(now):
    """Los siete días anteriores a hoy (hora de Chile), del más reciente al más antiguo."""
    today = now.astimezone(TZ_CHILE).date()
    return [today - timedelta(days=offset) for offset in range(1, ARCHIVE_DAYS + 1)]


def day_label(day, short=False):
    if short:
        return f"{WEEKDAYS[day.weekday()][:3]} {day.day}"
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def _by_day(archive, days):
    wanted = set(days)
    grouped = {day: [] for day in days}
    for item in archive or []:
        if not isinstance(item, dict) or not item.get("title") or not item.get("link"):
            continue
        moment = _moment(item.get("published"))
        if moment is None:
            continue
        local = moment.astimezone(TZ_CHILE)
        if local.date() in wanted:
            grouped[local.date()].append((local, item))
    for items in grouped.values():
        items.sort(key=lambda pair: pair[0], reverse=True)
    return grouped


def _head(title, description, url, base):
    return f"""<!DOCTYPE html>
<html lang="es-CL">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#31584A">
<link rel="icon" href="{esc(base)}/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{esc(base)}/apple-touch-icon.png">
<style>
:root{{color-scheme:light dark;--paper:#F2F1ED;--card:#FFFFFF;--ink:#282C30;--muted:#626970;--rule:#D7DBD4;--brand:#31584A;--accent:#C04C3E}}
@media (prefers-color-scheme:dark){{:root{{--paper:#111315;--card:#1C1F23;--ink:#F7F6F2;--muted:#CCD1D6;--rule:#4C545E;--accent:#FF907F}}}}
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif}}
a{{color:inherit;text-underline-offset:3px}}
a:focus-visible,button:focus-visible{{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}}
.wrap{{max-width:960px;margin:0 auto;padding:0 24px}}
header{{background:var(--card);border-bottom:1px solid var(--rule)}}
header .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px}}
.brand{{display:inline-flex;align-items:center;gap:10px;font:700 18px/1.2 "Source Serif 4",Georgia,serif;text-decoration:none}}
.brand svg{{width:32px;height:32px;flex:none}}
.back{{font-size:13px;font-weight:600}}
main{{padding:32px 0 56px}}
.eyebrow{{font:700 11px/1.4 Inter,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0}}
h1{{font:700 clamp(28px,4.5vw,40px)/1.2 "Source Serif 4",Georgia,serif;margin:6px 0 8px}}
.intro{{color:var(--muted);margin:0 0 20px;max-width:720px}}
.days,.filters{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px;padding:0;list-style:none}}
.days a,.filters button{{display:inline-flex;align-items:center;min-height:40px;padding:8px 12px;border:1px solid var(--rule);border-radius:8px;background:var(--card);color:var(--ink);font:600 13px Inter,sans-serif;text-decoration:none;cursor:pointer}}
.days a[aria-current="page"],.filters button[aria-pressed="true"]{{border-color:var(--brand);box-shadow:inset 0 0 0 1px var(--brand)}}
.filters[hidden]{{display:none}}
section{{margin-top:28px}}
h2{{font:700 22px/1.3 "Source Serif 4",Georgia,serif;margin:0 0 10px;padding-bottom:8px;border-bottom:1px solid var(--rule)}}
ol{{list-style:none;margin:0;padding:0;display:grid;gap:8px}}
ol li{{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:12px 14px}}
ol li a{{font:600 16px/1.4 "Source Serif 4",Georgia,serif;text-decoration-thickness:1px}}
.meta{{display:block;margin-top:4px;color:var(--muted);font-size:12px}}
.empty{{color:var(--muted)}}
footer{{border-top:1px solid var(--rule);padding:20px 0;color:var(--muted);font-size:12px}}
@media (max-width:600px){{.wrap{{padding:0 16px}}main{{padding-top:22px}}}}
</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="{esc(base)}/"><svg viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="9" fill="#31584A"/><path d="M12.5 28V12l15 16V12" fill="none" stroke="#F7F6F2" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M12.5 33h15" stroke="#FF907F" stroke-width="2.4" stroke-linecap="round"/></svg>Noticias del Momento</a><a class="back" href="{esc(base)}/">Volver a la portada</a></div></header>
"""


FOOT = """<footer><div class="wrap">Titulares, medios y enlaces proceden de sus fuentes; cada titular abre la publicación original. Este archivo se conserva siete días.</div></footer>
<script>
(function () {
  var box = document.querySelector("[data-archive-filters]");
  if (!box) return;
  var sections = document.querySelectorAll("section[data-section]");
  box.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    var key = button.getAttribute("data-section-filter");
    box.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b === button)); });
    sections.forEach(function (s) { s.hidden = !!key && s.getAttribute("data-section") !== key; });
  });
  box.hidden = false;
})();
</script>
</body>
</html>
"""


def _day_nav(days, current, base):
    links = []
    for day in days:
        attr = ' aria-current="page"' if day == current else ""
        links.append(f'<li><a href="{esc(base)}/{DIR}/{day.isoformat()}.html"{attr}>{esc(day_label(day, short=True))}</a></li>')
    return f'<nav aria-label="Días del archivo"><ul class="days">{"".join(links)}</ul></nav>'


def render_day(day, items, days, base, categories, section_of):
    """Página de un día: titulares agrupados por sección, del más reciente al más antiguo."""
    labels = {c["key"]: c["label"] for c in categories}
    order = [c["key"] for c in categories]
    sections = {}
    for local, item in items:
        category = item.get("category") or ""
        if category not in labels:
            continue
        sections.setdefault(section_of(category), []).append((local, item))
    blocks, buttons = [], ['<button type="button" data-section-filter="" aria-pressed="true">Todas</button>']
    for key in order:
        if key not in sections:
            continue
        rows = []
        for local, item in sections[key]:
            sources = ", ".join(item.get("sources") or [])
            topic = labels[item["category"]]
            extra = f"{topic} · " if topic != labels[key] else ""
            rows.append(f'<li><a href="{esc(item["link"])}" rel="noopener">{esc(item["title"])}</a>'
                        f'<span class="meta">{esc(extra)}{esc(sources)} · <time datetime="{esc(local.isoformat())}">'
                        f'{local:%H:%M}</time></span></li>')
        blocks.append(f'<section data-section="{esc(key)}" aria-labelledby="s-{esc(key)}">'
                      f'<h2 id="s-{esc(key)}">{esc(labels[key])}</h2><ol>{"".join(rows)}</ol></section>')
        buttons.append(f'<button type="button" data-section-filter="{esc(key)}" aria-pressed="false">{esc(labels[key])}</button>')
    count = sum(len(v) for v in sections.values())
    title = f"Titulares del {day_label(day)} | Noticias del Momento"
    url = f"{base}/{DIR}/{day.isoformat()}.html"
    body = (f'<main id="contenido"><div class="wrap"><p class="eyebrow">Últimos 7 días</p>'
            f'<h1>{esc(day_label(day).capitalize())}</h1>'
            f'<p class="intro">{count} {"titular registrado" if count == 1 else "titulares registrados"} ese día, '
            f'en hora de Chile. Para lo más reciente, vuelve a la portada.</p>'
            f'{_day_nav(days, day, base)}'
            + (f'<div class="filters" data-archive-filters hidden role="group" aria-label="Filtrar por sección">{"".join(buttons)}</div>'
               if len(buttons) > 2 else "")
            + ("".join(blocks) if blocks else '<p class="empty">No hay titulares registrados para este día.</p>')
            + '</div></main>')
    description = f"Titulares de Chile y el mundo publicados el {day_label(day)}, con enlace a cada medio."
    return _head(title, description, url, base) + body + FOOT


def render_index(days, grouped, base):
    rows = "".join(
        f'<li><a href="{esc(base)}/{DIR}/{day.isoformat()}.html">{esc(day_label(day).capitalize())}</a>'
        f'<span class="meta">{len(grouped[day])} titulares</span></li>' for day in days)
    body = ('<main id="contenido"><div class="wrap"><p class="eyebrow">Archivo</p><h1>Últimos 7 días</h1>'
            '<p class="intro">La portada muestra las últimas 24 horas. Aquí puedes consultar los titulares '
            'de los siete días anteriores, ordenados por sección.</p>'
            + (f'<ol>{rows}</ol>' if rows else '<p class="empty">Todavía no hay días anteriores registrados.</p>')
            + '</div></main>')
    return _head("Últimos 7 días | Noticias del Momento",
                 "Titulares de los siete días anteriores, por día y sección, con enlace a cada medio.",
                 f"{base}/{DIR}/", base) + body + FOOT


def render_archive(archive, now, site_url, categories, section_of=lambda key: key):
    """{ruta relativa: html} para el índice y cada uno de los siete días."""
    base = site_url.rstrip("/")
    grouped = _by_day(archive, archive_days(now))
    # Solo días con titulares: al empezar el registro no se publican páginas vacías.
    days = [day for day in archive_days(now) if grouped[day]]
    files = {f"{DIR}/index.html": render_index(days, grouped, base)}
    for day in days:
        files[f"{DIR}/{day.isoformat()}.html"] = render_day(day, grouped[day], days, base, categories, section_of)
    return files
