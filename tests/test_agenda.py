"""Agenda: solo eventos validados, vigentes y con fuente; mismas tarjetas que las noticias; nunca bloquea la portada."""
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

    def test_crowded_region_does_not_push_out_the_others(self):
        # Caso real del 2026-10-24: 17 eventos de Santiago dejaban fuera al Biobío.
        santiago = [event(title=f"Obra {i}", commune="Santiago", region="Metropolitana",
                          source_url=f"https://m.cl/{i}", date="2026-10-25") for i in range(30)]
        payloads = {"https://x.cl/a.json": {"events": [event(date="2026-12-20")]},
                    "https://x.cl/b.json": {"events": santiago}}
        with patch.dict(os.environ, {}, clear=True):
            events = load_agenda(NOW, fetch=payloads.__getitem__, snapshots=self.SNAPSHOTS)
        regions = [e["region"] for e in events]
        self.assertEqual(regions.count("Metropolitana"), 12)
        self.assertIn("Biobío", regions)


class RenderAgendaTests(unittest.TestCase):
    def sample(self):
        return upcoming_events({"events": [
            event(region="Biobío", source_url="https://a.cl/1"),
            event(title="Feria", region="Valparaíso", commune="Valparaíso", category="Comunidad",
                  price_status="paid", price_text="$3.000", date="2026-10-25", time="",
                  source_url="https://a.cl/2")]}, TODAY)

    def test_empty_agenda_renders_nothing(self):
        self.assertEqual(render_agenda([], NOW), "")

    def test_card_escapes_text_and_links_to_source(self):
        events = upcoming_events({"events": [
            event(title="<script>alert(1)</script>", status="Por confirmar")]}, TODAY, "Biobío")
        html = render_agenda(events, NOW)
        self.assertNotIn("<script>", html)
        self.assertIn('rel="noopener" data-countries="" data-cat="Agenda" data-key="agenda"', html)
        self.assertIn(">alert(1)</a>", html)
        self.assertIn('href="https://teatrobiobio.cl/concierto/"', html)
        self.assertIn('<span class="source-country">Por confirmar</span>', html)

    def test_reuses_news_section_structure(self):
        html = render_agenda(self.sample(), NOW, number=12, source_mark=news.source_mark)
        self.assertIn('<span class="section-num">12</span><h2 id="titulo-agenda">Agenda</h2>', html)
        self.assertIn('<div class="section-grid" id="noticias-agenda"><ul class="compact-list">', html)
        self.assertIn('<li class="cat-agenda" data-region="Biobío" data-free><article class="compact">', html)
        self.assertIn('<li class="cat-agenda" data-region="Valparaíso"><article class="compact">', html)
        self.assertIn('class="media media--source media--date"', html)
        self.assertIn('<p class="kicker">Cultura · Concepción</p>', html)
        self.assertIn('<span class="source-mark"', html)
        self.assertIn('<span class="source-name">Teatro Biobío</span>', html)
        self.assertIn('<time datetime="2026-10-30T19:30:00-03:00">vie 30 oct, 19:30 h</time>', html)
        self.assertIn('<time datetime="2026-10-25T00:00:00-03:00">Mañana</time>', html)
        for absent in ("agenda-tag", "agenda-item", "agenda-note"):
            self.assertNotIn(absent, html)

    def test_official_poster_replaces_date_tile(self):
        [with_image] = upcoming_events({"events": [event(image_url="https://gam.cl/media/poster.png")]},
                                       TODAY, "Biobío")
        html = render_agenda([with_image], NOW)
        self.assertIn('<figure class="media"><img src="https://gam.cl/media/poster.png" alt=""', html)
        self.assertIn('loading="lazy"', html)
        self.assertNotIn("media--date", html)
        [unsafe] = upcoming_events({"events": [event(image_url="http://x.cl/a.png")]}, TODAY, "Biobío")
        self.assertIn("media--date", render_agenda([unsafe], NOW))

    def test_ongoing_event_shows_today_until_end(self):
        [item] = upcoming_events({"events": [event(date="2026-10-20", end_date="2026-11-02", time="")]},
                                 TODAY, "Biobío")
        self.assertIn(">Hoy al 2 nov</time>", render_agenda([item], NOW))

    def test_filters_hidden_until_js_and_only_when_useful(self):
        html = render_filters(self.sample())
        self.assertIn("data-agenda-filters hidden", html)
        self.assertIn('class="density-switch" data-agenda-region="" aria-pressed="true">Todo Chile', html)
        self.assertIn('data-agenda-region="Valparaíso"', html)
        self.assertIn("data-agenda-free", html)
        [single] = upcoming_events({"events": [event()]}, TODAY, "Biobío")
        self.assertEqual(render_filters([single]), "")

    def test_template_script_reveals_and_applies_filters(self):
        page = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn('d.querySelector("[data-agenda-filters]")', page)
        self.assertIn("box.hidden = false;", page)
        self.assertIn("#noticias-agenda li[data-filtered]{display:none !important;}", page)

    def test_site_numbers_agenda_after_news_sections(self):
        stories = [{"category": cat, "title": f"Nota {i} de {cat}", "summary": "",
                    "image": "", "sources": [f"Medio {i}"], "link": f"https://medio{i}.cl/nota",
                    "published": f"2026-10-24T{10 - i % 5:02d}:00:00Z"}
                   for i, cat in enumerate(["nacional", "deportes"] * 4)]
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            news.build_site(stories, NOW, folder)
            empty = Path(folder, "index.html").read_text(encoding="utf-8")
            news.build_site(stories, NOW, folder, agenda=self.sample())
            full = Path(folder, "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="cat-agenda"', empty)
        self.assertNotIn('href="#cat-agenda"', empty)
        self.assertIn('<li><a class="cat-agenda" href="#cat-agenda">Agenda</a></li>', full)
        import re
        numbers = [int(n) for n in re.findall(r'<span class="section-num">(\d+)</span>', full)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))  # la agenda continúa la numeración
        self.assertIn(f'<span class="section-num">{numbers[-1]:02d}</span><h2 id="titulo-agenda">', full)
        self.assertEqual(full.count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()


class ManualAgendaFileTests(unittest.TestCase):
    """eventos/agenda_manual.json: cada evento cargado a mano debe poder publicarse tal cual."""

    def test_manual_events_are_complete_and_cite_the_organizer(self):
        import json
        payload = json.loads((ROOT / "eventos" / "agenda_manual.json").read_text(encoding="utf-8"))
        self.assertIsInstance(payload.get("events"), list)
        for item in payload["events"]:
            with self.subTest(item.get("title")):
                for field in ("title", "date", "commune", "region", "source_url", "source"):
                    self.assertTrue(item.get(field), field)
                self.assertTrue(item["source_url"].startswith("https://"))
                date.fromisoformat(item["date"])
                if item.get("time"):
                    self.assertRegex(item["time"], r"^([01]\d|2[0-3]):[0-5]\d$")
                self.assertEqual(upcoming_events({"events": [item]}, date(1970, 1, 1))[0]["title"],
                                 item["title"])


class LocalSnapshotTests(unittest.TestCase):
    def test_reads_local_files_and_skips_missing_ones(self):
        import json
        from scripts.agenda import fetch_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            path.write_text(json.dumps({"events": [event()]}), encoding="utf-8")
            self.assertEqual(fetch_snapshot(str(path))["events"][0]["title"], "Concierto en el Teatro")
            snapshots = (("A", str(path), "Biobío"), ("B", str(Path(tmp) / "falta.json"), ""))
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(len(load_agenda(NOW, snapshots=snapshots)), 1)
