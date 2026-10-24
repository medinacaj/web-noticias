"""Agenda de eventos: solo validados, vigentes y con fuente; etiquetas y filtros; nunca bloquea la portada."""
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_noticias as news
from scripts.agenda import load_agenda, render_agenda, render_filters, upcoming_events

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
TODAY = date(2026, 10, 24)
ROOT = Path(__file__).resolve().parents[1]


def event(**changes):
    base = {"title": "Concierto en el Teatro", "date": "2026-10-30", "time": "19:30",
            "venue": "Teatro Biobío", "commune": "Concepción", "price_text": "Gratis",
            "price_status": "free", "category": "Cultura", "tags": ["música", "Música", "rock", "x"],
            "status": "Confirmado", "source": "Teatro Biobío",
            "source_url": "https://teatrobiobio.cl/concierto/"}
    base.update(changes)
    return base


class UpcomingEventsTests(unittest.TestCase):
    def test_only_validated_events_list_is_used(self):
        payload = {"events": [], "possible_events": [event(title="Publicación de seleccionados")]}
        self.assertEqual(upcoming_events(payload, TODAY, "Biobío"), [])

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
        titles = [e["title"] for e in upcoming_events(payload, TODAY, "Biobío")]
        self.assertEqual(titles, ["Feria en curso", "Válido"])

    def test_national_events_need_a_region(self):
        payload = {"events": [event(region="Valparaíso", commune="Valparaíso", source_url="https://a.cl/v"),
                              event(region=None, commune="Talca", source_url="https://a.cl/t")]}
        events = upcoming_events(payload, TODAY)
        self.assertEqual([(e["commune"], e["region"]) for e in events], [("Valparaíso", "Valparaíso")])

    def test_tags_are_normalized_and_limited(self):
        [item] = upcoming_events({"events": [event()]}, TODAY, "Biobío")
        self.assertEqual(item["tags"], ["música", "rock"])
        self.assertTrue(item["free"])

    def test_escaped_html_becomes_plain_text(self):
        # Caso real de GAM en national_events.json (2026-10-24).
        [item] = upcoming_events({"events": [event(
            venue="Centro Gabriela Mistral - GAM - &lt;p&gt;&lt;b&gt;Plaza Central&lt;/b&gt;&lt;/p&gt;",
            title="Trueque &amp;amp; Novelas")]}, TODAY, "Biobío")
        self.assertEqual(item["venue"], "Centro Gabriela Mistral - GAM - Plaza Central")
        self.assertEqual(item["title"], "Trueque & Novelas")
        html = render_agenda([item], NOW)
        self.assertIn("Trueque &amp; Novelas", html)
        self.assertNotIn("&lt;p&gt;", html)

    def test_malformed_payloads_yield_nothing(self):
        for payload in (None, [], {"events": "x"}, {"events": [None, 3, "a"]}):
            self.assertEqual(upcoming_events(payload, TODAY, "Biobío"), [])


class LoadAgendaTests(unittest.TestCase):
    SNAPSHOTS = (("AGENDA_A", "https://x.cl/a.json", "Biobío"), ("AGENDA_B", "https://x.cl/b.json", ""))

    def test_merges_snapshots_dedupes_and_survives_one_failure(self):
        payloads = {
            "https://x.cl/a.json": {"events": [event(source_url="https://a.cl/1", date="2026-11-02")]},
            "https://x.cl/b.json": {"events": [
                event(source_url="https://a.cl/1", region="Biobío"),
                event(title="En Valparaíso", commune="Valparaíso", region="Valparaíso",
                      source_url="https://a.cl/2", date="2026-10-25")]},
        }
        with patch.dict(os.environ, {}, clear=True):
            events = load_agenda(NOW, fetch=payloads.__getitem__, snapshots=self.SNAPSHOTS)
        self.assertEqual([(e["title"], e["region"]) for e in events],
                         [("En Valparaíso", "Valparaíso"), ("Concierto en el Teatro", "Biobío")])

        def broken(url):
            if url.endswith("a.json"):
                raise OSError("sin red")
            return payloads[url]
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(len(load_agenda(NOW, fetch=broken, snapshots=self.SNAPSHOTS)), 2)

    def test_empty_variable_disables_a_snapshot(self):
        def fetch(url):
            raise AssertionError("no debe consultarse")
        with patch.dict(os.environ, {"AGENDA_A": "", "AGENDA_B": ""}, clear=True):
            self.assertEqual(load_agenda(NOW, fetch=fetch, snapshots=self.SNAPSHOTS), [])


class RenderAgendaTests(unittest.TestCase):
    def sample(self):
        return upcoming_events({"events": [
            event(region="Biobío", source_url="https://a.cl/1"),
            event(title="Feria", region="Valparaíso", commune="Valparaíso", category="Comunidad",
                  price_status="paid", price_text="$3.000", tags=[], source_url="https://a.cl/2")]}, TODAY)

    def test_empty_agenda_renders_nothing(self):
        self.assertEqual(render_agenda([], NOW), "")

    def test_card_escapes_text_and_links_to_source(self):
        events = upcoming_events({"events": [
            event(title="<script>alert(1)</script>", status="Por confirmar")]}, TODAY, "Biobío")
        html = render_agenda(events, NOW)
        self.assertNotIn("<script>", html)
        self.assertIn('rel="noopener">alert(1)</a>', html)  # etiquetas eliminadas, texto escapado
        self.assertIn('href="https://teatrobiobio.cl/concierto/" target="_blank" rel="noopener"', html)
        self.assertIn('<time class="agenda-date" datetime="2026-10-30">', html)
        self.assertIn("Teatro Biobío · 19:30 h · Gratis", html)
        self.assertIn('<span class="agenda-status">Por confirmar</span>', html)

    def test_cards_carry_tags_and_filter_attributes(self):
        html = render_agenda(self.sample(), NOW)
        self.assertIn('<li data-region="Biobío" data-category="Cultura" data-free>', html)
        self.assertIn('<li data-region="Valparaíso" data-category="Comunidad">', html)
        for tag in ('agenda-tag--region">Valparaíso', 'agenda-tag--category">Comunidad',
                    'agenda-tag--free">Gratis', 'agenda-tag--tag">rock'):
            self.assertIn(tag, html)
        self.assertIn("2 eventos · 2 regiones", html)

    def test_filters_hidden_until_js_and_only_when_useful(self):
        html = render_filters(self.sample())
        self.assertIn("data-agenda-filters hidden", html)
        self.assertIn('data-agenda-filter="region"', html)
        self.assertIn('<option value="Valparaíso">Valparaíso</option>', html)
        self.assertIn('data-agenda-filter="category"', html)
        self.assertIn('data-agenda-filter="free"', html)
        [single] = upcoming_events({"events": [event()]}, TODAY, "Biobío")
        self.assertEqual(render_filters([single]), "")

    def test_template_script_reveals_and_applies_filters(self):
        page = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn('d.querySelector("[data-agenda-filters]")', page)
        self.assertIn("box.hidden = false;", page)
        self.assertIn(".agenda-list > li[hidden]{display:none;}", page)

    def test_site_shows_section_and_nav_only_with_events(self):
        stories = [{"category": "nacional", "title": "Nota nacional", "summary": "",
                    "image": "", "sources": ["Medio"], "link": "https://medio.cl/nota",
                    "published": "2026-10-24T11:00:00Z"}]
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            news.build_site(stories, NOW, folder)
            empty = Path(folder, "index.html").read_text(encoding="utf-8")
            news.build_site(stories, NOW, folder, agenda=self.sample())
            full = Path(folder, "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="cat-agenda"', empty)
        self.assertNotIn('href="#cat-agenda"', empty)
        self.assertNotIn("%%AGENDA%%", empty)
        self.assertIn('<a class="cat-agenda" href="#cat-agenda">Agenda</a>', full)
        self.assertIn('<h2 id="titulo-agenda">Agenda de eventos</h2>', full)
        self.assertEqual(full.count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
