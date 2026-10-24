"""Agenda de eventos validados por el proyecto eventos-biobio (Biobío y resto de Chile).

Solo se publica la lista `events` de los snapshots versionados de ese proyecto,
que ya pasaron su filtro de calidad: `crawled_events.json` (Biobío) y
`national_events.json` (resto del país, con la región de cada comuna). Los
`possible_events` y candidatos pendientes de revisión nunca se muestran. Si un
snapshot no responde se usa el otro; sin eventos próximos, la sección no
aparece y la portada se publica igual.
"""
from datetime import date
import html
import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

RAW_BASE = "https://raw.githubusercontent.com/medinacaj/eventos-biobio/claude/eventos-biobio-v1/data/"
# (variable de entorno, URL por omisión, región cuando el snapshot no la trae)
SNAPSHOTS = (
    ("EVENTOS_BIOBIO_URL", RAW_BASE + "crawled_events.json", "Biobío"),
    ("EVENTOS_NACIONALES_URL", RAW_BASE + "national_events.json", ""),
)
PROJECT_URL = "https://github.com/medinacaj/eventos-biobio"
MAX_BYTES = 5_000_000
MAX_EVENTS = 18
TIMEOUT = 10
TZ_CHILE = ZoneInfo("America/Santiago")
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

esc = lambda value: html.escape(str(value), quote=True)


def fetch_snapshot(url):
    request = Request(url, headers={"User-Agent": "NoticiasDelMomento/2.0 (agenda)"})
    with urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Snapshot de eventos demasiado grande")
    return json.loads(raw.decode("utf-8"))


def _text(value, limit):
    # Algunos editores publican HTML escapado («&lt;p&gt;Sala&lt;/p&gt;»): se muestra solo el texto.
    text = str(value or "")
    for _ in range(2):
        text = html.unescape(text)
    text = " ".join(re.sub(r"<[^>]*>", " ", text).split())
    return text[:limit].rstrip() if text else ""


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _https(url):
    try:
        parts = urlsplit(str(url or "").strip())
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.username or parts.password or "." not in host:
        return ""
    return parts.geturl()


def _tags(value):
    items = value if isinstance(value, list) else []
    tags = []
    for item in items:
        tag = _text(item, 24).lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:2]


def upcoming_events(payload, today, default_region="", limit=MAX_EVENTS):
    """Eventos validados vigentes (fin >= hoy), no cancelados y con enlace a su fuente."""
    items = payload.get("events") if isinstance(payload, dict) else None
    result, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        title, commune = _text(item.get("title"), 160), _text(item.get("commune"), 60)
        start, link = _day(item.get("date")), _https(item.get("source_url"))
        region = _text(item.get("region"), 40) or default_region
        if not (title and commune and region and start and link):
            continue
        end = _day(item.get("end_date"))
        end = end if end and end >= start else start
        status = _text(item.get("status"), 40)
        if end < today or status.lower() == "cancelado" or link in seen:
            continue
        seen.add(link)
        time = _text(item.get("time"), 5)
        result.append({
            "title": title, "commune": commune, "region": region, "date": start, "end_date": end,
            "time": time if TIME_RE.match(time) else "",
            "venue": _text(item.get("venue"), 90),
            "price": _text(item.get("price_text"), 70),
            "free": item.get("price_status") == "free",
            "category": _text(item.get("category"), 30),
            "tags": _tags(item.get("tags")),
            "status": status, "source": _text(item.get("source"), 70) or urlsplit(link).hostname,
            "link": link,
        })
    return _ordered(result, today)[:limit]


def _ordered(events, today):
    return sorted(events, key=lambda e: (max(e["date"], today), e["time"] or "99:99", e["title"]))


def load_agenda(now, fetch=fetch_snapshot, snapshots=None):
    """Nunca interrumpe la publicación de noticias: un snapshot que falla solo se omite."""
    today = now.astimezone(TZ_CHILE).date()
    events, seen = [], set()
    for variable, default_url, region in snapshots or SNAPSHOTS:
        url = os.environ.get(variable, default_url).strip()
        if not url:
            continue
        try:
            found = upcoming_events(fetch(url), today, region, limit=None)
        except Exception as error:
            print(f"[aviso] Agenda: {variable} no disponible: {error}")
            continue
        for event in found:
            if event["link"] not in seen:
                seen.add(event["link"])
                events.append(event)
    events = _ordered(events, today)[:MAX_EVENTS]
    print(f"Agenda: {len(events)} eventos próximos validados en "
          f"{len({e['region'] for e in events})} regiones")
    return events


def _when(event, today):
    start, end = event["date"], event["end_date"]
    if end > start:
        return (f"Hasta el {end.day} {MONTHS[end.month - 1]}" if start <= today else
                f"{start.day} {MONTHS[start.month - 1]} al {end.day} {MONTHS[end.month - 1]}")
    return "Hoy" if start == today else ("Mañana" if (start - today).days == 1 else "")


def _options(values, label, name):
    options = "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in sorted(values))
    return (f'<label>{label}<select data-agenda-filter="{name}">'
            f'<option value="">Todas</option>{options}</select></label>')


def render_filters(events):
    """Controles inertes sin JavaScript: quedan ocultos y se ve la lista completa."""
    regions = {e["region"] for e in events}
    categories = {e["category"] for e in events if e["category"]}
    controls = []
    if len(regions) > 1:
        controls.append(_options(regions, "Región", "region"))
    if len(categories) > 1:
        controls.append(_options(categories, "Categoría", "category"))
    if any(e["free"] for e in events) and not all(e["free"] for e in events):
        controls.append('<label class="agenda-check"><input type="checkbox" data-agenda-filter="free"> '
                        'Solo gratis</label>')
    if not controls:
        return ""
    return (f'<div class="agenda-filters" data-agenda-filters hidden role="group" '
            f'aria-label="Filtrar eventos">{"".join(controls)}'
            f'<p class="agenda-empty" data-agenda-empty hidden>No hay eventos con esos filtros.</p></div>')


def render_agenda(events, now):
    if not events:
        return ""
    today = now.astimezone(TZ_CHILE).date()
    cards = []
    for event in events:
        shown = max(event["date"], today)
        details = " · ".join(esc(v) for v in (event["venue"], event["time"] and f'{event["time"]} h',
                                              event["price"]) if v)
        when = _when(event, today)
        badge = (f'<span class="agenda-status">{esc(event["status"])}</span>'
                 if event["status"] and event["status"].lower() != "confirmado" else "")
        labels = [("region", event["region"])]
        labels += [("category", event["category"])] if event["category"] else []
        labels += [("free", "Gratis")] if event["free"] else []
        labels += [("tag", tag) for tag in event["tags"]]
        tags = "".join(f'<li class="agenda-tag agenda-tag--{kind}">{esc(text)}</li>' for kind, text in labels)
        cards.append(
            f'<li data-region="{esc(event["region"])}" data-category="{esc(event["category"])}"'
            f'{" data-free" if event["free"] else ""}><article class="agenda-item">'
            f'<time class="agenda-date" datetime="{shown.isoformat()}">'
            f'<span class="agenda-day">{shown.day}</span>'
            f'<span class="agenda-month">{MONTHS[shown.month - 1]}</span></time>'
            f'<div class="agenda-body">'
            f'<p class="kicker">{esc(when) + " · " if when else ""}{esc(event["commune"])}</p>'
            f'<h3><a href="{esc(event["link"])}" target="_blank" rel="noopener">{esc(event["title"])}</a></h3>'
            f'{f"<p class=\"agenda-meta\">{details}{badge}</p>" if details or badge else ""}'
            f'<ul class="agenda-tags" aria-label="Etiquetas">{tags}</ul>'
            f'<p class="agenda-source">Fuente: {esc(event["source"])}</p>'
            f'</div></article></li>')
    count = len(events)
    regions = len({e["region"] for e in events})
    scope = f'{regions} {"región" if regions == 1 else "regiones"}'
    return (f'<section class="section cat-agenda" id="cat-agenda" aria-labelledby="titulo-agenda">'
            f'<div class="section-head"><span class="section-num">Chile</span>'
            f'<h2 id="titulo-agenda">Agenda de eventos</h2>'
            f'<span class="section-count" data-agenda-count>{count} {"evento" if count == 1 else "eventos"} · {scope}</span></div>'
            f'{render_filters(events)}'
            f'<ul class="agenda-list">{"".join(cards)}</ul>'
            f'<p class="agenda-note">Eventos públicos validados por el proyecto '
            f'<a href="{PROJECT_URL}" target="_blank" rel="noopener">Eventos Región del Biobío</a>, '
            f'que también rastrea fuentes oficiales del resto del país. '
            f'Confirma fecha, hora y acceso con el organizador antes de asistir.</p></section>')
