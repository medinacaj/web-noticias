"""Indicadores de cobertura vinculados a datos reales, no a candidatos publicados."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import fetch_noticias as news
from scripts.agenda import coverage_summary, render_coverage, load_agenda, render_agenda

TODAY = date(2026, 11, 1)
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def payload():
    return {
        "generated_at": "2026-11-01T08:00:00",
        "runs": [
            {"source_name": "Teatro A", "ok": 1, "http_status": 200},
            {"source_name": "Teatro B", "ok": 1, "http_status": 200},
            {"source_name": "Municipalidad de Tomé", "ok": 0, "http_status": 403},
        ],
        "events": [
            {"title": "Feria del libro", "date": "2026-11-02",
             "commune": "Concepción", "source_url": "https://teatroa.cl/feria"},
            {"title": "Evento pasado", "date": "2026-10-30",
             "commune": "Tomé", "source_url": "https://teatroa.cl/pasado"},
        ],
        "possible_events": [
            {"title": "Aviso 1", "reason": "Texto con fecha futura"},
            {"title": "Aviso 2", "reason": "Texto con fecha futura"},
            {"title": "Aviso 3", "reason": "Fuente radar"},
        ],
    }


class AgendaQualityTests(unittest.TestCase):
    def test_summary_counts_only_live_accepted_regional_events(self):
        with TemporaryDirectory() as temp:
            communes = Path(temp) / "communes.json"
            communes.write_text(json.dumps({"communes": [
                {"name": "Concepción"}, {"name": "Tomé"}, {"name": "Hualpén"}]}),
                encoding="utf-8")
            report = coverage_summary(payload(), TODAY, communes_path=communes)
        self.assertEqual((report["attempted"], report["responded"]), (3, 2))
        self.assertEqual((report["events"], report["pending"]), (1, 3))
        self.assertEqual((report["communes_covered"], report["communes_total"]), (1, 3))
        self.assertEqual(set(report["missing"]), {"Tomé", "Hualpén"})
        self.assertEqual(report["failed"], ["Municipalidad de Tomé"])
        self.assertEqual(report["top_reasons"][0], ("Texto con fecha futura", 2))

    def test_quality_panel_is_collapsed_and_does_not_show_unvalidated_events(self):
        coverage = {"attempted": 3, "responded": 2, "events": 1,
                    "pending": 11, "communes_total": 3, "communes_covered": 1,
                    "missing": ["Tomé", "Hualpén"],
                    "failed": ["<script>fake</script>"],
                    "top_reasons": [("Texto con fecha", 11)],
                    "generated_at": "2026-11-01T08:00:00"}
        html = render_coverage(coverage)
        self.assertIn("<details", html)
        self.assertIn("Cobertura y calidad de la agenda", html)
        self.assertIn("Fuentes que respondieron", html)
        self.assertIn("Candidatos guardados para revisión", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<article", html)
        self.assertNotIn("<time", html)
        page = render_agenda([], NOW, coverage=coverage)
        self.assertIn('id="cat-agenda"', page)
        self.assertIn("0 eventos", page)
        self.assertEqual(render_agenda([], NOW), "")

    def test_integration_does_not_turn_candidates_into_news(self):
        quality = {}
        inputs = {"bio": payload(), "national": {"events": []}, "manual": {"events": []}}
        with patch.dict("os.environ", {}, clear=True):
            events = load_agenda(NOW, fetch=inputs.__getitem__,
                                 snapshots=(("BIO", "bio", "Biobío"),
                                            ("NAT", "national", ""),
                                            ("MAN", "manual", "")),
                                 coverage=quality)
        self.assertEqual(len(events), 1)
        self.assertEqual(quality["pending"], 3)
        with TemporaryDirectory() as tmp:
            news.build_site([], NOW, tmp, agenda=events, agenda_quality=quality)
            index = Path(tmp, "index.html").read_text(encoding="utf-8")
        self.assertIn('id="cat-agenda"', index)
        self.assertEqual(index.count('class="agenda-quality"'), 1)
        self.assertIn("Feria del libro", index)
        self.assertNotIn("Aviso 1", index)
        self.assertNotIn("Aviso 2", index)


if __name__ == "__main__":
    unittest.main()
