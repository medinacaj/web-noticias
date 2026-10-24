"""Only the original template supplies interpolation tokens; RSS stays text."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from xml.sax.saxutils import escape

import fetch_noticias as news


NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


class TemplateInterpolationTests(unittest.TestCase):
    def rss_stories(self, title, source):
        raw = (
            '<rss><channel><item><title>' + escape(title) + '</title>'
            '<source url="https://publisher.example">' + escape(source) + '</source>'
            '<link>https://publisher.example/news/update</link>'
            '<pubDate>Sat, 24 Oct 2026 11:00:00 GMT</pubDate>'
            '</item></channel></rss>'
        ).encode()
        with patch.object(news, "http_get", return_value=raw):
            incoming = news.fetch_rss("https://news.google.com/rss/topic/WORLD", "internacional")
        stories = []
        self.assertEqual(news.merge(stories, incoming, NOW), 1)
        return stories

    def render_rss(self, title, source):
        stories = self.rss_stories(title, source)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            try:
                news.build_site(stories, NOW, folder)
            except SystemExit as error:
                self.fail(f"RSS text must not be interpreted as template tokens: {error}")
            return Path(folder, "index.html").read_text(encoding="utf-8")

    def test_rss_title_and_source_keep_unknown_marker_literal(self):
        title = "Market update %%REMOTE_MARKER%%"
        source = "Publisher %%REMOTE_MARKER%%"
        page = self.render_rss(title, source)
        self.assertIn(title, page)
        self.assertIn(source, page)

    def test_known_tokens_from_rss_are_never_interpolated(self):
        title = "Market %%TOP%% and %%ADSENSE_SCRIPT%%"
        source = "Publisher %%TOP%% and %%ADSENSE_SCRIPT%%"
        page = self.render_rss(title, source)
        self.assertIn(title, page)
        self.assertIn(source, page)
        structured = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        self.assertIsNotNone(structured)
        graph = json.loads(structured.group(1))["@graph"]
        self.assertEqual(graph[1]["mainEntity"]["itemListElement"][0]["name"], title)

    def test_unknown_template_token_preserves_previous_publication(self):
        stories = self.rss_stories("Market update", "Publisher")
        original = Path(news.TEMPLATE_PATH).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            template = Path(folder, "template.html")
            template.write_text(original + "\n%%UNKNOWN_STRUCTURE%%", encoding="utf-8")
            output = Path(folder, "public")
            output.mkdir()
            index = output / "index.html"
            index.write_text("previous edition", encoding="utf-8")
            with patch.object(news, "TEMPLATE_PATH", str(template)):
                with self.assertRaisesRegex(SystemExit, "%%UNKNOWN_STRUCTURE%%"):
                    news.build_site(stories, NOW, str(output))
            self.assertEqual(index.read_text(encoding="utf-8"), "previous edition")
            self.assertEqual(list(output.iterdir()), [index])


if __name__ == "__main__":
    unittest.main()
