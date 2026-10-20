"""Fuentes internacionales verificadas, límites por medio y deduplicación."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import fetch_noticias as news
from scripts.global_sources import (
    WORLD_NEWS_SOURCES, MAX_NEWS_PER_WORLD_SOURCE,
    matches_world_source, world_news_google_url,
)


class WorldSourcesTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)
        self.published = "2026-10-20T17:00:00Z"

    def item(self, media, index=0):
        return {
            "category": "internacional", "title": f"Tema mundial único {media['name']} {index}",
            "source": media["name"], "source_url": "https://www." + media["domain"],
            "link": "https://www." + media["domain"] + f"/world/{index}",
            "published": self.published, "summary": "", "image": "",
        }

    def test_recognized_sources_have_global_diversity(self):
        names = [m["name"] for m in WORLD_NEWS_SOURCES]
        for name in ("Reuters", "Associated Press", "Al Jazeera English",
                     "NHK World-Japan", "The Guardian", "NPR World",
                     "DW Español", "France 24 Español", "CNN en Español",
                     "El País Internacional", "Euronews Español"):
            self.assertIn(name, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("BBC News Mundo", [name for _, name in news.DIRECT_FEEDS["internacional"]])
        self.assertLessEqual(MAX_NEWS_PER_WORLD_SOURCE, 5)
        self.assertFalse(next(m for m in WORLD_NEWS_SOURCES if m["name"] == "The Guardian")["enabled"])
        self.assertGreaterEqual(sum(m["language"] == "es" for m in WORLD_NEWS_SOURCES), 4)

    def test_google_news_site_filters_locale_and_recent_date(self):
        for medium in WORLD_NEWS_SOURCES:
            url = world_news_google_url(medium)
            self.assertTrue(url.startswith("https://news.google.com/rss/search?"))
            params = parse_qs(urlsplit(url).query)
            self.assertEqual(params["q"], [medium["query"] + " when:1d"])
            self.assertEqual(params["hl"], ["es-419"] if medium["language"] == "es" else ["en-US"])
        self.assertNotIn("feeds.reuters.com", " ".join(world_news_google_url(s) for s in WORLD_NEWS_SOURCES))
        self.assertNotIn("theguardian.com/world/rss", " ".join(world_news_google_url(s) for s in WORLD_NEWS_SOURCES))

    def test_source_domain_rejects_mismatches_and_spoofing(self):
        medium = WORLD_NEWS_SOURCES[0]
        self.assertTrue(matches_world_source(self.item(medium), medium))
        self.assertFalse(matches_world_source({**self.item(medium), "source_url": ""}, medium))
        self.assertFalse(matches_world_source({**self.item(medium), "source_url": "https://reuters.com.evil.net"}, medium))
        self.assertFalse(matches_world_source({**self.item(medium), "source_url": "http://reuters.com"}, medium))
        self.assertFalse(matches_world_source({**self.item(medium), "source_url": "https://reuters.com@evil.net"}, medium))

    def test_collection_bounded_by_source_and_no_cross_category_spill(self):
        calls = []
        def fake_rss(url, category, default_source=None):
            calls.append((url, category))
            q = parse_qs(urlsplit(url).query).get("q", [""])[0]
            media = next((x for x in WORLD_NEWS_SOURCES if q == x["query"] + " when:1d"), None)
            if media is None:
                return []
            items = [self.item(media, i) for i in range(12)]
            items.insert(0, {**self.item(media, 777), "source_url": "https://otro.example/"})
            return items
        with patch.object(news, "fetch_rss", side_effect=fake_rss), patch.object(news, "GNEWS_API_KEY", ""):
            result = news.collect(self.now)
        active = sum(m.get("enabled", True) for m in WORLD_NEWS_SOURCES)
        self.assertEqual(len(result), active * MAX_NEWS_PER_WORLD_SOURCE)
        self.assertTrue(all(item["image_fetch_disabled"] for item in result))
        self.assertTrue(all(item["summary"] == "" and item["image"] == "" for item in result))
        self.assertTrue(all(item["category"] == "internacional" for item in result))
        self.assertTrue(all(item["source"] != "Fuente" for item in result))
        self.assertEqual(len(calls), len(news.CATEGORIES) + 1 + active)

    def test_broken_media_does_not_block_other_sources(self):
        def fake_rss(url, category, default_source=None):
            q = parse_qs(urlsplit(url).query).get("q", [""])[0]
            media = next((x for x in WORLD_NEWS_SOURCES if q == x["query"] + " when:1d"), None)
            if media is None:
                return []
            if media["name"] == "Reuters":
                raise ConnectionError("prueba de interrupción")
            return [self.item(media)]
        with patch.object(news, "fetch_rss", side_effect=fake_rss), patch.object(news, "GNEWS_API_KEY", ""):
            result = news.collect(self.now)
        self.assertEqual(len(result), sum(m.get("enabled", True) for m in WORLD_NEWS_SOURCES) - 1)

    def test_same_url_with_different_titles_is_single_article(self):
        first = self.item(WORLD_NEWS_SOURCES[0])
        first["title"] = "Titular original del artículo"
        second = {**first, "title": "Otro título completamente distinto",
                  "source": "Medio colaborador"}
        stories = []
        self.assertEqual(news.merge(stories, [first, second], self.now), 1)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["sources"], ["Reuters", "Medio colaborador"])
        self.assertEqual(stories[0]["link"], first["link"])

    def test_search_filters_out_stale_and_future_articles(self):
        media = WORLD_NEWS_SOURCES[0]
        def fake_rss(url, category, default_source=None):
            q = parse_qs(urlsplit(url).query).get("q", [""])[0]
            if q != media["query"] + " when:1d":
                return []
            return [
                {**self.item(media, 1), "published": "2026-10-19T16:00:00Z"},
                {**self.item(media, 2), "published": "2026-10-20T18:30:00Z"},
                {**self.item(media, 3), "published": "2026-10-20T17:30:00Z"},
            ]
        with patch.object(news, "fetch_rss", side_effect=fake_rss), patch.object(news, "GNEWS_API_KEY", ""):
            found = news.collect(self.now)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["title"], "Tema mundial único Reuters 3")

    def test_source_rejects_link_spoofing_and_untrusted_direct_destinations(self):
        media = WORLD_NEWS_SOURCES[0]
        story = self.item(media)
        self.assertTrue(matches_world_source(story, media))
        self.assertTrue(matches_world_source({**story, "link": "https://news.google.com/rss/articles/xyz"}, media))
        for bad in ("http://reuters.com/world",
                    "https://evil.example/world",
                    "https://reuters.com.evil.example/world",
                    "https://reuters.com@evil.example/world",
                    "javascript:alert(1)"):
            self.assertFalse(matches_world_source({**story, "link": bad}, media))

    def test_same_canonical_path_dedupes_tracking_parameters(self):
        first = self.item(WORLD_NEWS_SOURCES[0])
        first["link"] = "https://www.reuters.com/world/example?utm_source=rss"
        second = {**first, "title": "Titular muy diferente al inicial",
                  "link": "https://www.reuters.com/world/example?utm_campaign=feed"}
        stories = []
        self.assertEqual(news.merge(stories, [first, second], self.now), 1)
        self.assertEqual(len(stories), 1)

    def test_collection_does_not_create_news_without_publication_date(self):
        media = WORLD_NEWS_SOURCES[0]
        def fake_rss(url, category, default_source=None):
            q = parse_qs(urlsplit(url).query).get("q", [""])[0]
            return [{**self.item(media), "published": None}] if q == media["query"] + " when:1d" else []
        with patch.object(news, "fetch_rss", side_effect=fake_rss), patch.object(news, "GNEWS_API_KEY", ""):
            self.assertEqual(news.collect(self.now), [])


if __name__ == "__main__":
    unittest.main()
