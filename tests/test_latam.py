"""Latinoamérica comparte portal; país del hecho y del editor son distintos."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import fetch_noticias as news
from scripts.dedupe_history import deduplicate

NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


def item(title="Brasil anuncia novas medidas", **changes):
    return dict(category="internacional", title=title, link="https://medio.example/nota",
                source="Medio", source_url="https://medio.example", published=news.to_iso(NOW),
                summary="Extracto", image="https://medio.example/foto.jpg") | changes


class LatamTests(unittest.TestCase):
    def test_explicit_countries_and_controlled_demonyms_classify_without_publisher_inference(self):
        examples = [("Brasil y Venezuela acuerdan con Argentina", ["AR", "BR", "VE"]),
                    ("Brasileiros e peruanos celebram", ["BR", "PE"]),
                    ("México y República Dominicana dialogan con Costa Rica", ["CR", "DO", "MX"]),
                    ("La cooperación ecuatoriana y uruguaya", ["EC", "UY"])]
        for title, countries in examples:
            with self.subTest(title=title):
                stories = []
                news.merge(stories, [item(title)], NOW)
                self.assertEqual(stories[0]["category"], "latinoamerica")
                self.assertEqual(stories[0]["coverage_countries"], countries)
        stories = []
        news.merge(stories, [item("Francia anuncia cambios", source_country="BR")], NOW)
        self.assertEqual(stories[0]["category"], "internacional")
        self.assertEqual(stories[0].get("coverage_countries", []), [])
        for category in ("nacional", "regiones", "politica"):
            record = item("Chile y Brasil acuerdan cooperación")
            record["category"] = category
            stories = []
            news.merge(stories, [record], NOW)
            self.assertEqual(stories[0]["category"], category)
        record = item("Chile anuncia medidas")
        record["category"] = "nacional"
        stories = []
        news.merge(stories, [record], NOW)
        self.assertEqual(stories[0]["category"], "nacional")

    def test_exact_url_tracking_reclassifies_existing_international_and_keeps_metadata(self):
        old = item("Acuerdo internacional")
        stories = []
        news.merge(stories, [old], NOW)
        new = item("Brasil y Venezuela firman acuerdo")
        new.update(category="latinoamerica", link=old["link"] + "?utm_source=rss",
                   coverage_countries=["BR", "VE"], metadata_only=True, source_country="BR")
        news.merge(stories, [new], NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["category"], "latinoamerica")
        self.assertEqual(stories[0]["coverage_countries"], ["BR", "VE"])
        self.assertEqual(stories[0]["source_country"], "BR")
        self.assertEqual(stories[0]["title"], new["title"])
        self.assertEqual((stories[0]["summary"], stories[0]["image"]), ("", ""))
        from scripts.article_images import enrich_visible_images
        self.assertEqual(enrich_visible_images(stories, {"lead": stories[0], "secondary": [], "by_category": {}},
                         NOW, fetch_image=lambda url: self.fail("metadata_only consulted article")), (0, 0))
        for pair in ([deepcopy(stories[0]), {**deepcopy(stories[0]), "coverage_countries": ["AR"]}],):
            self.assertEqual(deduplicate(pair)[0]["coverage_countries"], ["AR", "BR", "VE"])

    def test_latam_reclassification_prefers_valid_https_over_legacy_http(self):
        stories = []
        news.merge(stories, [item("Acuerdo internacional", link="http://medio.example/nota")], NOW)
        news.merge(stories, [item(metadata_only=True)], NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["category"], "latinoamerica")
        self.assertEqual(stories[0]["link"], "https://medio.example/nota")

    def test_legacy_history_load_save_and_invalid_records(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            record = item("Venezuela dialoga con Colombia")
            record.update(sources=[record.pop("source")], first_seen=news.to_iso(NOW))
            path.write_text(json.dumps({"noticias": [record]}))
            loaded = news.load_history(path)
            self.assertEqual(loaded[0]["category"], "latinoamerica")
            self.assertEqual(loaded[0]["coverage_countries"], ["CO", "VE"])
            news.save_history(path, loaded, NOW)
            self.assertEqual(news.load_history(path)[0]["coverage_countries"], ["CO", "VE"])
        stories = []
        record = item()
        record["category"] = "latinoamerica"
        record["link"] = "javascript:alert(1)"
        news.merge(stories, [record], NOW)
        self.assertEqual(stories, [])

    def test_metadata_only_import_cannot_keep_summary_or_image(self):
        stories = []
        record = item()
        record.update(category="latinoamerica", metadata_only=True)
        news.merge(stories, [record], NOW)
        self.assertEqual((stories[0]["summary"], stories[0]["image"]), ("", ""))

    def test_real_rss_parser_rejects_timezone_less_dates_and_discards_content(self):
        raw = b'''<rss><channel><item><title>Brasil anuncia medidas</title>
          <link>https://medio.example/a</link><source url="https://medio.example">Medio</source>
          <pubDate>Fri, 23 Oct 2026 11:00:00 GMT</pubDate><description>Extracto ajeno</description>
          <enclosure type="image/jpeg" url="https://medio.example/photo.jpg"/></item>
          <item><title>Venezuela anuncia medidas</title><link>https://medio.example/b</link>
          <source url="https://medio.example">Medio</source><pubDate>2026-10-23T11:00:00</pubDate>
          </item></channel></rss>'''
        for category, count in (("latinoamerica", 2), ("internacional", 1)):
            with self.subTest(category=category), patch.object(news, "http_get", return_value=raw), \
                 patch.object(news, "CATEGORIES", [{"key": category, "label": category, "google_topic": "WORLD"}]), \
                 patch.object(news, "DIRECT_FEEDS", {}), \
                 patch("scripts.regional_sources.collect_regional", return_value=[]):
                records = news.collect(NOW)
            self.assertEqual(len(records), count)
            self.assertTrue(all(x["title"] == "Brasil anuncia medidas" for x in records))
            self.assertTrue(all(not x["summary"] and not x["image"] for x in records))

    def test_catalog_gate_requires_every_activation_condition_even_through_aggregator(self):
        catalog = dict(name="Medio", domain="medio.example", enabled=True,
                       permission_status="approved", technical_status="verified",
                       permission_evidence="https://medio.example/permiso")
        variations = [("enabled", False), ("permission_status", "pending"),
                      ("permission_status", "restricted"), ("technical_status", "pending"),
                      ("permission_evidence", "")]
        for field, value in variations + [("enabled", True)]:
            with self.subTest(field=field, value=value), \
                 patch.object(news, "fetch_rss", return_value=[item()]), \
                 patch.object(news, "CATEGORIES", [{"key": "latinoamerica", "label": "Latinoamérica"}]), \
                 patch("scripts.regional_sources.load_catalog", return_value=[{**catalog, field: value}]), \
                 patch("scripts.regional_sources.collect_regional", return_value=[]):
                records = news.collect(NOW)
            self.assertEqual(len(records), 2 if value is True else 0)

    def test_blocked_legacy_is_tagged_but_stays_international(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            record = item("Brasil anuncia medidas", source_url="https://efectococuyo.com")
            record.update(sources=["Efecto Cocuyo"], first_seen=news.to_iso(NOW))
            path.write_text(json.dumps({"noticias": [record]}))
            loaded = news.load_history(path)
        self.assertEqual(loaded[0]["category"], "internacional")
        self.assertEqual(loaded[0]["coverage_countries"], ["BR"])
        self.assertEqual(loaded[0]["summary"], "Extracto")

    def test_new_items_require_editorial_links_or_exact_google_news_host(self):
        from scripts.latam import prepare_item
        for url in ("https://127.0.0.1/private", "https://otro.example/nota",
                    "https://news.google.com.evil.example/rss/articles/ABC",
                    "https://medio.example:444/nota", "https://medio.example/"):
            with self.subTest(url=url):
                self.assertIsNone(prepare_item(item(link=url), NOW, []))
        self.assertIsNotNone(prepare_item(item(link="https://news.google.com/rss/articles/ABC"), NOW, []))

    def test_collect_uses_two_localized_searches_and_no_extra_gnews(self):
        requests, api = [], []
        def rss(url, category, default_source=None, **kwargs):
            requests.append((url, category))
            if category != "latinoamerica":
                return []
            params = parse_qs(urlsplit(url).query)
            record = item("Brasil anuncia novas medidas" if params.get("gl") == ["BR"] else "Venezuela anuncia medidas")
            record["category"] = category
            record["link"] += "-" + str(len(requests))
            return [record]
        with patch.object(news, "fetch_rss", side_effect=rss), patch.object(news, "GNEWS_API_KEY", "fixture"), \
             patch.object(news, "fetch_gnews", side_effect=lambda cat: api.append(cat["key"]) or []), \
             patch("scripts.regional_sources.collect_regional", return_value=[]):
            collected = news.collect(NOW)
        latam = [(url, parse_qs(urlsplit(url).query)) for url, key in requests if key == "latinoamerica"]
        self.assertEqual(len(latam), 2)
        self.assertEqual(latam[0][1]["hl"], ["pt-BR"])
        self.assertEqual(latam[0][1]["gl"], ["BR"])
        self.assertEqual(latam[0][1]["ceid"], ["BR:pt-419"])
        self.assertIn("Brasil", latam[0][1]["q"][0])
        self.assertEqual(latam[1][1]["hl"], ["es-419"])
        self.assertEqual(len(api), 6)
        self.assertEqual(len(collected), 2)
        self.assertTrue(all(x["metadata_only"] and not x["summary"] and not x["image"] for x in collected))

    def test_world_feed_reclassification_cannot_bypass_metadata_or_catalog_gate(self):
        records = [item(), item("Venezuela anuncia medidas", source_url="https://www.elnacional.com")]
        def rss(url, category, default_source=None, **kwargs):
            return records if category == "internacional" and not default_source else []
        with patch.object(news, "fetch_rss", side_effect=rss), patch.object(news, "GNEWS_API_KEY", ""), \
             patch("scripts.regional_sources.collect_regional", return_value=[]):
            collected = news.collect(NOW)
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["category"], "latinoamerica")
        self.assertTrue(collected[0]["metadata_only"])
        self.assertEqual((collected[0]["summary"], collected[0]["image"]), ("", ""))

    def test_new_search_rejects_catalog_restrictions_bad_sources_and_dates_independently(self):
        base = item()
        base["category"] = "latinoamerica"
        invalid = []
        for field, value in (("source_url", ""), ("source_url", "http://medio.example"),
                             ("source_url", "https://127.0.0.1"), ("published", None),
                             ("published", "2026-10-23T11:00:00"),
                             ("published", news.to_iso(NOW - timedelta(hours=25))),
                             ("published", news.to_iso(NOW + timedelta(minutes=16)))):
            invalid.append({**base, field: value})
        invalid += [{**base, "title": "Francia anuncia medidas"},
                    {**base, "source_url": "https://www.elnacional.com"}]
        calls = []
        def rss(url, category, default_source=None, **kwargs):
            if category != "latinoamerica":
                return []
            calls.append(url)
            if len(calls) == 1:
                raise OSError("fixture feed failure")
            return invalid + [{**base, "published": news.to_iso(NOW + timedelta(minutes=15))}]
        with patch.object(news, "fetch_rss", side_effect=rss), patch.object(news, "GNEWS_API_KEY", ""), \
             patch("scripts.regional_sources.collect_regional", return_value=[]):
            records = news.collect(NOW)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["coverage_countries"], ["BR"])

    def test_generated_portal_has_latam_tags_filters_feed_and_single_canonical(self):
        stories = []
        records = []
        for index, category in enumerate(news.CATEGORY_LABELS):
            for offset in range(8):
                record = item(f"Brasil medida {offset}" if category == "latinoamerica" else f"Titular {category} {offset}")
                record.update(category=category, link=f"https://medio.example/{category}/{offset}",
                              metadata_only=True, summary="", image="")
                records.append(record)
        news.merge(stories, records, NOW)
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, NOW, folder)
            page = (Path(folder) / "index.html").read_text()
            self.assertIn('href="#cat-latinoamerica"', page)
            self.assertIn('class="coverage-country"', page)
            self.assertIn('data-countries="Brasil"', page)
            self.assertIn('data-key="latinoamerica"', page)
            self.assertIn('canonical" href="' + news.SITE_URL + '/"', page)
            self.assertNotIn('NewsArticle', page)
            for route in ("brasil", "venezuela"):
                self.assertFalse((Path(folder) / route).exists())
            root = ET.parse(Path(folder) / "rss/latinoamerica.xml").getroot()
            self.assertTrue(root.findall("./channel/item"))
            self.assertNotIn("Extracto", (Path(folder) / "rss/latinoamerica.xml").read_text())
