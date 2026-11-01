"""Genera matriz de cobertura regional basada exclusivamente en datos rastreados."""
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _current_event(event, today):
    """Las filas históricas del snapshot no acreditan cobertura vigente."""
    if not isinstance(event, dict):
        return False
    end = event.get("end_date") or event.get("date")
    if not isinstance(end, str):
        return False
    try:
        valid_until = date.fromisoformat(end)
    except ValueError:
        return False
    return (valid_until >= today
            and str(event.get("status") or "").strip().casefold() != "cancelado")


def _cell(value, limit=90):
    """La fuente es externa: no permitir que rompa tablas Markdown."""
    return " ".join(str(value).split()).replace("|", "/").replace("<", "&lt;").replace(">", "&gt;")[:limit]


def report(snapshot, communes, sources, today=None):
    today = today or datetime.now(ZoneInfo("America/Santiago")).date()
    catalog = json.loads(Path(snapshot).read_text(encoding="utf8"))
    communedata = json.loads(Path(communes).read_text(encoding="utf8"))
    sourcedata = json.loads(Path(sources).read_text(encoding="utf8"))
    names = [c["name"] for c in communedata["communes"]]
    srcs = sourcedata["sources"]
    runs = {r["source_name"]: r for r in catalog.get("runs", [])}
    counts = Counter(e.get("commune") for e in catalog.get("events", [])
                     if _current_event(e, today))
    review = Counter(e.get("commune") for e in catalog.get("possible_events", []))
    lines = [
        "# Cobertura verificada · Eventos Región del Biobío",
        "",
        f"Snapshot: `{catalog.get('generated_at','sin fecha')}`",
        "",
        "La cobertura vigente cuenta solo eventos de `events` con fecha final igual o posterior "
        "al día de revisión en Chile y no cancelados. El snapshot puede conservar hasta 30 días "
        "de eventos históricos. HTTP 2xx y candidatos no acreditan eventos verificados.",
        "",
        "| Comuna | Fuentes locales habilitadas | Fuentes HTTP 2xx | Eventos publicados | Candidatos por revisar |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in names:
        local = [s for s in srcs if s.get("commune") == name and s.get("enabled")]
        ok = sum(1 for s in local if runs.get(s["name"], {}).get("ok")
                 and 200 <= (runs.get(s["name"], {}).get("http_status") or 0) < 300)
        lines.append(f"| {name} | {len(local)} | {ok} | {counts[name]} | {review[name]} |")
    coverage = sum(bool(counts[n]) for n in names)
    lines += ["", f"**Cobertura vigente: {coverage}/{len(names)} comunas.**",
              "", "Nota: hay ticketeras y radares nacionales sin comuna confiable; "
              "sus candidatos no se publican automáticamente.",
              "", "## Diagnóstico del último rastreo por fuente",
              "", "La tabla prioriza fuentes con candidatos por revisar. Las fuentes omitidas "
              "por cadencia no se cuentan como accesibles en esta ejecución.",
              "", "| Fuente | Candidatos acumulados | HTTP esta ejecución | Páginas consultadas | Eventos aceptados |",
              "|---|---:|---|---:|---:|"]
    pending_sources = Counter(e.get("source") for e in catalog.get("possible_events", [])
                              if isinstance(e, dict) and e.get("source"))
    for name, pending in pending_sources.most_common(15):
        run = runs.get(name)
        status = str(run.get("http_status") or "Sin respuesta") if run else "No consultada"
        pages = run.get("pages_fetched", 0) if run else 0
        accepted = run.get("events_found", 0) if run else 0
        title = _cell(name)
        lines.append(f"| {title} | {pending} | {status} | {pages} | {accepted} |")
    skipped = catalog.get("skipped_by_cadence", [])
    if isinstance(skipped, list) and skipped:
        lines += ["", f"**Fuentes omitidas por cadencia:** {len(skipped)} (sin petición nueva)."]
    summary = catalog.get("summary") or {}
    if isinstance(summary, dict):
        checked = summary.get("revalidation_attempts", 0)
        ok = summary.get("revalidated_ok", 0)
        lines += ["", f"**Revalidación de fichas vigentes:** {ok}/{checked} respuestas satisfactorias."]
    # Motivos originales del snapshot, sin promover ni borrar candidaturas.
    # Evitar que un gran volumen de notas sin fecha verificada oculte causas
    # distintas, como recinto sin comuna o convocatorias administrativas.
    reasons = Counter(_cell(item.get("reason") or "Sin motivo", 130)
                      for item in catalog.get("possible_events", [])
                      if isinstance(item, dict))
    lines += ["", "## Candidatos pendientes por motivo de revisión", "",
              "Estos registros están en cuarentena; no son eventos publicados ni "
              "se verifican automáticamente al generar el informe.", ""]
    if reasons:
        lines += ["| Motivo registrado | Candidatos |", "|---|---:|"]
        for reason, count in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("No se registran candidatos pendientes.")

    state = catalog.get("source_state")
    if not isinstance(state, dict):
        state = {}
    enabled = {s.get("name") for s in srcs if isinstance(s, dict) and s.get("enabled")}
    failing = []
    for name, status in state.items():
        if name not in enabled or not isinstance(status, dict):
            continue
        failures = status.get("consecutive_failures")
        if isinstance(failures, int) and not isinstance(failures, bool) and failures >= 3:
            failing.append((name, failures, status))
    failing.sort(key=lambda item: (-item[1], str(item[0])))
    lines += ["", "## Alertas de salud por fuente", "",
              "Se informa desde 3 fallos consecutivos **registrados** en fuentes habilitadas. "
              "No se hacen solicitudes nuevas ni se atribuye una respuesta a fuentes omitidas por cadencia.",
              ""]
    if failing:
        lines += ["| Fuente | Fallos consecutivos | Último HTTP | Última comprobación |",
                  "|---|---:|---|---|"]
        for name, failures, status in failing[:15]:
            code = status.get("last_http_status")
            http = str(code) if isinstance(code, int) and not isinstance(code, bool) else "Sin respuesta"
            checked = _cell(status.get("last_checked_at") or "Sin registro", 35)
            lines.append(f"| {_cell(name)} | {failures} | {http} | {checked} |")
        if len(failing) > 15:
            lines.append(f"\nOtras fuentes con fallos consecutivos: {len(failing) - 15}.")
    elif not state:
        lines.append("No hay historial de estados por fuente para evaluar la continuidad de fallos.")
    else:
        lines.append("No se registran 3 fallos consecutivos en fuentes habilitadas.")
    return "\n".join(lines)+"\n"


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("Uso: python scripts/report_coverage.py SNAPSHOT COMUNAS FUENTES SALIDA")
    result = report(sys.argv[1], sys.argv[2], sys.argv[3])
    path=Path(sys.argv[4])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(result,encoding="utf8")
    print(result)
