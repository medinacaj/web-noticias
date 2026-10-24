"""Agenda de eventos validados por el proyecto eventos-biobio (Biobío y resto de Chile).

Solo se publica la lista `events` de los snapshots versionados de ese proyecto,
que ya pasaron su filtro de calidad: `crawled_events.json` (Biobío) y
`national_events.json` (resto del país, con la región de cada comuna). Los
`possible_events` y candidatos pendientes de revisión nunca se muestran. Si un
snapshot no responde se usa el otro; sin eventos próximos, la sección no
aparece y la portada se publica igual.
"""
from datetime import date, datetime, time as clock
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
        hhmm = _text(item.get("time"), 5)
        result.append({
            "title": title, "commune": commune, "region": region, "date": start, "end_date": end,
            "time": hhmm if TIME_RE.match(hhmm) else "",
            "venue": _text(item.get("venue"), 90),
            "price": _text(item.get("price_text"), 70),
            "free": item.get("price_status") == "free",
            "category": _text(item.get("category"), 30),
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


WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def _moment(day, hhmm):
    hour, minute = (int(x) for x in (hhmm or "00:00").split(":"))
    return datetime.combine(day, clock(hour, minute), TZ_CHILE).isoformat()


def _when(event, today):
    """Fecha legible para la línea de metadatos, como «hace 2 h» en las noticias."""
    start, end = event["date"], event["end_date"]
    shown = max(start, today)
    if shown == today:
        label = "Hoy"
    elif (shown - today).days == 1:
        label = "Mañana"
    else:
        label = f"{WEEKDAYS[shown.weekday()]} {shown.day} {MONTHS[shown.month - 1]}"
    if end > shown:
        label += f" al {end.day} {MONTHS[end.month - 1]}"
    return label + (f', {event["time"]} h' if event["time"] else "")


def render_filters(events):
    """Botones con el mismo estilo que las opciones de vista; ocultos sin JavaScript."""
    regions = sorted({e["region"] for e in events})
    some_free = any(e["free"] for e in events) and not all(e["free"] for e in events)
    if len(regions) < 2 and not some_free:
        return ""
    buttons = []
    if len(regions) > 1:
        buttons.append('<button type="button" class="density-switch" data-agenda-region="" '
                       'aria-pressed="true">Todo Chile</button>')
        buttons += [f'<button type="button" class="density-switch" data-agenda-region="{esc(r)}" '
                    f'aria-pressed="false">{esc(r)}</button>' for r in regions]
    if some_free:
        buttons.append('<button type="button" class="density-switch" data-agenda-free '
                       'aria-pressed="false">Solo gratis</button>')
    return (f'<div class="agenda-filters" data-agenda-filters hidden role="group" '
            f'aria-label="Filtrar eventos">{"".join(buttons)}</div>')


def render_agenda(events, now, number=None, source_mark=None):
    """Misma estructura que una sección de noticias: encabezado numerado y tarjetas compactas."""
    if not events:
        return ""
    today = now.astimezone(TZ_CHILE).date()
    cards = []
    for i, event in enumerate(events):
        shown = max(event["date"], today)
        label = event["category"] or "Evento"
        mark = source_mark({"sources": [event["source"]], "source_url": event["link"],
                            "link": event["link"]}) if source_mark else ""
        badge = (f'<span class="source-country">{esc(event["status"])}</span>'
                 if event["status"] and event["status"].lower() != "confirmado" else "")
        free = '<span class="source-country">Gratis</span>' if event["free"] else ""
        dek = " · ".join(esc(v) for v in (event["venue"], event["price"]) if v)
        cards.append(
            f'<li class="cat-agenda" data-region="{esc(event["region"])}"{" data-free" if event["free"] else ""}'
            f'{" data-extra" if i >= 5 else ""}><article class="compact">'
            f'<figure class="media media--source media--date" role="img" '
            f'aria-label="{shown.day} de {MONTHS[shown.month - 1]}">'
            f'<span class="source-visual"><span class="date-mark"><span class="date-day">{shown.day}</span>'
            f'<span class="date-month">{MONTHS[shown.month - 1]}</span></span></span></figure>'
            f'<div class="news-body"><p class="kicker">{esc(label)} · {esc(event["commune"])}</p>'
            f'<h3><a href="{esc(event["link"])}" target="_blank" rel="noopener" data-countries="" '
            f'data-cat="Agenda" data-key="agenda" '
            f'data-sources="{esc(json.dumps([event["source"]], ensure_ascii=False))}">{esc(event["title"])}</a></h3>'
            f'{f"<p class=\"dek\">{dek}</p>" if dek else ""}'
            f'<p class="meta"><span class="src">{mark}<span class="source-name">{esc(event["source"])}</span></span>'
            f'<span class="source-country">{esc(event["region"])}</span>{free}{badge}'
            f'<time datetime="{_moment(shown, event["time"])}">{esc(_when(event, today))}</time></p>'
            f'</div></article></li>')
    count = len(events)
    more = (f'<button type="button" class="show-more" data-show-more aria-controls="noticias-agenda" '
            f'data-step="6">Ver más eventos <span aria-hidden="true">↓</span></button>' if count > 6 else "")
    num = f'<span class="section-num">{number:02d}</span>' if number else ""
    return (f'<section class="section cat-agenda" id="cat-agenda" aria-labelledby="titulo-agenda">'
            f'<div class="section-head">{num}<h2 id="titulo-agenda">Agenda</h2>'
            f'<span class="section-count" data-agenda-count>{count} {"evento" if count == 1 else "eventos"}</span></div>'
            f'{render_filters(events)}'
            f'<div class="section-grid" id="noticias-agenda"><ul class="compact-list">{"".join(cards)}</ul></div>'
            f'{more}</section>')
