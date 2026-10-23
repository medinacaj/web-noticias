"""Regresiones de ingesta y render con reloj fijo y sin HTTP real."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import fetch_noticias as news


NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def article(link="https://a.example/nota", hours=1, **changes):
    return {"category": "nacional", "title": "Gobierno anuncia nuevas medidas económicas",
            "source": "Medio A", "source_url": "https://a.example",
            "link": link, "published": (NOW - timedelta(hours=hours)).isoformat(),
            "summary": "", "image": "", **changes}


def history_item(**changes):
    item = article(**changes)
    item["sources"] = [item.pop("source")]
    item["first_seen"] = "2026-10-22T10:00:00Z"
    item["_norm"] = news.normalize_title(item["title"])
    return item


class TemporalMergeTests(unittest.TestCase):
    def test_expired_history_cannot_absorb_a_recent_distinct_url(self):
        stories = [history_item(hours=25)]
        news.merge(stories, [article("https://b.example/nota")], NOW)
        kept = news.prune(stories, NOW, 24)
        self.assertEqual([s["link"] for s in kept], ["https://b.example/nota"])
        self.assertEqual(kept[0]["published"], "2026-10-23T11:00:00Z")

    def test_expired_incoming_url_cannot_age_a_recent_story(self):
        stories = [history_item()]
        news.merge(stories, [article("https://b.example/nota", hours=25)], NOW)
        kept = news.prune(stories, NOW, 24)
        self.assertEqual([s["link"] for s in kept], ["https://a.example/nota"])
        self.assertEqual(kept[0]["published"], "2026-10-23T11:00:00+00:00")

    def test_batch_order_does_not_erase_the_recent_distinct_url(self):
        old = article(hours=25)
        recent = article("https://b.example/nota")
        for items in ([old, recent], [recent, old]):
            with self.subTest(first=items[0]["link"]):
                stories = []
                news.merge(stories, items, NOW)
                self.assertEqual([s["link"] for s in news.prune(stories, NOW, 24)],
                                 ["https://b.example/nota"])

    def test_exact_url_tracking_duplicate_preserves_expired_original_date(self):
        stories = [history_item(hours=25)]
        added = news.merge(stories, [article("https://a.example/nota?utm_source=rss")], NOW)
        self.assertEqual(added, 0)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["published"], "2026-10-22T11:00:00+00:00")
        self.assertEqual(news.prune(stories, NOW, 24), [])

    def test_exact_url_without_published_cannot_rejuvenate_expired_first_seen(self):
        for link in ("https://a.example/nota", "https://a.example/nota?utm_source=rss"):
            with self.subTest(link=link):
                original = history_item(published=None)
                original["first_seen"] = "2026-10-22T11:00:00Z"
                stories = [original]
                self.assertEqual(news.merge(stories, [article(link)], NOW), 0)
                self.assertEqual(len(stories), 1)
                self.assertIsNone(stories[0]["published"])
                self.assertEqual(stories[0]["first_seen"], "2026-10-22T11:00:00Z")
                self.assertEqual(news.prune(stories, NOW, 24), [])

    def test_exact_url_can_add_editorial_date_earlier_than_first_seen(self):
        original = history_item(published=None)
        original["first_seen"] = "2026-10-22T11:00:00Z"
        stories = [original]
        self.assertEqual(news.merge(stories, [article(hours=26)], NOW), 0)
        self.assertEqual(stories[0]["published"], "2026-10-22T10:00:00Z")
        self.assertEqual(stories[0]["first_seen"], "2026-10-22T11:00:00Z")
        self.assertEqual(news.prune(stories, NOW, 24), [])

    def test_expired_first_seen_fallback_cannot_absorb_recent_distinct_url(self):
        stories = [history_item(published=None)]
        news.merge(stories, [article("https://b.example/nota")], NOW)
        self.assertEqual([s["link"] for s in news.prune(stories, NOW, 24)],
                         ["https://b.example/nota"])

    def run_import(self, window, old_hours):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history = path / "history.json"
            history.write_text(json.dumps({"noticias": [history_item(hours=old_hours)]}),
                               encoding="utf-8")
            imported = path / "incoming.json"
            imported.write_text(json.dumps([article("https://b.example/nota")]), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "fetch_noticias.py"), "--importar", str(imported),
                 "--historial", str(history), "--salida", str(path / "public"),
                 "--ahora", "2026-10-23T12:00:00Z", "--ventana", str(window)],
                cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(history.read_text(encoding="utf-8"))["noticias"]

    def test_cli_shorter_window_keeps_recent_distinct_url(self):
        self.assertEqual([s["link"] for s in self.run_import(12, 13)],
                         ["https://b.example/nota"])

    def test_cli_larger_window_still_groups_eligible_coverage(self):
        stories = self.run_import(48, 25)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["published"], "2026-10-22T11:00:00+00:00")
        self.assertEqual(len(stories[0]["coverages"]), 1)


class FutureDateTests(unittest.TestCase):
    def test_rss_future_date_never_enters_history_or_becomes_lead(self):
        raw = b'''<rss><channel><item><title>Titular del futuro</title>
        <link>https://future.example/nota</link><pubDate>Thu, 01 Jan 2099 00:00:00 GMT</pubDate>
        <source url="https://future.example">Medio futuro</source></item>
        <item><title>Investigadores estudian especies marinas</title>
        <link>https://current.example/nota</link><pubDate>Fri, 23 Oct 2026 11:00:00 GMT</pubDate>
        <source url="https://current.example">Medio actual</source></item></channel></rss>'''
        # Único doble: la respuesta HTTP externa. Parser, merge, prune y select son reales.
        with patch("urllib.request.urlopen", return_value=io.BytesIO(raw)):
            items = news.fetch_rss("https://feed.example/rss", "nacional")
        stories = []
        news.merge(stories, items, NOW)
        self.assertEqual([s["link"] for s in stories], ["https://current.example/nota"])
        self.assertEqual(news.select(news.prune(stories, NOW, 24), NOW)["lead"]["link"],
                         "https://current.example/nota")

    def test_excessive_future_date_is_rejected_before_similar_coverage(self):
        stories = [history_item()]
        news.merge(stories, [article("https://b.example/nota", hours=-1, source="Futuro")], NOW)
        self.assertEqual(stories[0]["sources"], ["Medio A"])
        self.assertEqual(len(stories), 1)

    def test_future_first_item_cannot_poison_a_valid_exact_url(self):
        stories = []
        news.merge(stories, [article(hours=-100), article(source="Vigente")], NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["sources"], ["Vigente"])
        self.assertEqual(stories[0]["published"], "2026-10-23T11:00:00Z")

    def test_future_history_is_pruned_even_if_first_seen_is_valid(self):
        valid = history_item()
        future = history_item(link="https://future.example/nota", hours=-100)
        self.assertEqual(news.prune([valid, future], NOW, 24), [valid])

    def test_future_first_seen_fallback_is_pruned(self):
        story = history_item(published=None)
        story["first_seen"] = "2099-01-01T00:00:00Z"
        self.assertEqual(news.prune([story], NOW, 24), [])

    def test_fifteen_minute_tolerance_is_inclusive_for_merge_and_prune(self):
        for minutes, expected in ((14, 1), (15, 1), (15.01, 0)):
            with self.subTest(minutes=minutes):
                stories = []
                news.merge(stories, [article(hours=-minutes / 60)], NOW)
                self.assertEqual(len(stories), expected)
                stored = history_item(hours=-minutes / 60)
                self.assertEqual(len(news.prune([stored], NOW, 24)), expected)

    def test_missing_date_keeps_first_seen_fallback_without_rejuvenating_old_dates(self):
        stories = []
        news.merge(stories, [article(published=None)], NOW)
        self.assertIsNone(stories[0]["published"])
        self.assertEqual(stories[0]["first_seen"], "2026-10-23T12:00:00Z")
        self.assertEqual(len(news.prune(stories, NOW, 24)), 1)
        old = history_item(hours=25)
        news.merge([old], [article(published=None)], NOW)
        self.assertEqual(old["published"], "2026-10-22T11:00:00+00:00")


class InvalidSourceTests(unittest.TestCase):
    def test_malformed_source_falls_back_to_article_domain(self):
        self.assertEqual(news.source_domain("https://[", "https://medio.example/nota"),
                         "medio.example")

    def test_two_malformed_urls_leave_visible_monogram(self):
        mark = news.source_mark({"source_url": "https://[", "link": "https://[",
                                 "sources": ["Medio"]})
        self.assertNotIn("<img", mark)
        self.assertIn('class="source-initial">M', mark)

    def test_malformed_source_does_not_abort_build_or_other_stories(self):
        stories = [history_item(source_url="https://["),
                   history_item(link="https://b.example/nota",
                                title="Investigadores estudian especies marinas", source="Medio B")]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, NOW, folder, 24)
            page = (Path(folder) / "index.html").read_text(encoding="utf-8")
            self.assertIn("Gobierno anuncia nuevas medidas económicas", page)
            self.assertIn("Investigadores estudian especies marinas", page)
            self.assertIn("domain=a.example", page)
            self.assertTrue((Path(folder) / "sitemap.xml").is_file())


if __name__ == "__main__":
    unittest.main()
