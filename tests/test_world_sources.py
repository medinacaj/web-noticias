"""Preparación mundial opt-in: gates, límites y contrato real de ingesta."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape

import fetch_noticias as news
from scripts.article_images import enrich_visible_images
from scripts.dedupe_history import deduplicate

try:
    world = importlib.import_module("scripts.global_sources")
except ModuleNotFoundError:
    world = None

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
EMPTY = b"<rss><channel/></rss>"


def source(number=0, **changes):
    return {"id": f"world-{number}", "name": f"Editor mundial {number}",
            "domain": f"editor{number}.example", "search_scope": f"editor{number}.example/world",
            "language": "en", "enabled": True, "permission_status": "approved",
            "technical_status": "verified", "permission_evidence": "Fixture autorizado para pruebas",
            **changes}


def item(media=None, index=0, **changes):
    media = media or source()
    return {"category": "internacional", "title": f"World headline {index}",
            "source": media["name"], "source_url": f'https://www.{media["domain"]}',
            "link": f'https://www.{media["domain"]}/world/article-{index}',
            "published": news.to_iso(NOW - timedelta(hours=1)),
            "summary": "Extracto que no se debe conservar", "image": "https://photo.example/p.jpg",
            **changes}


def rss(records):
    rows = []
    for record in records:
        text = lambda value: escape(str(value or ""))
        rows.append('<item><title>' + text(record.get("title")) + '</title><link>'
                    + text(record.get("link")) + '</link><source url="'
                    + text(record.get("source_url")) + '">' + text(record.get("source"))
                    + '</source><pubDate>' + text(record.get("published"))
                    + '</pubDate><description>Contenido que no debe copiarse</description>'
                    + '<enclosure type="image/jpeg" url="https://photo.example/p.jpg"/></item>')
    return ('<rss><channel>' + ''.join(rows) + '</channel></rss>').encode()


class WorldSourcesTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(world, "Falta preparación mundial con gates desactivados")

    def collect(self, fetch, catalog=None, gnews=None):
        catalog = world.load_catalog() if catalog is None else catalog
        with patch("scripts.global_sources.load_catalog", return_value=catalog), \
             patch.object(news, "http_get", side_effect=fetch), \
             patch.object(news, "GNEWS_API_KEY", "fixture" if gnews else ""), \
             patch.object(news, "fetch_gnews", side_effect=gnews or (lambda cat: [])), \
             patch("scripts.regional_sources.collect_regional", return_value=[]):
            return news.collect(NOW)

    def test_catalog_all_candidates_are_off_with_unknown_permission_and_guardian_restricted(self):
        catalog = world.load_catalog()
        self.assertEqual({x["name"] for x in catalog}, {
            "Reuters", "Associated Press", "Al Jazeera English", "NHK World-Japan", "NPR World",
            "DW Español", "France 24 Español", "CNN en Español", "El País Internacional",
            "Euronews Español", "The Guardian"})
        self.assertEqual(len({x["id"] for x in catalog}), len(catalog))
        self.assertTrue(all(x.get("enabled") is False and not x.get("permission_evidence")
                            and x.get("technical_status") != "verified" for x in catalog))
        self.assertEqual(next(x for x in catalog if x["name"] == "The Guardian")["permission_status"], "restricted")
        self.assertTrue(all(x["permission_status"] in ("pending", "restricted") for x in catalog))
        self.assertIn(("https://feeds.bbci.co.uk/mundo/rss.xml", "BBC News Mundo"), news.DIRECT_FEEDS["internacional"])

    def test_default_catalog_makes_zero_extra_queries_and_keeps_six_gnews_calls(self):
        requests, api = [], []
        self.collect(lambda url: requests.append(url) or EMPTY,
                     gnews=lambda cat: api.append(cat["key"]) or [])
        self.assertEqual(len(api), 6)
        self.assertFalse(any("site:" in parse_qs(urlsplit(url).query).get("q", [""])[0] for url in requests))
        # Latam extra + BBC + dos ediciones de entretenimiento + búsquedas de cine y conciertos en Chile.
        self.assertEqual(len(requests), len(news.CATEGORIES) + 6)
        editions = [parse_qs(urlsplit(url).query).get("gl") for url in requests]
        self.assertIn(["ES"], editions)
        self.assertIn(["MX"], editions)

    def test_each_missing_gate_prevents_requests_and_guardian_stays_blocked(self):
        variants = [("enabled", False), ("enabled", "true"), ("permission_status", "pending"),
                    ("permission_status", "restricted"), ("technical_status", "pending"),
                    ("permission_evidence", ""), ("permission_evidence", None)]
        for key, value in variants:
            with self.subTest(key=key, value=value):
                requests = []
                self.assertEqual(world.collect_world(NOW, fetch=lambda *a, **k: requests.append(a) or [],
                                                     catalog=[source(**{key: value})]), [])
                self.assertEqual(requests, [])

    def test_active_collection_caps_ten_queries_four_items_and_localizes(self):
        catalog = [source(i, language="es" if i % 2 else "en") for i in range(12)]
        requests = []
        def fetch(url):
            params = parse_qs(urlsplit(url).query)
            query = params.get("q", [""])[0]
            medium = next((m for m in catalog if query == f'site:{m["search_scope"]} when:1d'), None)
            if medium is None:
                return EMPTY
            requests.append((medium, params))
            return rss([item(medium, i) for i in range(9)])
        records = self.collect(fetch, catalog)
        self.assertEqual(len(requests), 10)
        self.assertEqual(len(records), 40)
        for medium, params in requests:
            self.assertEqual(params["hl"], ["es-419"] if medium["language"] == "es" else ["en-US"])
            self.assertEqual(params["ceid"], ["CL:es-419"] if medium["language"] == "es" else ["US:en"])
            self.assertEqual(sum(x["publisher_id"] == medium["id"] for x in records), 4)
        self.assertTrue(all(x["metadata_only"] and x["summary"] == "" and x["image"] == "" for x in records))
        self.assertTrue(all(x["category"] == "internacional" for x in records))
        self.assertFalse(any("image_fetch_disabled" in x for x in records))

    def test_failed_source_does_not_block_other_sources(self):
        catalog = [source(0), source(1)]
        def fetch(url):
            query = parse_qs(urlsplit(url).query).get("q", [""])[0]
            if "site:editor0.example" in query:
                raise OSError("fixture failure")
            return rss([item(catalog[1])]) if "site:editor1.example" in query else EMPTY
        records = self.collect(fetch, catalog)
        self.assertEqual([x["publisher_id"] for x in records], ["world-1"])

    def test_invalid_xml_is_isolated_to_its_source(self):
        catalog = [source(0), source(1)]
        for invalid in (b"<broken", b'<?xml version="1.0" encoding="unknown_codec"?><rss/>'):
            with self.subTest(invalid=invalid):
                def fetch(url):
                    query = parse_qs(urlsplit(url).query).get("q", [""])[0]
                    if "site:editor0.example" in query:
                        return invalid
                    return rss([item(catalog[1])]) if "site:editor1.example" in query else EMPTY
                found = self.collect(fetch, catalog)
                self.assertEqual([record["publisher_id"] for record in found], ["world-1"])

    def test_raw_rss_rejects_naive_missing_stale_future_dates_before_normalization(self):
        invalid = [None, "bad-date", "2026-10-24T11:00:00", "Fri, 24 Oct 2026 11:00:00 -0000",
                   news.to_iso(NOW - timedelta(hours=24, seconds=1)),
                   news.to_iso(NOW + timedelta(minutes=15, seconds=1))]
        records = [item(index=i, published=date) for i, date in enumerate(invalid)]
        records += [item(index=50, published=news.to_iso(NOW - timedelta(hours=24))),
                    item(index=51, published=news.to_iso(NOW + timedelta(minutes=15)))]
        found = self.collect(lambda url: rss(records) if "site%3A" in url else EMPTY, [source()])
        self.assertEqual({x["link"] for x in found}, {records[-2]["link"], records[-1]["link"]})

    def test_generic_world_bbc_and_gnews_keep_their_previous_policy(self):
        medium = world.load_catalog()[0]
        record = item(medium)
        # The new pending catalogue controls only the new directed collector.
        for target in ("world", "bbc", "gnews"):
            with self.subTest(target=target):
                def fetch(url):
                    matches = (target == "world" and "/topic/WORLD?" in url) or (
                        target == "bbc" and url == "https://feeds.bbci.co.uk/mundo/rss.xml")
                    return rss([record]) if matches else EMPTY
                found = self.collect(fetch, gnews=(lambda cat: [record] if target == "gnews" and
                                     cat["key"] == "internacional" else []))
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["link"], record["link"])
                self.assertTrue(found[0]["summary"])
                self.assertTrue(found[0]["image"])
                self.assertFalse(found[0].get("metadata_only"))

    def test_unrepresentable_utc_dates_do_not_discard_valid_items_or_other_editors(self):
        catalog = [source(0), source(1)]
        for extreme in ("9999-12-31T23:59:59-12:00", "0001-01-01T00:00:00+12:00"):
            with self.subTest(date=extreme):
                def fetch(url):
                    query = parse_qs(urlsplit(url).query).get("q", [""])[0]
                    for medium in catalog:
                        if query == f'site:{medium["search_scope"]} when:1d':
                            return rss([item(medium, index=0, published=extreme),
                                        item(medium, index=1)])
                    return EMPTY
                records = self.collect(fetch, catalog)
                self.assertEqual(len(records), 2)
                self.assertEqual({record["publisher_id"] for record in records}, {"world-0", "world-1"})
                self.assertTrue(all(record["link"].endswith("article-1") for record in records))

    def test_explicit_metadata_mode_validates_date_without_changing_category(self):
        records = [item(index=0, published="2026-10-24T11:00:00"), item(index=1)]
        with patch.object(news, "http_get", return_value=rss(records)):
            found = news.fetch_rss("https://news.google.com/rss/search", "internacional", metadata_only=True)
        self.assertEqual([record["category"] for record in found], ["internacional", "internacional"])
        self.assertIsNone(found[0]["published"])
        self.assertEqual(found[1]["published"], records[1]["published"])
        self.assertTrue(all(not record["summary"] and not record["image"] for record in found))

    def test_source_and_link_must_match_https_editorial_domain_or_google_exactly(self):
        medium = source()
        invalid = [("source_url", ""), ("source_url", "http://editor0.example"),
                   ("source_url", "https://editor0.example.evil.test"),
                   ("source_url", "https://user@editor0.example"),
                   ("link", "https://otro.example/article"), ("link", "https://editor0.example.evil.test/a"),
                   ("link", "https://127.0.0.1/a"), ("link", "https://editor0.example:444/a"),
                   ("link", "https://news.google.com.evil.example/rss/articles/x"),
                   ("link", "https://news.google.com/"), ("link", "https://news.google.com/rss/articles/"),
                   ("link", "https://editor0.example/a\x00"), ("link", "https://editor0.example/"),
                   ("link", "javascript:alert(1)"), ("link", "https://editor0.example\\@evil.test/a")]
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                self.assertIsNone(world.prepare_item(item(medium, **{field: value}), medium, NOW))
        self.assertIsNotNone(world.prepare_item(item(medium, link="https://news.google.com/rss/articles/ABC"), medium, NOW))

    def test_tracking_duplicates_count_once_while_distinct_article_ids_survive(self):
        records = [item(link="https://editor0.example/a?id=1&utm_source=rss"),
                   item(title="Completely different title", link="https://editor0.example/a?id=1&utm_campaign=other"),
                   item(link="https://editor0.example/a?id=2"), item(link="https://editor0.example/b")]
        found = self.collect(lambda url: rss(records) if "site%3A" in url else EMPTY, [source()])
        self.assertEqual(len(found), 3)
        stories = []
        news.merge(stories, found, NOW)
        self.assertEqual(len(stories), 3)

    def test_metadata_survives_load_save_merge_dedupe_and_never_enriches(self):
        records = self.collect(lambda url: rss([item(title="Brasil y Venezuela anuncian acuerdo")]) if "site%3A" in url else EMPTY, [source()])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["category"], "latinoamerica")
        stories = []
        news.merge(stories, records, NOW)
        raw = {**deepcopy(stories[0]), "summary": "Prohibido", "image": "https://photo.example/p.jpg", "metadata_only": False}
        merged = deduplicate([raw, deepcopy(stories[0])])
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0]["summary"], merged[0]["image"]), ("", ""))
        self.assertEqual(merged[0]["publisher_id"], source()["id"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            news.save_history(path, merged, NOW)
            loaded = news.load_history(path)
        self.assertEqual(loaded[0]["coverage_countries"], ["BR", "VE"])
        self.assertTrue(loaded[0]["metadata_only"])
        def unexpected(*args, **kwargs):
            self.fail("No decoder ni artículo para metadata_only")
        self.assertEqual(enrich_visible_images(loaded, {"lead": loaded[0], "secondary": [], "by_category": {}},
                         NOW, decoder=unexpected, fetch_image=unexpected), (0, 0))
