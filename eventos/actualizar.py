"""Actualización sin interfaz: rastrea las fuentes y guarda el resultado en
archivos JSON. En web-noticias el workflow «Actualizar eventos» lo ejecuta a
diario y guarda los snapshots en la rama de datos `events-data`; la Agenda
del portal solo publica su lista `events`.

Uso:
    python3 actualizar.py                    # todas las fuentes habilitadas
    python3 actualizar.py --only "Teatro Biobío"
    python3 actualizar.py --no-update-sources
    python3 actualizar.py --nacional         # fuentes del resto de Chile
    python3 actualizar.py --snapshot X.json --estado-fuentes Y.json
                                             # rutas fuera del código (workflow)

Escribe:
    data/crawled_events.json   eventos rastreados + historial, corridas,
                               posibles eventos y fuentes candidatas
    config/sources.json        verified_live / last_live_check según la
                               respuesta REAL de cada fuente en esta corrida

Con --nacional usa config/national_sources.json y las 346 comunas de
config/chile_communes.json, y escribe data/national_events.json. Cada evento
lleva la región de su comuna. El flujo del Biobío no cambia.
"""
import argparse
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import db  # noqa: E402
import discovery  # noqa: E402
import source_planning  # noqa: E402
from scrapers import event_page, runner  # noqa: E402
from scrapers.common import fetch  # noqa: E402

CRAWLED_PATH = os.path.join(BASE_DIR, "data", "crawled_events.json")
NATIONAL_PATH = os.path.join(BASE_DIR, "data", "national_events.json")
_STATUS_PREFIX = re.compile(
    r"^(No verificada en vivo:.*?contra esta URL\.|Verificada en vivo el [^.]*\.|"
    r"Última verificación en vivo [^.]*\.(?: Error: [^\n]*?\.)?)\s*", re.S)


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def update_sources_file(path, runs):
    """Marca verified_live según la última petición real a cada fuente."""
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    by_name = {r["source_name"]: r for r in runs}
    changed = 0
    for s in cfg["sources"]:
        r = by_name.get(s["name"])
        if not r:
            continue
        ok = bool(r["ok"]) and r.get("http_status") is not None and 200 <= r["http_status"] < 300
        day = (r.get("finished_at") or "")[:10]
        if ok:
            prefix = "Verificada en vivo el %s (HTTP %s; %s página(s), %s evento(s))." % (
                day, r["http_status"], r.get("pages_fetched"), r.get("events_found"))
        else:
            err = (r.get("error") or "sin detalle").replace(".", ",")[:160]
            prefix = "Última verificación en vivo %s: falló. Error: %s." % (day, err)
        s["notes"] = prefix + " " + _STATUS_PREFIX.sub("", s.get("notes") or "")
        s["notes"] = s["notes"].strip()
        s["verified_live"] = ok
        if ok and s.get("url_candidates") and r.get("source_url"):
            s["url"] = r["source_url"]
            s["url_evidence"] = "dominio_candidato_verificado_en_vivo"
            s["enabled"] = True
            del s["url_candidates"]
        s["last_live_check"] = {"at": r.get("finished_at"), "ok": ok, "http_status": r.get("http_status"),
                                "error": r.get("error")}
        changed += 1
    cfg["_notes"] = ("verified_live=true solo si la URL respondió (HTTP 2xx) a una petición real hecha por "
                     "actualizar.py en su última corrida; ver last_live_check. url_evidence indica de dónde salió la URL.")
    _write_json(path, cfg)
    return changed


def with_regions(items, communes):
    """Agrega la región de la comuna (si el listado de comunas la conoce)."""
    region = {c["name"]: c.get("region") for c in communes}
    for item in items:
        item["region"] = region.get(item.get("commune"))
    return items


def main(argv=None, fetcher=fetch, crawled_path=None, sources_path=None, communes_path=None):
    ap = argparse.ArgumentParser(description="Rastrea las fuentes y guarda data/crawled_events.json")
    ap.add_argument("--only", action="append", help="nombre exacto de una fuente (repetible)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-update-sources", action="store_true",
                    help="no modificar config/sources.json")
    ap.add_argument("--force", action="store_true",
                    help="Forzar comprobación sin cadencia (uso editorial manual)")
    ap.add_argument("--nacional", action="store_true",
                    help="fuentes del resto de Chile -> data/national_events.json")
    ap.add_argument("--snapshot", help="ruta del snapshot (se lee el anterior y se reescribe)")
    ap.add_argument("--estado-fuentes",
                    help="copia de las fuentes donde anotar el estado en vivo; config/ no se modifica")
    args = ap.parse_args(argv)
    national = args.nacional
    crawled_path = crawled_path or args.snapshot or (NATIONAL_PATH if national else CRAWLED_PATH)
    sources_path = sources_path or (discovery.NATIONAL_SOURCES_PATH if national else discovery.SOURCES_PATH)
    status_path = sources_path
    if args.estado_fuentes:
        status_path = args.estado_fuentes
        os.makedirs(os.path.dirname(os.path.abspath(status_path)), exist_ok=True)
        with open(sources_path, encoding="utf-8") as src, open(status_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())
    communes_path = communes_path or (discovery.CHILE_COMMUNES_PATH if national else discovery.COMMUNES_PATH)

    sources = discovery.load_sources(sources_path)
    communes = discovery.load_communes(communes_path)
    conn = db.connect(":memory:")
    db.init_db(conn)
    try:
        with open(crawled_path, encoding="utf-8") as f:
            previous_data = json.load(f)
    except (OSError, ValueError):
        previous_data = {}
    state = previous_data.get("source_state") if isinstance(previous_data, dict) else {}
    planned = [s for s in sources if not args.only or s["name"] in args.only]
    due, skipped = source_planning.due_sources(planned, state, datetime.now(timezone.utc),
                                               force=args.force or bool(args.only))
    if not due and skipped:
        # La validación del snapshot exige una respuesta HTTP de ESTA ejecución.
        # Si el workflow se dispara nuevamente antes de que venza cualquier
        # ventana (p. ej. tras fusionar un PR), sondear hasta tres fuentes con
        # última respuesta exitosa; no reutilizar éxitos antiguos como nuevos.
        def good_last_response(src):
            previous_status = ((state or {}).get(src["name"]) or {}).get("last_http_status")
            return isinstance(previous_status, int) and 200 <= previous_status < 300
        priority = sorted(planned, key=lambda src: (not good_last_response(src), src["name"]))
        due = priority[:3]
        forced_names = {src["name"] for src in due}
        skipped = [name for name in skipped if name not in forced_names]
    remembered = source_planning.remembered_event_urls(previous_data, due,
                                                        datetime.now(ZoneInfo("America/Santiago")).date())
    # Continuidad del historial. Las fichas sin datos estructurados no se arrastran:
    # se vuelven a extraer con la regla vigente (y desaparecen si ya no la cumplen).
    previous = db.load_crawled(conn, crawled_path, communes, skip_tags=(event_page.PAGE_TAG,))
    # Los timestamps tienen precisión de segundos; usar el ID evita mezclar
    # corridas sucesivas del mismo segundo con los runs del snapshot previo.
    last_run_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM source_runs").fetchone()[0]
    summary = runner.refresh(conn, sources=due, communes=communes, fetcher=fetcher,
                             max_workers=args.workers, only=args.only, remembered=remembered)
    if "error" in summary:
        print(summary["error"])
        return 1
    runs = [dict(r) for r in conn.execute(
        "SELECT * FROM source_runs WHERE id > ? ORDER BY source_name", (last_run_id,))]
    for r in runs:
        r.pop("id", None)
    summary["skipped_by_cadence"] = len(skipped)
    state = source_planning.update_state(state, sources, runs)
    # Fuente caída hoy: sus fichas del snapshot anterior se mantienen hasta que responda.
    responded = {r["source_name"] for r in runs if r["ok"]}
    restored = db.restore_tagged_events(conn, crawled_path, communes, event_page.PAGE_TAG,
                                        skip_sources=responded)
    pending = [dict(r) for r in conn.execute(
        "SELECT title, raw_text, date, commune, source, source_url, reason FROM possible_events"
        " WHERE date IS NULL OR date >= ? ORDER BY date LIMIT 500", (db.today_iso(),))]
    candidates = [dict(r) for r in conn.execute(
        "SELECT url, domain, found_on, reason FROM source_candidates ORDER BY id LIMIT 500")]
    events = db.export_crawled(conn)
    if national:
        with_regions(events, communes)
        with_regions(pending, communes)
    os.makedirs(os.path.dirname(os.path.abspath(crawled_path)), exist_ok=True)
    _write_json(crawled_path, {
        "_notes": "Generado por actualizar.py%s. Solo contiene lo que las fuentes publicaron en esta "
                  "corrida y en corridas anteriores; nada se completa a mano." % (" --nacional" if national else ""),
        "generated_at": db.now_iso(),
        "summary": summary,
        "events": events,
        "runs": runs,
        "source_state": state,
        "skipped_by_cadence": skipped,
        "possible_events": pending,
        "source_candidates": candidates,
    })
    updated = 0 if args.no_update_sources else update_sources_file(status_path, runs)
    ok = summary["sources_ok"]
    print("Fuentes intentadas: %d | respondieron: %d | fallaron: %d" % (
        summary["sources_attempted"], ok, summary["sources_failed"]))
    print("Eventos encontrados: %d (nuevos %d, fusionados %d) | eventos en snapshot: %d (antes %d)" % (
        summary["events_found"], summary["events_inserted"], summary["events_merged"], len(events),
        previous["inserted"] + previous["merged"] + previous["unchanged"]))
    print("Posibles eventos pendientes: %d | fuentes candidatas: %d" % (len(pending), len(candidates)))
    print("Candidatos derivados a revisión editorial: %d" % summary.get("quarantined_candidates", 0))
    print("Fichas conservadas de fuentes que no respondieron: %d" % restored)
    print("Cadencia: %d fuentes omitidas por consulta reciente; revalidación %d/%d URLs" % (
        len(skipped), summary["revalidated_ok"], summary["revalidation_attempts"]))
    print("Fuentes con estado actualizado en sources.json: %d" % updated)
    for f in summary.get("feeds", []):
        print("  Calendario estructurado de %s: %s" % (f["source"], ", ".join(f["feeds"])))
    for e in summary["errors"][:10]:
        print("  - %s: %s" % (e["source"], e["error"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
