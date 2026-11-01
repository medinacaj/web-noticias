"""Planificación responsable de fuentes y revalidación de fichas ya verificadas.

El cron de GitHub sigue siendo diario: estas ventanas definen cuándo una
fuente vuelve a consultarse cuando se ejecuta el proceso, no crean tareas.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit


def refresh_hours(source):
    """Cadencia en horas; mínimo/máximo estrictos para evitar carga excesiva."""
    default = 48 if source.get("radar_only") else (
        12 if source.get("source_type") in {"ticketing", "venue"} else 24)
    try:
        raw = source.get("refresh_interval_hours")
        value = int(raw) if raw is not None else default
        return value if 6 <= value <= 168 else default
    except (TypeError, ValueError, OverflowError):
        return default


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 35:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def due_sources(sources, state, now, force=False):
    """Nunca finge una comprobación HTTP de las fuentes omitidas por cadencia."""
    state = state if isinstance(state, dict) else {}
    due, skipped = [], []
    for source in sources:
        if not source.get("enabled") or source.get("parser") == "none":
            continue
        last = _timestamp((state.get(source["name"]) or {}).get("last_checked_at"))
        interval = refresh_hours(source)
        # Margen ante la variabilidad del cron diario de GitHub.
        span = timedelta(hours=max(6, interval - 2))
        if not force and last and timedelta() <= now - last < span:
            skipped.append(source["name"])
        else:
            due.append(source)
    return due, skipped


def update_state(previous, sources, runs):
    """Persistir el último intento incluso si una fuente se omite en esta corrida."""
    state = dict(previous) if isinstance(previous, dict) else {}
    known = {s["name"]: s for s in sources}
    for run in runs:
        name = run.get("source_name")
        if name not in known:
            continue
        before = state.get(name) or {}
        ok = bool(run.get("ok")) and isinstance(run.get("http_status"), int) and 200 <= run["http_status"] < 300
        checked = run.get("finished_at") or run.get("started_at")
        state[name] = {
            "last_checked_at": checked,
            "last_success_at": checked if ok else before.get("last_success_at"),
            "last_http_status": run.get("http_status"),
            "consecutive_failures": 0 if ok else min(int(before.get("consecutive_failures") or 0) + 1, 999),
            "refresh_interval_hours": refresh_hours(known[name]),
        }
    return {name: state[name] for name in sorted(state) if name in known}


def remembered_event_urls(previous, sources, today, limit_per_source=4):
    """Volver a comprobar fichas que siguen vigentes aunque salgan de la portada.

    Solo URL HTTPS previamente publicada, mismo host de la fuente y evento
    individual con fecha futura. No amplía dominios ni acepta candidatos.
    """
    known = {s["name"]: s for s in sources if s.get("enabled") and not s.get("radar_only")}
    data = previous.get("events") if isinstance(previous, dict) else []
    results = {name: [] for name in known}
    if not isinstance(data, list):
        return results
    for ev in sorted((e for e in data if isinstance(e, dict)),
                     key=lambda e: str(e.get("date") or "")):
        if str(ev.get("end_date") or ev.get("date") or "") < today.isoformat():
            continue
        if str(ev.get("status") or "").lower() == "cancelado":
            continue
        refs = [{"name": ev.get("source"), "url": ev.get("source_url")}] + (
            ev.get("sources") if isinstance(ev.get("sources"), list) else [])
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            name, url = ref.get("name"), ref.get("url")
            source = known.get(name)
            if not source or not isinstance(url, str):
                continue
            parsed, base = urlsplit(url), urlsplit(source["url"])
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.hostname.removeprefix("www.") != (base.hostname or "").removeprefix("www.")
                    or not parsed.path.strip("/") or url == source["url"]):
                continue
            bucket = results[name]
            if url not in bucket and len(bucket) < limit_per_source:
                bucket.append(url)
    return results
