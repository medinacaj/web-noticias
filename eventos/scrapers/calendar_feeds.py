"""Calendarios estructurados que publican los sitios oficiales (además del HTML).

Muchos municipios usan WordPress con «The Events Calendar», que expone su agenda
como JSON (`/wp-json/tribe/events/v1/events`) y como iCalendar (`?ical=1`).
Otros enlazan un `.ics` con `<link rel="alternate" type="text/calendar">`.
Son datos estructurados del propio organizador (fecha, hora, lugar), así que se
publican como un evento JSON-LD; los RSS de noticias, en cambio, siguen yendo
solo a revisión (ver scrapers/rss.py).
"""
from datetime import date, datetime, timedelta, timezone
import json
import re
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import metadata
from scrapers.generic_events import _plain

ALLOWED_TYPES = {"municipal", "venue", "university"}
TRIBE_PATH = "/wp-json/tribe/events/v1/events?per_page=50"
ICAL_PATHS = ("/?post_type=tribe_events&ical=1&eventDisplay=list", "/eventos/?ical=1")
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
MAX_EVENTS = 60
TZ_CHILE = ZoneInfo("America/Santiago")


def eligible(source):
    return (bool(source.get("official")) and not source.get("radar_only")
            and source.get("source_type") in ALLOWED_TYPES)


def feed_urls(page_html, page_url):
    """Calendarios enlazados en la portada más los puntos de entrada habituales del sitio."""
    root = "%s://%s" % (urlparse(page_url).scheme, urlparse(page_url).netloc)
    found = []
    for tag in LINK_RE.findall(page_html or ""):
        low = tag.lower()
        href = re.search(r'href=["\']([^"\']+)', tag, re.I)
        if href and "alternate" in low and "text/calendar" in low:
            found.append(urljoin(page_url, href.group(1)))
    if "tribe" in (page_html or "").lower() or not found:
        found += [root + TRIBE_PATH] + [root + p for p in ICAL_PATHS]
    return list(dict.fromkeys(u for u in found if urlparse(u).netloc == urlparse(page_url).netloc))


def _event(source, communes, title, start, end, hhmm, venue, address, locality, url, image, desc, cost):
    names = [c["name"] for c in communes]
    commune = (metadata.detect_commune(locality or "", names)
               or metadata.detect_commune(" ".join(x for x in (venue, address) if x), names)
               or source.get("commune"))
    if not (title and start and commune and url):
        return None
    price_value, price_status = metadata.parse_price(cost or "")
    return {
        "title": title[:200], "description": desc[:1200] or None, "date": start,
        "end_date": end if end and end > start else None, "time": hhmm, "end_time": None,
        "venue": venue or None, "address": address or None, "commune": commune,
        "category": metadata.guess_category(title + " " + desc),
        "price_value": price_value, "price_status": price_status,
        "status": "Confirmado" if hhmm else "Por confirmar",
        "source": source["name"], "source_url": url,
        "source_type": source.get("source_type"), "source_priority": source.get("source_priority", 3),
        "official": True, "image_url": image if image and image.startswith("https://") else None,
        "single_event_page": True,
    }


def events_from_tribe(text, source, communes, ref=None):
    """Respuesta JSON de The Events Calendar (REST v1)."""
    ref = (ref or date.today()).isoformat()
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return []
    out = []
    for item in (data.get("events") if isinstance(data, dict) else None) or []:
        if not isinstance(item, dict):
            continue
        start, end = str(item.get("start_date") or ""), str(item.get("end_date") or "")
        if len(start) < 10 or max(start[:10], end[:10]) < ref:
            continue
        venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
        image = item.get("image") if isinstance(item.get("image"), dict) else {}
        hhmm = None if item.get("all_day") else (start[11:16] or None)
        ev = _event(source, communes, _plain(item.get("title")), start[:10], end[:10] or None,
                    None if hhmm == "00:00" else hhmm, _plain(venue.get("venue")),
                    _plain(venue.get("address")), _plain(venue.get("city")), item.get("url"),
                    image.get("url"), _plain(item.get("description")), _plain(item.get("cost")))
        if ev:
            out.append(ev)
    return out[:MAX_EVENTS]


def _unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text or "")


def _ics_value(value):
    return (value.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\").strip())


def _ics_when(value):
    """'20261024T190000' o '20261024' -> ('2026-10-24', '19:00' | None). Hora UTC (Z) a hora de Chile."""
    m = re.match(r"(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})\d{2}(Z?))?", value or "")
    if not m:
        return None, None
    y, mo, d, hh, mm, utc = m.groups()
    if not hh:
        return "%s-%s-%s" % (y, mo, d), None
    moment = datetime(int(y), int(mo), int(d), int(hh), int(mm))
    if utc:
        moment = moment.replace(tzinfo=timezone.utc).astimezone(TZ_CHILE)
    hhmm = moment.strftime("%H:%M")
    return moment.date().isoformat(), None if hhmm == "00:00" else hhmm


def events_from_ics(text, source, communes, ref=None):
    """VEVENT de un iCalendar. Sin URL propia se usa la del calendario: nunca la portada."""
    ref = (ref or date.today()).isoformat()
    if "BEGIN:VCALENDAR" not in (text or "")[:2000]:
        return []
    out = []
    for block in _unfold(text).split("BEGIN:VEVENT")[1:]:
        fields = {}
        for line in block.split("END:VEVENT")[0].splitlines():
            key, _, value = line.partition(":")
            fields.setdefault(key.split(";")[0].upper(), _ics_value(value))
        start, hhmm = _ics_when(fields.get("DTSTART"))
        end, _ = _ics_when(fields.get("DTEND"))
        if not start or max(start, end or start) < ref:
            continue
        if end and "T" not in fields.get("DTEND", ""):
            # En iCalendar el DTEND de un día completo es exclusivo (día siguiente).
            end = (date.fromisoformat(end) - timedelta(days=1)).isoformat()
        location = fields.get("LOCATION", "")
        url = fields.get("URL", "")
        if not url.startswith("http"):
            continue
        ev = _event(source, communes, _plain(fields.get("SUMMARY")), start, end, hhmm,
                    location.split(",")[0].strip(), location, location, url, None,
                    _plain(fields.get("DESCRIPTION")), "")
        if ev:
            out.append(ev)
    return out[:MAX_EVENTS]


def collect(source, page_html, page_url, communes, fetcher, timeout=20, ref=None):
    """(eventos, feeds que respondieron) de los calendarios del sitio oficial."""
    if not eligible(source):
        return [], []
    events, live = [], []
    for url in feed_urls(page_html, page_url):
        page = fetcher(url, timeout=timeout)
        if not page.ok:
            continue
        found = (events_from_tribe(page.text, source, communes, ref)
                 or events_from_ics(page.text, source, communes, ref))
        if found:
            live.append(url)
            events += found
    seen, unique = set(), []
    for ev in events:  # el mismo calendario suele venir en JSON y en iCal
        key = (ev["source_url"], ev["date"])
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    return unique, live
