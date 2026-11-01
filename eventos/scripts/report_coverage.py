"""Genera matriz de cobertura regional basada exclusivamente en datos rastreados."""
import json
import sys
from collections import Counter
from pathlib import Path


def report(snapshot, communes, sources):
    catalog = json.loads(Path(snapshot).read_text(encoding="utf8"))
    communedata = json.loads(Path(communes).read_text(encoding="utf8"))
    sourcedata = json.loads(Path(sources).read_text(encoding="utf8"))
    names = [c["name"] for c in communedata["communes"]]
    srcs = sourcedata["sources"]
    runs = {r["source_name"]: r for r in catalog.get("runs", [])}
    counts = Counter(e.get("commune") for e in catalog.get("events", []))
    review = Counter(e.get("commune") for e in catalog.get("possible_events", []))
    lines = [
        "# Cobertura verificada · Eventos Región del Biobío",
        "",
        f"Snapshot: `{catalog.get('generated_at','sin fecha')}`",
        "",
        "Solo se consideran **eventos publicados** los incluidos en `events`. "
        "Una fuente HTTP 2xx o un candidato no equivalen a un evento verificado.",
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
    lines += ["", f"**Cobertura publicada: {coverage}/{len(names)} comunas.**",
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
        title = str(name).replace("|", "/").replace("\\n", " ")[:90]
        lines.append(f"| {title} | {pending} | {status} | {pages} | {accepted} |")
    skipped = catalog.get("skipped_by_cadence", [])
    if isinstance(skipped, list) and skipped:
        lines += ["", f"**Fuentes omitidas por cadencia:** {len(skipped)} (sin petición nueva)."]
    summary = catalog.get("summary") or {}
    if isinstance(summary, dict):
        checked = summary.get("revalidation_attempts", 0)
        ok = summary.get("revalidated_ok", 0)
        lines += ["", f"**Revalidación de fichas vigentes:** {ok}/{checked} respuestas satisfactorias."]
    return "\n".join(lines)+"\n"


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("Uso: python scripts/report_coverage.py SNAPSHOT COMUNAS FUENTES SALIDA")
    result = report(sys.argv[1], sys.argv[2], sys.argv[3])
    path=Path(sys.argv[4])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(result,encoding="utf8")
    print(result)
