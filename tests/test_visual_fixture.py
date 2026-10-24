"""La QA visual no depende del reloj ni modifica el fixture versionado."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.render_visual_fixture import render_fixture


class VisualFixtureTests(unittest.TestCase):
    def test_expired_history_renders_at_its_own_clock_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "history.json"
            source.write_text(json.dumps({"noticias": [{
                "category": "nacional", "title": "Titular de prueba permanente",
                "link": "https://medio.example/nota", "sources": ["Medio"],
                "published": "2001-01-01T12:00:00Z", "first_seen": "2001-01-01T12:00:00Z",
                "summary": "", "image": ""
            }]}), encoding="utf-8")
            before = source.read_bytes()
            output = Path(folder) / "public"
            render_fixture(source, output)
            page = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Titular de prueba permanente", page)
            self.assertIn('datetime="2001-01-01T12:00:00Z"', page)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue((output / "rss.xml").is_file())

    def test_render_always_exercises_latam_even_when_live_history_has_none(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "history.json"
            source.write_text(json.dumps({"noticias": [{
                "category": "nacional", "title": "Titular nacional de prueba",
                "link": "https://medio.example/nacional", "sources": ["Medio"],
                "published": "2001-01-01T12:00:00Z", "first_seen": "2001-01-01T12:00:00Z"
            }]}), encoding="utf-8")
            output = Path(folder) / "public"
            render_fixture(source, output)
            page = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="#cat-latinoamerica"', page)
            self.assertIn('class="coverage-country"', page)
            self.assertIn('data-countries="Brasil', page)
            self.assertIn("Fixture visual", page)
            self.assertIn('data-key="latinoamerica"', page)
            self.assertNotIn("Fixture visual", source.read_text(encoding="utf-8"))

    def test_empty_or_undated_fixture_fails_before_publishing(self):
        for stories in ([], [{"category": "nacional", "title": "Sin fecha"}]):
            with self.subTest(stories=stories), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "history.json"
                source.write_text(json.dumps({"noticias": stories}), encoding="utf-8")
                output = Path(folder) / "public"
                with self.assertRaises(ValueError):
                    render_fixture(source, output)
                self.assertFalse(output.exists())
