#!/usr/bin/env python3
"""Render offline de QA con el reloj del fixture; nunca para publicar Pages."""
import argparse
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
    with tempfile.TemporaryDirectory(prefix="visual-fixture-") as folder:
        copy = Path(folder) / "history.json"
        copy.write_bytes(source.read_bytes())
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
