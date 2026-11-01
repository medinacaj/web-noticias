"""Agenda de eventos validados (Biobío y resto de Chile).

Solo se publica la lista `events` de tres archivos:
- los snapshots del recolector `eventos/` (antes el repositorio eventos-biobio),
  que el workflow «Actualizar eventos» guarda en la rama `events-data`:
  `crawled_events.json` (Biobío) y `national_events.json` (resto del país);
- `eventos/agenda_manual.json`: eventos que el responsable revisó a mano desde
  la publicación oficial del organizador (p. ej. afiches de Instagram).
Los `possible_events` y candidatos pendientes de revisión nunca se muestran.
Si un archivo falta o no se puede leer se usan los demás; sin eventos
próximos, la sección no aparece y la portada se publica igual.
"""
from datetime import date, datetime, time as clock
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ".events-data/eventos/"  # checkout de la rama events-data en el workflow
# (variable de entorno, ruta o URL por omisión, región cuando el archivo no la trae)
SNAPSHOTS = (
    ("EVENTOS_BIOBIO_URL", DATA_DIR + "crawled_events.json", "Biobío"),
    ("EVENTOS_NACIONALES_URL", DATA_DIR + "national_events.json", ""),
    ("EVENTOS_MANUAL_URL", "eventos/agenda_manual.json", ""),
)
MAX_BYTES = 5_000_000
MAX_EVENTS = 36
# Tope por región: Santiago no desplaza al Biobío ni a otras regiones con menos eventos.
MAX_PER_REGION = 12
TIMEOUT = 10
TZ_CHILE = ZoneInfo("America/Santiago")
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

esc = lambda value: html.escape(str(value), quote=True)


def fetch_snapshot(url):
    """Archivo local (relativo a la raíz del repositorio) o URL https."""
    if not url.startswith("https://"):
        with open(ROOT / url, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
    else:
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
            # Póster o imagen oficial publicada por el organizador (se referencia, no se copia).
            "image": _https(item.get("image_url")),
        })
    return _ordered(result, today)[:limit]


def _ordered(events, today):
    return sorted(events, key=lambda e: (max(e["date"], today), e["time"] or "99:99", e["title"]))


def _balanced(events, limit=MAX_EVENTS, per_region=MAX_PER_REGION):
    """Los más próximos, con un tope por región para que todas tengan presencia."""
    chosen, per = [], {}
    for event in events:
        if per.get(event["region"], 0) < per_region:
            per[event["region"]] = per.get(event["region"], 0) + 1
            chosen.append(event)
        if len(chosen) == limit:
            break
    return chosen


def coverage_summary(payload, today, communes_path=None):
    """Indicadores de la última captura regional, no una promesa de cobertura.

    Los candidatos no se publican. La cobertura por comuna considera únicamente
    eventos vigentes aceptados por el recolector (no la agenda editorial manual).
    """
    if not isinstance(payload, dict):
        return {}
    runs = [r for r in payload.get("runs", []) if isinstance(r, dict)]
    if not runs:
        return {}
    try:
        path = communes_path or (ROOT / "eventos/config/communes.json")
        with open(path, encoding="utf-8") as f:
            communes = [c["name"] for c in json.load(f).get("communes", [])
                        if isinstance(c, dict) and isinstance(c.get("name"), str)]
    except (OSError, ValueError, TypeError, KeyError):
        communes = []
    accepted = upcoming_events(payload, today, "Biobío", limit=None)
    covered = {e["commune"] for e in accepted}
    ok = [r for r in runs if r.get("ok") and isinstance(r.get("http_status"), int)
          and 200 <= r["http_status"] < 300]
    failed = [r.get("source_name", "") for r in runs if r not in ok]
    pending = payload.get("possible_events")
    pending = pending if isinstance(pending, list) else []
    reasons = {}
    for item in pending:
        if isinstance(item, dict) and isinstance(item.get("reason"), str):
            reason = item["reason"][:110]
            reasons[reason] = reasons.get(reason, 0) + 1
    generated = str(payload.get("generated_at") or "")[:19]
    if not re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d", generated):
        generated = ""
    skipped = payload.get("skipped_by_cadence")
    skipped = len(skipped) if isinstance(skipped, list) else 0
    metrics = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "generated_at": generated, "attempted": len(runs), "responded": len(ok),
        "skipped": skipped,
        "revalidation_attempts": metrics.get("revalidation_attempts", 0),
        "revalidated_ok": metrics.get("revalidated_ok", 0),
        "events": len(accepted), "pending": len(pending),
        "communes_total": len(communes),
        "communes_covered": len(covered.intersection(communes)),
        "missing": [name for name in communes if name not in covered],
        "failed": [name for name in failed if name][:6],
        "top_reasons": sorted(reasons.items(), key=lambda item: (-item[1], item[0]))[:3],
    }


def render_coverage(quality):
    """Panel expandible de transparencia, sin alterar las tarjetas de Agenda."""
    if not quality or not quality.get("attempted"):
        return ""
    pairs = (
        ("Fuentes consultadas", quality["attempted"]),
        ("Fuentes que respondieron", quality["responded"]),
        ("Eventos regionales vigentes en el rastreo", quality["events"]),
        ("Candidatos guardados para revisión", quality["pending"]),
    )
    if quality.get("skipped"):
        pairs += (("Fuentes omitidas por cadencia", quality["skipped"]),)
    if quality.get("revalidation_attempts"):
        pairs += (("Fichas previas revalidadas",
                   f'{quality.get("revalidated_ok", 0)} de {quality["revalidation_attempts"]}'),)
    cells = "".join(
        f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>'
        for label, value in pairs
    )
    covered = quality.get("communes_covered", 0)
    total = quality.get("communes_total", 0)
    if total:
        cells += (f'<div><dt>Comunas con eventos</dt><dd>{covered} de {total}</dd></div>')
    missing = quality.get("missing") or []
    missing_text = ", ".join(missing[:8])
    if len(missing) > 8:
        missing_text += f" y {len(missing) - 8} más"
    issue = '<p><strong>Comunas sin eventos detectados:</strong> ' + esc(missing_text) + '</p>' if missing else ""
    failed = quality.get("failed") or []
    failure = ('<p><strong>Fuentes con fallas en la última captura:</strong> '
               + esc(", ".join(failed)) + '</p>') if failed else ""
    reasons = quality.get("top_reasons") or []
    reasons_html = ('<p><strong>Principales motivos de revisión:</strong> '
                    + esc("; ".join(f"{reason} ({count})" for reason, count in reasons)) + '</p>'
                    if reasons else "")
    generated = quality.get("generated_at")
    timestamp = f'<p>Captura de datos: {esc(generated.replace("T", " "))} (hora registrada por el recolector).</p>' if generated else ""
    return ('<details class="agenda-quality"><summary>Cobertura y calidad de la agenda</summary>'
            '<div class="agenda-quality-body"><dl>' + cells + '</dl>' + timestamp
            + issue + failure + reasons_html
            + '<p>Estas cifras corresponden al último rastreo de Biobío, no al total '
            'nacional ni a los eventos agregados manualmente. Un candidato no es '
            'un evento confirmado y una fuente accesible no garantiza que publique eventos.</p>'
            '</div></details>')


def load_agenda(now, fetch=fetch_snapshot, snapshots=None, coverage=None):
    """Nunca interrumpe la publicación de noticias: un snapshot que falla solo se omite."""
    today = now.astimezone(TZ_CHILE).date()
    events, seen = [], set()
    for variable, default_url, region in snapshots or SNAPSHOTS:
        url = os.environ.get(variable, default_url).strip()
        if not url:
            continue
        try:
            payload = fetch(url)
            found = upcoming_events(payload, today, region, limit=None)
            if coverage is not None and region == "Biobío":
                coverage.update(coverage_summary(payload, today))
        except Exception as error:
            print(f"[aviso] Agenda: {variable} no disponible: {error}")
            continue
        for event in found:
            if event["link"] not in seen:
                seen.add(event["link"])
                events.append(event)
            elif variable == "EVENTOS_MANUAL_URL":
                # Una corrección editorial revisada prevalece sobre el dato
                # extraído automáticamente cuando ambos apuntan a la misma ficha.
                events = [event if e["link"] == event["link"] else e for e in events]
    events = _balanced(_ordered(events, today))
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


def _figure(event, shown):
    """Imagen oficial como en las noticias; sin imagen, la fecha ocupa su lugar."""
    if event["image"]:
        return (f'<figure class="media"><img src="{esc(event["image"])}" alt="" width="1200" height="630" '
                f'loading="lazy" decoding="async" referrerpolicy="no-referrer"></figure>')
    return (f'<figure class="media media--source media--date" role="img" '
            f'aria-label="{shown.day} de {MONTHS[shown.month - 1]}">'
            f'<span class="source-visual"><span class="date-mark"><span class="date-day">{shown.day}</span>'
            f'<span class="date-month">{MONTHS[shown.month - 1]}</span></span></span></figure>')


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


def render_agenda(events, now, number=None, source_mark=None, coverage=None):
    """Misma estructura que una sección de noticias: encabezado numerado y tarjetas compactas."""
    if not events and not coverage:
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
            f'{_figure(event, shown)}'
            f'<div class="news-body"><p class="kicker">{esc(label)} · {esc(event["commune"])}</p>'
            f'<h3><a href="{esc(event["link"])}" rel="noopener" data-countries="" '
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
            f'{more}{render_coverage(coverage)}</section>')
