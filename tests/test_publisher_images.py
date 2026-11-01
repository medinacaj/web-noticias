"""Pruebas sin red de recuperación de imágenes oficiales."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts.article_images import (
    image_from_html, permitted_url, enrich_visible_images, is_google_news,
)


class PublisherImagesTests(unittest.TestCase):
    def test_initial_section_cards_are_enriched_before_hidden_national_cards(self):
        now = datetime(2026, 10, 26, tzinfo=timezone.utc)
        national = [{'category': 'nacional', 'link': f'https://medio.example/n/{i}', 'image': ''} for i in range(24)]
        latam = [{'category': 'latinoamerica', 'link': f'https://medio.example/l/{i}', 'image': ''} for i in range(6)]
        selected = {'lead': None, 'secondary': [], 'by_category': {'nacional': national, 'latinoamerica': latam}}
        with patch('scripts.article_images.permitted_url', return_value=True):
            enrich_visible_images(national + latam, selected, now, max_lookups=12,
                                  fetch_image=lambda url: 'https://medio.example/photo.jpg')
        self.assertTrue(all(story['image'] for story in latam))
        self.assertFalse(national[6]['image'])

    def test_visible_images_are_spread_across_categories_before_hidden_items(self):
        now = datetime(2026, 11, 1, tzinfo=timezone.utc)
        first = [{"category": "nacional", "link": f"https://editor.example/n/{i}", "image": ""}
                 for i in range(24)]
        later = [{"category": "cultura", "link": f"https://editor.example/c/{i}", "image": ""}
                 for i in range(6)]
        selected = {"lead": None, "secondary": [], "by_category": {
            "nacional": first, "cultura": later}}
        visited = []
        def lookup(url):
            visited.append(url)
            return "https://editor.example/photo.jpg"
        with patch("scripts.article_images.permitted_url", return_value=True):
            count, checked = enrich_visible_images(
                first + later, selected, now, max_lookups=8,
                fetch_image=lookup)
        self.assertEqual((count, checked), (8, 8))
        self.assertEqual([x["link"] for x in later[:4]], visited[1:8:2])
        self.assertFalse(first[6]["image"])
        self.assertTrue(all(x["image"] for x in later[:4]))

    def test_extracts_official_open_graph_image(self):
        page = '''<html><head><meta property="og:image" content="/media/reportaje.jpg">
                  <meta name="twitter:image" content="https://cdn.example.com/other.jpg"></head></html>'''
        self.assertEqual(image_from_html(page, "https://medio.cl/articulos/42"),
                         "https://medio.cl/media/reportaje.jpg")

    def test_twitter_image_when_no_open_graph(self):
        page = '<meta name="twitter:image" content="https://imagenes.medio.cl/foto.webp">'
        self.assertEqual(image_from_html(page, "https://medio.cl/nota"),
                         "https://imagenes.medio.cl/foto.webp")

    def test_rejects_insecure_or_internal_picture_urls(self):
        for value in ('http://medio.cl/foto.jpg', 'javascript:alert(1)',
                      'https://localhost/foto.jpg', 'https://127.0.0.1/foto.jpg'):
            self.assertEqual(image_from_html(f'<meta property="og:image" content="{value}">',
                                             "https://medio.cl/nota"), "")

    def test_article_structured_image_supports_graph_lists_and_objects(self):
        import json
        for image in ('/foto.jpg', {'url': '/foto.jpg'}, [{'contentUrl': '/foto.jpg'}]):
            data = {'@graph': [{'@type': 'Organization', 'image': '/logo.jpg'},
                               {'@type': ['NewsArticle', 'Article'], 'image': image}]}
            page = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
            self.assertEqual(image_from_html(page, 'https://medio.cl/nota'), 'https://medio.cl/foto.jpg')

    def test_structured_images_ignore_logos_malformed_and_private_urls(self):
        for data in ('{oops', '{"@type":"Organization","image":"/logo.jpg"}',
                     '{"@type":"NewsArticle","image":"https://127.0.0.1/a.jpg"}'):
            page = '<script type="application/ld+json">' + data + '</script>'
            self.assertEqual(image_from_html(page, 'https://medio.cl/nota'), '')

    def test_open_graph_stays_preferred_over_structured_image(self):
        page = ('<meta property="og:image" content="/official.jpg">'
                '<script type="application/ld+json">{"@type":"NewsArticle","image":"/other.jpg"}</script>')
        self.assertEqual(image_from_html(page, 'https://medio.cl/nota'), 'https://medio.cl/official.jpg')

    def test_resolves_google_and_stores_photo_with_official_article(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        story = {"category": "nacional", "title": "Nota",
                 "sources": ["Mi Medio"], "image": "",
                 "source_url": "https://medio.cl",
                 "link": "https://news.google.com/rss/articles/CBMfoo"}
        selected = {"lead": story, "secondary": [], "by_category": {}}
        def resolve(urls, **kwargs):
            self.assertEqual(len(urls), 1)
            return {urls[0]: "https://medio.cl/nota"}
        with patch("scripts.article_images.permitted_url", return_value=True):
            count, checked = enrich_visible_images(
                [story], selected, now, decoder=resolve,
                fetch_image=lambda url: "https://medio.cl/foto.jpg")
        self.assertEqual((count, checked), (1, 1))
        self.assertEqual(story["link"], "https://medio.cl/nota")
        self.assertEqual(story["image"], "https://medio.cl/foto.jpg")

    def test_missing_photo_keeps_source_fallback_and_retries_later(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        story = {"category": "nacional", "title": "Nota", "image": "",
                 "sources": ["Mi Medio"], "link": "https://medio.cl/nota"}
        selected = {"lead": story, "secondary": [], "by_category": {}}
        with patch("scripts.article_images.permitted_url", return_value=True):
            self.assertEqual(enrich_visible_images(
                [story], selected, now, decoder=lambda *a, **kw: {},
                fetch_image=lambda url: ""), (0, 1))
            self.assertEqual(enrich_visible_images(
                [story], selected, now, decoder=lambda *a, **kw: {},
                fetch_image=lambda url: ""), (0, 0))
        self.assertEqual(story["image"], "")

    def test_google_links_identified_only_by_hostname(self):
        self.assertTrue(is_google_news("https://news.google.com/rss/articles/ABC"))
        self.assertFalse(is_google_news("https://news.google.com.evil.test/rss/articles/ABC"))
        self.assertFalse(is_google_news("https://medio.cl/nota"))

    def test_invalid_public_urls_rejected_without_dns(self):
        for url in ("http://example.com/a", "https://localhost/a",
                    "https://user:pw@example.com/a",
                    "https://example.com:8443/a", "https://127.0.0.1/a"):
            self.assertFalse(permitted_url(url, check_dns=False))


if __name__ == "__main__":
    unittest.main()
