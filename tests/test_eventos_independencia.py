"""Regresión de independencia del recolector de eventos respecto al repositorio antiguo.

Pruebas sin red: verifican rutas de datos y flujos del código versionado.
No certifican variables externas ni consumidores ajenos a este repositorio.
"""

import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.agenda import SNAPSHOTS, load_agenda


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SNAPSHOTS = (
    ("EVENTOS_BIOBIO_URL", ".events-data/eventos/crawled_events.json", "Biobío"),
    ("EVENTOS_NACIONALES_URL", ".events-data/eventos/national_events.json", ""),
    ("EVENTOS_MANUAL_URL", "eventos/agenda_manual.json", ""),
)


class IndependenciaEventosTests(unittest.TestCase):
    def test_agenda_uses_only_local_default_snapshots(self):
        self.assertEqual(SNAPSHOTS, EXPECTED_SNAPSHOTS)
        self.assertTrue(all(not ruta.startswith(("http://", "https://"))
                            for _, ruta, _ in SNAPSHOTS))

    def test_agenda_loads_without_fetching_the_retired_repository(self):
        sources = {
            ".events-data/eventos/crawled_events.json": {
                "events": [{
                    "title": "Taller en Biobío", "date": "2026-11-03",
                    "commune": "Coronel", "source_url": "https://organizador.cl/taller",
                }],
            },
            ".events-data/eventos/national_events.json": {
                "events": [{
                    "title": "Feria nacional", "date": "2026-11-04",
                    "commune": "Temuco", "region": "La Araucanía",
                    "source_url": "https://organizador.cl/feria",
                }],
            },
            "eventos/agenda_manual.json": {"events": []},
        }
        requested = []

        def local_only(path):
            self.assertIn(path, sources)
            requested.append(path)
            return sources[path]

        with patch.dict(os.environ, {}, clear=True):
            events = load_agenda(datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
                                 fetch=local_only)
        self.assertEqual(set(requested), set(sources))
        self.assertEqual({e["title"] for e in events},
                         {"Taller en Biobío", "Feria nacional"})

    def test_workflows_use_internal_events_data_branch(self):
        collector = (ROOT / ".github/workflows/actualizar-eventos.yml").read_text(
            encoding="utf-8")
        publisher = (ROOT / ".github/workflows/update-news.yml").read_text(
            encoding="utf-8")
        self.assertIn("ref: events-data", collector)
        self.assertIn("scripts/events_data.py persist", collector)
        self.assertIn("ref: events-data", publisher)
        self.assertIn("path: .events-data", publisher)

    def test_runtime_does_not_reference_old_repository_url(self):
        runtime_files = [
            ROOT / ".github/workflows/actualizar-eventos.yml",
            ROOT / ".github/workflows/update-news.yml",
            ROOT / "fetch_noticias.py",
            ROOT / "scripts/agenda.py",
            ROOT / "eventos/actualizar.py",
        ]
        forbidden = (
            "github.com/medinacaj/eventos-biobio",
            "raw.githubusercontent.com/medinacaj/eventos-biobio",
            "api.github.com/repos/medinacaj/eventos-biobio",
        )
        for path in runtime_files:
            with self.subTest(path=path.relative_to(ROOT)):
                lines = path.read_text(encoding="utf-8").splitlines()
                executable = "\n".join(line for line in lines
                                       if not line.lstrip().startswith("#"))
                self.assertFalse(any(url in executable for url in forbidden),
                                 f"Dependencia antigua encontrada en {path}")


if __name__ == "__main__":
    unittest.main()
