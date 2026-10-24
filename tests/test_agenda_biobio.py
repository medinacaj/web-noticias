"""Agenda Biobío: solo eventos validados, vigentes y con fuente; nunca bloquea la portada."""
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_noticias as news
from scripts.agenda_biobio import load_agenda, render_agenda, upcoming_events

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
TODAY = date(2026, 10, 24)


def event(**changes):
    base = {"title": "Concierto en el Teatro", "date": "2026-10-30", "time": "19:30",
            "venue": "Teatro Biobío", "commune": "Concepción", "price_text": "Gratis",
            "status": "Confirmado", "source": "Teatro Biobío",
            "source_url": "https://teatrobiobio.cl/concierto/"}
    base.update(changes)
    return base


class UpcomingEventsTests(unittest.TestCase):
    def test_only_validated_events_list_is_used(self):
        payload = {"events": [], "possible_events": [event(title="Publicación de seleccionados")]}
        self.assertEqual(upcoming_events(payload, TODAY), [])

    def test_filters_past_cancelled_incomplete_and_unsafe_links(self):
        payload = {"events": [
            event(title="Pasado", date="2026-10-01", source_url="https://a.cl/1"),
            event(title="Cancelado", status="Cancelado", source_url="https://a.cl/2"),
            event(title="Sin comuna", commune="", source_url="https://a.cl/3"),
            event(title="Inseguro", source_url="javascript:alert(1)"),
            event(title="HTTP", source_url="http://a.cl/4"),
            event(title="Fecha rota", date="30-10-2026", source_url="https://a.cl/5"),
            event(title="Feria en curso", date="2026-10-20", end_date="2026-10-26",
                  source_url="https://a.cl/6"),
            event(title="Válido", source_url="https://a.cl/7"),
            event(title="Duplicado", source_url="https://a.cl/7"),
        ]}
        titles = [e["title"] for e in upcoming_events(payload, TODAY)]
        self.assertEqual(titles, ["Feria en curso", "Válido"])

    def test_sorted_by_date_and_limited(self):
        payload = {"events": [event(title=f"E{i}", date=f"2026-11-{10 - i:02d}",
                                    source_url=f"https://a.cl/{i}") for i in range(9)]}
        events = upcoming_events(payload, TODAY)
        self.assertEqual(len(events), 6)
        self.assertEqual([e["date"] for e in events], sorted(e["date"] for e in events))

    def test_malformed_payloads_yield_nothing(self):
        for payload in (None, [], {"events": "x"}, {"events": [None, 3, "a"]}):
            self.assertEqual(upcoming_events(payload, TODAY), [])

    def test_network_failure_returns_empty_agenda(self):
        def broken(url):
            raise OSError("sin red")
        self.assertEqual(load_agenda(NOW, url="https://x.cl/e.json", fetch=broken), [])
        self.assertEqual(load_agenda(NOW, url="", fetch=broken), [])


class RenderAgendaTests(unittest.TestCase):
    def test_empty_agenda_renders_nothing(self):
        self.assertEqual(render_agenda([], NOW), "")

    def test_card_escapes_text_and_links_to_source(self):
        events = upcoming_events({"events": [
            event(title="<script>alert(1)</script>", status="Por confirmar")]}, TODAY)
        html = render_agenda(events, NOW)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn('href="https://teatrobiobio.cl/concierto/" target="_blank" rel="noopener"', html)
        self.assertIn('<time class="agenda-date" datetime="2026-10-30">', html)
        self.assertIn("Teatro Biobío · 19:30 h · Gratis", html)
        self.assertIn('<span class="agenda-status">Por confirmar</span>', html)
        self.assertIn('id="cat-agenda"', html)

    def test_site_shows_section_and_nav_only_with_events(self):
        stories = [{"category": "nacional", "title": "Nota nacional", "summary": "",
                    "image": "", "sources": ["Medio"], "link": "https://medio.cl/nota",
                    "published": "2026-10-24T11:00:00Z"}]
        agenda = upcoming_events({"events": [event()]}, TODAY)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            news.build_site(stories, NOW, folder)
            empty = Path(folder, "index.html").read_text(encoding="utf-8")
            news.build_site(stories, NOW, folder, agenda=agenda)
            full = Path(folder, "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="cat-agenda"', empty)
        self.assertNotIn('href="#cat-agenda"', empty)
        self.assertNotIn("%%AGENDA%%", empty)
        self.assertIn('<a class="cat-agenda" href="#cat-agenda">Agenda</a>', full)
        self.assertIn('<h2 id="titulo-agenda">Agenda Biobío</h2>', full)
        self.assertEqual(full.count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
