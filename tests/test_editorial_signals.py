"""Señales de RadarRRS adaptadas sin red: evidencia, límite y privacidad."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fetch_noticias as news
from scripts.editorial_signals import (
    ARCHIVE_DAYS, MAX_ARCHIVE, update_archive, trending_topics,
    related_timeline, render_signals, terms,
)


class EditorialSignalsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)

    def story(self, hour, number, source, title="Inteligencia artificial transforma servicios"):
        dt = self.now - timedelta(hours=hour)
        return {
            "link": f"https://medio{number}.example/noticia/{number}?utm_source=rss",
            "published": dt.isoformat(), "first_seen": dt.isoformat(),
            "category": "tecnologia", "title": title, "sources": [source],
            "image": "https://foto.example/no-copiar.jpg", "summary": "Texto ajeno",
        }

    def test_archive_uses_only_metadata_and_deduplicates_tracking(self):
        a = self.story(2, 1, "Medio A")
        b = {**a, "link": a["link"].split("?")[0] + "?oc=5",
             "sources": ["Medio B"]}
        result = update_archive([], [a, b, self.story(240, 8, "Antiguo")], self.now)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sources"], ["Medio A", "Medio B"])
        self.assertNotIn("image", result[0])
        self.assertNotIn("summary", result[0])
        self.assertNotIn("tracking", str(result))

    def test_archive_cap_and_window(self):
        articles = [self.story(2, i, f"Medio {i}") for i in range(MAX_ARCHIVE + 15)]
        self.assertEqual(len(update_archive([], articles, self.now)), MAX_ARCHIVE)
        self.assertEqual(update_archive([], [self.story(24 * (ARCHIVE_DAYS + 1), 1, "A")], self.now), [])

    def test_trends_require_complete_reference_period(self):
        articles = [self.story(2, i, f"Medio {i}") for i in range(4)]
        history = update_archive([], articles, self.now)
        self.assertEqual(trending_topics(history, self.now,
                         (self.now - timedelta(days=7)).isoformat()), [])
        self.assertEqual(trending_topics(history, self.now,
                         (self.now - timedelta(days=8)).isoformat()), [])
        anchor = self.story(24 * 8 - 1, 50, "Histórico", "Reporte antiguo del sector eléctrico")
        history = update_archive(history, [anchor], self.now)
        trends = trending_topics(history, self.now,
                        (self.now - timedelta(days=8)).isoformat())
        self.assertTrue(trends)
        self.assertTrue(any(x["sources"] == 4 for x in trends))
        self.assertTrue(all(x["stories"] >= 4 for x in trends))

    def test_same_publisher_does_not_fake_trend(self):
        articles = [self.story(2, i, "Solo Medio") for i in range(8)]
        articles.append(self.story(24 * 8 - 1, 50, "Histórico", "Reporte antiguo del sector eléctrico"))
        history = update_archive([], articles, self.now)
        self.assertEqual(trending_topics(history, self.now,
                         (self.now - timedelta(days=8)).isoformat()), [])

    def test_generic_weekday_month_sports_not_trend(self):
        for term in ("miercoles", "octubre", "partidos", "resultados"):
            self.assertNotIn(term, terms("Miércoles octubre partidos resultados"))
        titles = [self.story(2, i, f"Medio {i}", title="Miércoles octubre partidos resultados") for i in range(5)]
        titles.append(self.story(24 * 8 - 1, 50, "Histórico", "Reporte antiguo del sector eléctrico"))
        history = update_archive([], titles, self.now)
        self.assertEqual(trending_topics(history, self.now,
                         (self.now - timedelta(days=8)).isoformat()), [])

    def test_timeline_has_two_distinct_outlets_with_time_difference(self):
        first = self.story(36, 1, "Medio A", title="Una investigación científica importante")
        second = self.story(2, 2, "Medio B", title=first["title"])
        result = related_timeline(update_archive([], [first, second], self.now), self.now)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 2)
        self.assertLess(result[0][0]["published"], result[0][1]["published"])

    def test_timeline_ignores_single_media_and_unrelated_topics(self):
        first = self.story(36, 1, "Medio A")
        second = self.story(2, 2, "Medio A", title="Tecnología sin relación con investigación")
        self.assertFalse(related_timeline(update_archive([], [first, second], self.now), self.now))

    def test_renders_escaped_links_and_only_when_evidence_exists(self):
        self.assertEqual(render_signals([], []), "")
        safe = self.story(1, 1, "A")
        archive = update_archive([], [safe], self.now)
        self.assertEqual(render_signals([], related_timeline(archive, self.now)), "")
        html = render_signals([{"label": "<alert>", "link": safe["link"],
                 "stories": 4, "sources": 4}], [])
        self.assertIn("&lt;alert&gt;", html)
        self.assertNotIn("<alert>", html)
        self.assertIn('rel="noopener"', html)

    def test_save_and_reload_metadata_without_touching_24_hour_portada(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "historial.json")
            articles = [self.story(2, 1, "A")]
            archive = update_archive([], articles, self.now)
            news.save_history(path, articles, self.now, archive, self.now.isoformat())
            loaded, started = news.load_signals(path)
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(len(saved["noticias"]), 1)
            self.assertEqual(loaded, archive)
            self.assertEqual(started, self.now.isoformat())


if __name__ == "__main__":
    unittest.main()
