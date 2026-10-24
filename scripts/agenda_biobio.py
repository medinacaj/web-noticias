"""Agenda de eventos validados por el proyecto eventos-biobio.

Solo se publica la lista `events` del snapshot versionado de ese proyecto, que
ya pasó su filtro de calidad. Los `possible_events` y candidatos pendientes de
revisión nunca se muestran. Si el snapshot no responde o no hay eventos
próximos, la sección no aparece y la portada se publica igual.
"""
from datetime import date
import html
import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

DEFAULT_URL = ("https://raw.githubusercontent.com/medinacaj/eventos-biobio/"
               "claude/eventos-biobio-v1/data/crawled_events.json")
PROJECT_URL = "https://github.com/medinacaj/eventos-biobio"
MAX_BYTES = 5_000_000
MAX_EVENTS = 6
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
    text = " ".join(str(value or "").split())
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


def upcoming_events(payload, today, limit=MAX_EVENTS):
    """Eventos validados vigentes (fin >= hoy), no cancelados y con enlace a su fuente."""
    items = payload.get("events") if isinstance(payload, dict) else None
    result, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        title, commune = _text(item.get("title"), 160), _text(item.get("commune"), 60)
        start, link = _day(item.get("date")), _https(item.get("source_url"))
        if not (title and commune and start and link):
            continue
        end = _day(item.get("end_date"))
        end = end if end and end >= start else start
        status = _text(item.get("status"), 40)
        if end < today or status.lower() == "cancelado" or link in seen:
            continue
        seen.add(link)
        time = _text(item.get("time"), 5)
        result.append({
            "title": title, "commune": commune, "date": start, "end_date": end,
            "time": time if TIME_RE.match(time) else "",
            "venue": _text(item.get("venue"), 90),
            "price": _text(item.get("price_text"), 70),
            "status": status, "source": _text(item.get("source"), 70) or urlsplit(link).hostname,
            "link": link,
        })
    result.sort(key=lambda event: (max(event["date"], today), event["time"] or "99:99", event["title"]))
    return result[:limit]


def load_agenda(now, url=None, fetch=fetch_snapshot):
    """Nunca interrumpe la publicación de noticias: ante cualquier error devuelve []."""
    url = (url if url is not None else os.environ.get("EVENTOS_BIOBIO_URL", DEFAULT_URL)).strip()
    if not url:
        return []
    try:
        events = upcoming_events(fetch(url), now.astimezone(TZ_CHILE).date())
    except Exception as error:
        print(f"[aviso] Agenda Biobío no disponible: {error}")
        return []
    print(f"Agenda Biobío: {len(events)} eventos próximos validados")
    return events


def _when(event, today):
    start, end = event["date"], event["end_date"]
    if end > start:
        label = f"Hasta el {end.day} {MONTHS[end.month - 1]}" if start <= today else \
            f"{start.day} {MONTHS[start.month - 1]} al {end.day} {MONTHS[end.month - 1]}"
    else:
        label = "Hoy" if start == today else ("Mañana" if (start - today).days == 1 else "")
    return label


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
        cards.append(
            f'<li><article class="agenda-item">'
            f'<time class="agenda-date" datetime="{shown.isoformat()}">'
            f'<span class="agenda-day">{shown.day}</span>'
            f'<span class="agenda-month">{MONTHS[shown.month - 1]}</span></time>'
            f'<div class="agenda-body">'
            f'<p class="kicker">{esc(when) + " · " if when else ""}{esc(event["commune"])}</p>'
            f'<h3><a href="{esc(event["link"])}" target="_blank" rel="noopener">{esc(event["title"])}</a></h3>'
            f'{f"<p class=\"agenda-meta\">{details}{badge}</p>" if details or badge else ""}'
            f'<p class="agenda-source">Fuente: {esc(event["source"])}</p>'
            f'</div></article></li>')
    count = len(events)
    return (f'<section class="section cat-agenda" id="cat-agenda" aria-labelledby="titulo-agenda">'
            f'<div class="section-head"><span class="section-num">Biobío</span>'
            f'<h2 id="titulo-agenda">Agenda Biobío</h2>'
            f'<span class="section-count">{count} {"evento" if count == 1 else "eventos"}</span></div>'
            f'<ul class="agenda-list">{"".join(cards)}</ul>'
            f'<p class="agenda-note">Eventos públicos validados por el proyecto '
            f'<a href="{PROJECT_URL}" target="_blank" rel="noopener">Eventos Región del Biobío</a>. '
            f'Confirma fecha, hora y acceso con el organizador antes de asistir.</p></section>')
