#!/usr/bin/env python3
"""Indicadores editoriales de la edición generada; alertas informativas sin bloquear."""
import collections
import json
from pathlib import Path


def inspect_news(stories):
    total = len(stories)
    categories = collections.Counter(s.get("category") or "(sin categoría)" for s in stories)
    sources = collections.Counter(
        (s.get("sources") or ["(sin fuente)"])[0] for s in stories
    )
    with_summary = sum(bool((s.get("summary") or "").strip()) for s in stories)
    with_image = sum(bool((s.get("image") or "").strip()) for s in stories)
    dominant, n_dominant = sources.most_common(1)[0] if sources else ("", 0)
    return {
        "noticias": total,
        "categorias": dict(sorted(categories.items())),
        "fuente_mas_frecuente": dominant,
        "porcentaje_fuente_principal": round(100 * n_dominant / total, 1) if total else 0,
        "porcentaje_con_resumen": round(100 * with_summary / total, 1) if total else 0,
        "porcentaje_con_imagen": round(100 * with_image / total, 1) if total else 0,
    }


def alerts(snapshot):
    # No inventar artículos ni bloquear la publicación por cuotas o licencias.
    if snapshot["noticias"] == 0:
        return ["Historial sin noticias"]
    notices = []
    for category, amount in snapshot["categorias"].items():
        if amount < 5:
            notices.append(f"Cobertura reducida en {category}: {amount} noticias")
    if snapshot["porcentaje_fuente_principal"] > 25:
        notices.append(
            f"Alta concentración: {snapshot['fuente_mas_frecuente']} "
            f"({snapshot['porcentaje_fuente_principal']}%)"
        )
    if snapshot["porcentaje_con_resumen"] < 30:
        notices.append("Menos del 30% de noticias dispone de resumen")
    if snapshot["porcentaje_con_imagen"] < 50:
        notices.append("Menos del 50% de noticias dispone de imagen")
    return notices


def main():
    payload = json.loads(Path("data/historial.json").read_text(encoding="utf-8"))
    report = inspect_news(payload.get("noticias", []))
    print("SALUD EDITORIAL:", json.dumps(report, ensure_ascii=False, sort_keys=True))
    for warning in alerts(report):
        print(f"::warning::{warning}")


if __name__ == "__main__":
    main()
