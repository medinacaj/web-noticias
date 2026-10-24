#!/usr/bin/env python3
"""Render offline de QA con el reloj del fixture; nunca para publicar Pages."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def render_fixture(history, output):
    from fetch_noticias import load_history, story_time, to_iso
    source = Path(history).resolve()
    moments = [moment for story in load_history(source)
               if (moment := story_time(story)) is not None]
    if not moments:
        raise ValueError("El fixture visual necesita al menos una noticia con fecha válida")
    # Conservar los intervalos originales y ejercitar el CLI real sin consultar
    # fuentes, rejuvenecer artículos ni escribir en el historial versionado.
    clock = to_iso(max(moments))
    payload = json.loads(source.read_text(encoding="utf-8"))
    # Casos explícitos sólo para QA: el historial vivo puede no contener esta
    # sección. Nunca se escriben en main/news-data ni se suben al publicador.
    titles = ("Brasil: Fixture visual de cooperación", "Venezuela: Fixture visual de economía",
              "México y Perú: Fixture visual de cultura", "Argentina: Fixture visual de ciencia",
              "Colombia: Fixture visual de tecnología", "Uruguay: Fixture visual de deportes",
              "Brasileiros: Fixture visual em português", "Costa Rica: Fixture visual regional")
    payload["noticias"].extend({
        "category": "latinoamerica", "title": title,
        "link": f"https://qa.example/latinoamerica/{index}",
        "sources": ["Medio de prueba QA"], "source_url": "https://qa.example",
        "published": clock, "first_seen": clock, "metadata_only": True,
        "summary": "", "image": ""
    } for index, title in enumerate(titles))
    with tempfile.TemporaryDirectory(prefix="visual-fixture-") as folder:
        copy = Path(folder) / "history.json"
        copy.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "fetch_noticias.py"),
                        "--solo-render", "--historial", str(copy),
                        "--salida", str(Path(output).resolve()), "--ahora", clock],
                       cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=ROOT / "data/historial.json")
    parser.add_argument("--output", type=Path, default=ROOT / "public")
    args = parser.parse_args()
    render_fixture(args.history, args.output)
