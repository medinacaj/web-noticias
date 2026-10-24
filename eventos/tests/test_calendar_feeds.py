"""Calendarios estructurados de sitios oficiales y dominios municipales candidatos (sin red)."""
import json
import os
import tempfile
import unittest
from datetime import date

from tests.helpers import COMMUNES
import actualizar
from scrapers import calendar_feeds, deep_crawler
from scrapers.common import FetchResult

REF = date(2026, 10, 24)
MUNI = {"name": "Municipalidad de San Rosendo", "url": "https://www.sanrosendo.cl/", "official": True,
        "source_type": "municipal", "commune": "San Rosendo", "source_priority": 1, "parser": "generic"}
TRIBE = json.dumps({"events": [
    {"title": "Fiesta del Vino", "start_date": "2026-10-24 12:00:00", "end_date": "2026-10-25 20:00:00",
     "all_day": False, "url": "https://www.municipalidadsanrosendo.cl/evento/fiesta-del-vino/",
     "venue": {"venue": "Estación Turquía", "address": "Turquía", "city": "San Rosendo"},
     "image": {"url": "https://www.municipalidadsanrosendo.cl/afiche.jpg"}, "cost": "Gratis",
     "description": "<p>Música en vivo y vinos de la zona</p>"},
    {"title": "Feria ya realizada", "start_date": "2026-09-01 10:00:00", "end_date": "2026-09-01 12:00:00",
     "url": "https://www.municipalidadsanrosendo.cl/evento/feria/"},
]})
ICS = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nDTSTART:20261024T220000Z\r\n"
       "SUMMARY:Encuentro Folclórico\\, Del Mar al Cielo\r\nLOCATION:Centro Cívico Boca Sur\\, "
       "San Pedro de la Paz\r\nURL:https://www.sanpedrodelapaz.cl/evento/folclore/\r\nEND:VEVENT\r\n"
       "BEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261107\r\nDTEND;VALUE=DATE:20261109\r\nSUMMARY:Trail familiar\r\n"
       "LOCATION:Cerro Macera\\, Talcahuano\r\nURL:https://www.sanpedrodelapaz.cl/evento/trail/\r\nEND:VEVENT\r\n"
       "BEGIN:VEVENT\r\nDTSTART:20261030T100000\r\nSUMMARY:Sin enlace propio\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")


def fetcher(pages):
    def f(url, timeout=20, **kw):
        if url in pages:
            return FetchResult(url, 200, url, pages[url], "text/html")
        return FetchResult(url, 404, error="HTTP 404")
    return f


class CalendarFeedTests(unittest.TestCase):
    def test_events_calendar_json_becomes_published_events(self):
        events = calendar_feeds.events_from_tribe(TRIBE, MUNI, COMMUNES, REF)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual((ev["title"], ev["date"], ev["end_date"], ev["time"], ev["commune"], ev["venue"]),
                         ("Fiesta del Vino", "2026-10-24", "2026-10-25", "12:00", "San Rosendo", "Estación Turquía"))
        self.assertEqual((ev["price_status"], ev["status"], ev["description"]),
                         ("free", "Confirmado", "Música en vivo y vinos de la zona"))
        self.assertTrue(ev["image_url"].startswith("https://"))

    def test_ical_converts_utc_and_exclusive_all_day_end(self):
        source = dict(MUNI, name="Municipalidad de San Pedro de la Paz", commune="San Pedro de la Paz")
        events = calendar_feeds.events_from_ics(ICS, source, COMMUNES, REF)
        self.assertEqual([(e["title"], e["date"], e["end_date"], e["time"], e["commune"]) for e in events], [
            ("Encuentro Folclórico, Del Mar al Cielo", "2026-10-24", None, "19:00", "San Pedro de la Paz"),
            ("Trail familiar", "2026-11-07", "2026-11-08", None, "Talcahuano"),
        ])

    def test_discovers_linked_calendar_and_wordpress_endpoints(self):
        html = '<link rel="alternate" type="text/calendar" href="/agenda.ics"><link rel="stylesheet" href="x.css">'
        urls = calendar_feeds.feed_urls(html, "https://muni.cl/inicio")
        self.assertEqual(urls[0], "https://muni.cl/agenda.ics")
        self.assertEqual(calendar_feeds.feed_urls("<html>tribe-events</html>", "https://muni.cl/")[0],
                         "https://muni.cl" + calendar_feeds.TRIBE_PATH)

    def test_only_official_local_sources_publish_from_calendars(self):
        media = dict(MUNI, official=False, source_type="media")
        pages = {"https://www.sanrosendo.cl" + calendar_feeds.TRIBE_PATH: TRIBE}
        self.assertEqual(calendar_feeds.collect(media, "", MUNI["url"], COMMUNES, fetcher(pages), ref=REF), ([], []))
        events, live = calendar_feeds.collect(MUNI, "", MUNI["url"], COMMUNES, fetcher(pages), ref=REF)
        self.assertEqual((len(events), live), (1, ["https://www.sanrosendo.cl" + calendar_feeds.TRIBE_PATH]))


class DomainCandidateTests(unittest.TestCase):
    SOURCE = dict(MUNI, url="https://www.sanrosendo.cl/", url_candidates=[
        "https://www.sanrosendo.cl/", "https://www.municipalidadsanrosendo.cl/"])

    def test_first_candidate_that_presents_itself_as_the_municipality_wins(self):
        pages = {"https://www.sanrosendo.cl/": "<html><title>Dominio en venta</title></html>",
                 "https://www.municipalidadsanrosendo.cl/": "<html><h1>Ilustre Municipalidad de San Rosendo</h1></html>",
                 "https://www.municipalidadsanrosendo.cl" + calendar_feeds.TRIBE_PATH: TRIBE}
        res = deep_crawler.crawl(self.SOURCE, COMMUNES, fetcher=fetcher(pages), ref=REF)
        self.assertIsNone(res.error)
        self.assertEqual(res.resolved_url, "https://www.municipalidadsanrosendo.cl/")
        self.assertEqual([e["title"] for e in res.events], ["Fiesta del Vino"])

    def test_no_candidate_is_an_error_not_an_event(self):
        res = deep_crawler.crawl(self.SOURCE, COMMUNES, fetcher=fetcher({}), ref=REF)
        self.assertIn("Ningún dominio candidato", res.error)
        self.assertEqual(res.events, [])

    def test_verified_candidate_is_saved_in_sources_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sources.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"sources": [dict(self.SOURCE, enabled=True, notes="x", url_evidence="no_confirmado")]}, f)
            actualizar.update_sources_file(path, [{
                "source_name": MUNI["name"], "source_url": "https://www.municipalidadsanrosendo.cl/",
                "ok": 1, "http_status": 200, "finished_at": "2026-10-24T20:00:00"}])
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)["sources"][0]
        self.assertEqual(saved["url"], "https://www.municipalidadsanrosendo.cl/")
        self.assertNotIn("url_candidates", saved)
        self.assertEqual(saved["url_evidence"], "dominio_candidato_verificado_en_vivo")


if __name__ == "__main__":
    unittest.main()
