#!/usr/bin/env python3
"""QA editorial de historial y HTML publicado: sin efectuar peticiones a medios."""
import argparse
import collections
import json
import pathlib
import urllib.parse

def audit(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    stories = data.get("noticias", [])
    results = {"total": len(stories), "sin_resumen": 0,
               "sin_fotografia": 0, "imagenes_repetidas": 0,
               "enlaces_invalidos": 0, "fuentes_sin_nombre": 0}
    images = collections.Counter()
    for s in stories:
        url = s.get("link") or ""
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            results["enlaces_invalidos"] += 1
        if not s.get("summary"):
            results["sin_resumen"] += 1
        image = s.get("image") or ""
        if not image:
            results["sin_fotografia"] += 1
        else:
            images[image] += 1
        if not (s.get("sources") or []):
            results["fuentes_sin_nombre"] += 1
    results["imagenes_repetidas"] = sum(n - 1 for n in images.values() if n > 1)
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", default="data/historial.json")
    parser.add_argument("--strict", action="store_true", help="Fallos solo de enlaces y fuentes invalidos")
    args = parser.parse_args()
    results = audit(args.history)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if args.strict and (results["enlaces_invalidos"] or results["fuentes_sin_nombre"]):
        raise SystemExit(1)
