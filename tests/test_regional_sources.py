"""Fuentes regionales: publicación mínima, atribución y activación explícita."""
import copy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import fetch_noticias as news
from scripts.regional_sources import collect_regional, fetch_feed, load_catalog, parse_feed


NOW = datetime(2026, 10, 21, 15, tzinfo=timezone.utc)


def source(**changes):
    return {"id": "fixture-ve", "name": "Medio venezolano", "country": "VE",
            "country_label": "Venezuela", "domain": "medio.example",
            "feed_url": "https://medio.example/noticias/feed/", "enabled": True,
            "permission_status": "approved", "technical_status": "verified",
            "permission_evidence": "https://medio.example/condiciones-rss/",
            **changes}


def feed(link="https://medio.example/economia/nota", title="Titular económico venezolano",
         category="Economía", date=None, author="Medio venezolano"):
    date = date or NOW.isoformat()
    return ("<rss><channel><item><title>" + title + "</title><link>" + link
            + "</link><pubDate>" + date + "</pubDate><category>" + category
            + "</category><source url=\"https://medio.example\">" + author
            + "</source><description>Texto ajeno que no debe copiarse</description>"
            + '<enclosure type="image/jpeg" url="https://medio.example/foto.jpg"/>'
            + "</item></channel></rss>").encode()


class RegionalSourcesTests(unittest.TestCase):
    def test_catalog_contains_six_venezuelan_candidates_without_activation(self):
        catalog = load_catalog()
        self.assertEqual({s["name"] for s in catalog if s["country"] == "VE"},
                         {"El Nacional", "El Universal Venezuela", "El Pitazo",
                          "Efecto Cocuyo", "TalCual", "Runrun.es"})
        self.assertTrue(all(not s["enabled"] for s in catalog))

    def test_approved_feed_keeps_attribution_country_and_original_title_only(self):
        records = parse_feed(feed(), source(), NOW)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_country"], "VE")
        self.assertEqual(records[0]["source_country_label"], "Venezuela")
        self.assertEqual(records[0]["category"], "economia")
        self.assertEqual(records[0]["title"], "Titular económico venezolano")
        self.assertEqual(records[0]["source"], "Medio venezolano")
        self.assertEqual(records[0]["summary"], "")
        self.assertEqual(records[0]["image"], "")
        self.assertTrue(records[0]["metadata_only"])

    def test_rejects_spoofed_or_non_editorial_destinations(self):
        for link in ("https://medio.example.evil.test/nota", "https://otro.example/nota",
                     "https://user:pass@medio.example/nota", "http://medio.example/nota",
                     "https://medio.example:444/nota", "https://medio.example/"):
            with self.subTest(link=link):
                self.assertEqual(parse_feed(feed(link=link), source(), NOW), [])

    def test_opinion_and_advertising_are_excluded_from_news(self):
        for category in ("Opinión", "Editorial", "Columnistas", "Publicidad", "Patrocinado"):
            self.assertEqual(parse_feed(feed(category=category), source(), NOW), [])
        self.assertEqual(parse_feed(feed(link="https://medio.example/opinion/nota"), source(), NOW), [])

    def test_unknown_topics_stay_in_international_not_chilean_national(self):
        self.assertEqual(parse_feed(feed(category="Nacional"), source(), NOW)[0]["category"],
                         "internacional")

    def test_rejects_missing_stale_future_or_invalid_dates(self):
        for date in ((NOW - timedelta(hours=25)).isoformat(),
                     (NOW + timedelta(hours=1)).isoformat(), "bad-date"):
            self.assertEqual(parse_feed(feed(date=date), source(), NOW), [])
        self.assertEqual(parse_feed(feed().replace(b"<pubDate>", b"<unknown>").replace(
            b"</pubDate>", b"</unknown>"), source(), NOW), [])

    def test_collection_never_requests_disabled_pending_or_unverified_sources(self):
        catalog = [source(enabled=False), source(permission_status="pending"),
                   source(technical_status="pending"), source(permission_status="restricted")]
        requests = []
        self.assertEqual(collect_regional(NOW, lambda url: requests.append(url), catalog), [])
        self.assertEqual(requests, [])

    def test_request_budget_limits_work_and_one_failure_does_not_stop_others(self):
        catalog = [source(id=str(i), name=f"Medio {i}") for i in range(20)]
        requests = []
        def fetch(url):
            requests.append(url)
            if len(requests) == 1:
                raise OSError("unavailable")
            return feed()
        records = collect_regional(NOW, fetch, catalog)
        self.assertEqual(len(requests), 16)
        self.assertTrue(records)

    def test_feed_item_budget_and_duplicate_urls(self):
        record = feed().decode().split("<item>")[1].split("</item>")[0]
        # Repetición de una misma nota no aumenta su presencia editorial.
        raw = ("<rss><channel>" + ("<item>" + record + "</item>") * 20 + "</channel></rss>")
        self.assertEqual(len(parse_feed(raw.encode(), source(), NOW)), 1)

    def test_merge_preserves_country_and_metadata_only_policy(self):
        stories = []
        news.merge(stories, parse_feed(feed(), source(), NOW), NOW)
        self.assertEqual(stories[0]["source_country_label"], "Venezuela")
        self.assertTrue(stories[0]["metadata_only"])
        self.assertIn("Venezuela", news.meta_html(stories[0], NOW))

    def test_metadata_only_story_is_never_queried_for_a_photo(self):
        from scripts.article_images import enrich_visible_images
        item = {"link": "https://medio.example/nota", "metadata_only": True,
                "sources": ["Medio"], "image": ""}
        selected = {"lead": item, "secondary": [], "by_category": {}}
        fetch = lambda url: self.fail("No consultar el artículo de una fuente de metadatos")
        self.assertEqual(enrich_visible_images([item], selected, NOW, fetch_image=fetch), (0, 0))

    def test_normalizing_duplicates_keeps_the_stricter_metadata_policy(self):
        from scripts.dedupe_history import deduplicate
        old = {"title": "Nota", "link": "https://medio.example/nota", "sources": ["Medio"],
               "image": "https://medio.example/foto.jpg", "summary": "Extracto"}
        regional = {**old, "image": "", "summary": "", "metadata_only": True,
                    "source_country": "VE", "source_country_label": "Venezuela"}
        result = deduplicate([old, regional])
        self.assertTrue(result[0]["metadata_only"])
        self.assertEqual(result[0]["image"], "")
        self.assertEqual(result[0]["summary"], "")
        self.assertEqual(result[0]["source_country"], "VE")

    def test_distinct_article_ids_survive_collection_merge_and_normalization(self):
        from scripts.dedupe_history import deduplicate
        a = parse_feed(feed(link="https://medio.example/noticia?id=1"), source(), NOW)
        b = parse_feed(feed(link="https://medio.example/noticia?id=2", title="Otro hecho diferente"), source(), NOW)
        stories = []
        news.merge(stories, a + b, NOW)
        self.assertEqual(len(deduplicate(stories)), 2)

    def test_private_feed_is_rejected_before_making_any_request(self):
        with patch("scripts.article_images.permitted_url", return_value=False), patch(
                "urllib.request.build_opener") as opener:
            with self.assertRaises(ValueError):
                fetch_feed("https://127.0.0.1/feed/")
            opener.assert_not_called()

    def test_country_label_is_escaped_in_generated_html(self):
        story = parse_feed(feed(), source(country_label='<script>alert(1)</script>'), NOW)[0]
        stories = []
        news.merge(stories, [story], NOW)
        self.assertNotIn("<script>", news.meta_html(stories[0], NOW))


class FrontpageDiversityTests(unittest.TestCase):
    def test_section_quota_groups_aliases_of_the_same_editor(self):
        from scripts.source_diversity import publisher_key
        candidates = []
        for editor, count in (("BBC", 3), ("BBC News Mundo", 3), ("Medio B", 3), ("Medio C", 3)):
            for i in range(count):
                candidates.append({"title": f"{editor} {i}", "sources": [editor]})
        result = news.balance_section_sources(candidates)
        self.assertEqual(sum(publisher_key(s) == "bbc.com" for s in result[:6]), 2)

    def test_lead_and_highlights_use_different_editors_without_losing_candidates(self):
        stories = []
        for name, count in (("BioBioChile", 6), ("Medio B", 3), ("Medio C", 3), ("Medio D", 3)):
            for i in range(count):
                stories.append({"title": f"{name} {i}", "link": f"https://{name.replace(' ', '').lower()}.example/{i}",
                                "category": "internacional", "sources": [name],
                                "published": NOW.isoformat(), "image": "", "summary": ""})
        before = copy.deepcopy(stories)
        selected = news.select(stories, NOW)
        editors = [s["sources"][0] for s in [selected["lead"]] + selected["secondary"]]
        self.assertEqual(len(set(editors)), 4)
        self.assertEqual(stories, before)
        shown = [selected["lead"]] + selected["secondary"] + selected["by_category"]["internacional"]
        self.assertEqual({id(s) for s in stories}, {id(s) for s in shown})

    def test_ineligible_singleton_does_not_consume_an_editors_quota(self):
        def article(editor, category, number, image=""):
            return {"title": f"{editor} {number}", "link": f"https://{editor}.example/{number}",
                    "category": category, "sources": [editor], "published": NOW.isoformat(),
                    "image": image, "summary": ""}
        stories = [article("a", "nacional", 0, "https://a.example/photo.jpg"),
                   article("b", "tecnologia", 1)]
        stories += [article("a", "internacional", i) for i in range(2, 5)]
        stories += [article("b", "internacional", 5)]
        selected = news.select(stories, NOW)
        self.assertIn("b", [s["sources"][0] for s in selected["secondary"]])
        self.assertEqual(len(selected["by_category"]["tecnologia"]), 1)
