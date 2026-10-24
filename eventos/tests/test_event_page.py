"""Fichas de evento sin JSON-LD en fuentes oficiales (casos del rastreo real del 2026-10-24)."""
import unittest
from datetime import date

from tests.helpers import discovery
from scrapers import event_page, generic_events

CHILE = discovery.load_communes(discovery.CHILE_COMMUNES_PATH)
REF = date(2026, 10, 24)
MUNICIPAL = {"name": "Teatro Municipal de Santiago", "url": "https://www.municipal.cl/", "official": True,
             "source_type": "venue", "commune": "Santiago", "source_priority": 1}
MAULE = {"name": "Teatro Regional del Maule", "url": "https://www.teatroregional.cl/", "official": True,
         "source_type": "venue", "commune": "Talca", "source_priority": 1}
MINISTERIO = {"name": "Agenda Cultural del Ministerio de las Culturas",
              "url": "https://www.cultura.gob.cl/agendacultural/", "official": True,
              "source_type": "aggregator", "commune": None}
MUNI = {"name": "Municipalidad de Cañete", "url": "https://municanete.cl/", "official": True,
        "source_type": "municipal", "commune": "Cañete"}


def page(title, *blocks, og=""):
    meta = f'<meta property="og:title" content="{og}">' if og else ""
    body = "".join(f"<p>{b}</p>" for b in blocks)
    return f"<html><head><title>{title} | Sitio</title>{meta}</head><body><h1>{title}</h1>{body}</body></html>"


class EventPageTests(unittest.TestCase):
    def extract(self, html, url, source):
        return event_page.event_from_page(html, url, source, CHILE, REF)

    def test_venue_detail_page_becomes_event_por_confirmar(self):
        html = page("Elektra de Richard Strauss", "Martes 17 de noviembre – 18:00 horas / Ó1",
                    "Jueves 19 de noviembre – 19:00 horas", "Entradas desde $12.000")
        ev = self.extract(html, "https://municipal.cl/espectaculos/elektra-de-richard-strauss-2026/", MUNICIPAL)
        self.assertEqual((ev["title"], ev["date"], ev["end_date"], ev["time"], ev["commune"]),
                         ("Elektra de Richard Strauss", "2026-11-17", "2026-11-19", "18:00", "Santiago"))
        self.assertEqual(ev["status"], "Por confirmar")
        self.assertEqual((ev["price_value"], ev["price_status"]), (12000, "paid"))

    def test_regional_tour_uses_first_and_last_function(self):
        html = page("Gira Ópera Escolar 2026", "05 AL 12 DE NOVIEMBRE DE 2026",
                    "Jueves 5 de noviembre | 10:00 horas — Teatro Regional del Maule")
        ev = self.extract(html, "https://www.teatroregional.cl/archivo/28422", MAULE)
        self.assertEqual((ev["date"], ev["end_date"], ev["commune"]), ("2026-11-05", "2026-11-12", "Talca"))

    def test_listing_home_and_category_pages_are_not_events(self):
        html = page("Cartelera", "Martes 17 de noviembre – 18:00 horas")
        for url in ("https://municipal.cl/", "https://municipal.cl/espectaculos/",
                    "https://www.teatroregional.cl/archivo/category/eventos-especiales"):
            self.assertIsNone(self.extract(html, url, MUNICIPAL), url)

    def test_explicit_past_year_is_rejected(self):
        # CCLM: «9 al 19 de diciembre | 2020» se leía como diciembre de 2026.
        html = page("14 Muestra de Cine Iberoamericano", "9 al 19 de diciembre | 2020")
        source = dict(MUNICIPAL, name="Centro Cultural La Moneda", url="https://www.cclm.cl/")
        self.assertIsNone(self.extract(html, "https://www.cclm.cl/actividades/14-muestra-de-cine/", source))
        html = page("Ciudades nórdicas sustentables", "Diálogo realizado el 28 de octubre, 2020")
        self.assertIsNone(self.extract(html, "https://www.cclm.cl/actividades/ciudades-nordicas/", source))

    def test_inferred_year_far_away_is_rejected(self):
        # FTB: un taller de marzo (ya pasado) se inferiría como marzo de 2027.
        html = page("Taller de muralismo", "HORARIOS: 28 de marzo de 10:00 a 12:00 hrs.")
        ftb = dict(MUNICIPAL, name="FTB", url="https://ftb.cl/", commune="Concepción")
        self.assertIsNone(self.extract(html, "https://ftb.cl/taller-de-muralismo/", ftb))
        html = page("Taller de muralismo", "Fechas: 3 al 7 de noviembre.")
        self.assertEqual(self.extract(html, "https://ftb.cl/taller-de-muralismo/", ftb)["date"], "2026-11-03")

    def test_municipal_news_without_event_path_is_not_published(self):
        html = page("Conoce los seleccionados de la feria", "Publicación de seleccionados: 26 de octubre.")
        self.assertIsNone(self.extract(html, "https://municanete.cl/v2/conoce-los-seleccionados/", MUNI))
        ev = self.extract(page("Feria de Todos los Santos", "Sábado 31 de octubre, 10:00 hrs, Plaza"),
                          "https://municanete.cl/evento/feria-todos-los-santos/", MUNI)
        self.assertEqual((ev["commune"], ev["date"]), ("Cañete", "2026-10-31"))

    def test_aggregator_needs_commune_next_to_the_date(self):
        html = page("Día Mundial de la Ópera", "25 de octubre, Teatro Municipal de Nacimiento")
        url = "https://www.cultura.gob.cl/agendacultural/dia-mundial-de-la-opera/"
        self.assertEqual(self.extract(html, url, MINISTERIO)["commune"], "Nacimiento")
        html = page("Celebración regional", "25 de octubre")
        self.assertIsNone(self.extract(html, url, MINISTERIO))

    def test_unofficial_media_and_generic_titles_are_excluded(self):
        html = page("Concierto de jazz", "Sábado 31 de octubre, 20:00 hrs")
        media = dict(MUNICIPAL, official=False, source_type="media")
        self.assertIsNone(self.extract(html, "https://municipal.cl/espectaculos/jazz/", media))
        self.assertIsNone(self.extract(page("Cartelera", "Sábado 31 de octubre"),
                                       "https://municipal.cl/espectaculos/x/", MUNICIPAL))

    def test_logo_heading_is_not_taken_as_title(self):
        html = ('<html><head><meta property="og:title" content="Cascanueces | Teatro Municipal de Santiago">'
                '</head><body><h1>Teatro Municipal</h1><p>Lunes 14 de diciembre – 19:00 horas</p></body></html>')
        ev = self.extract(html, "https://municipal.cl/espectaculos/cascanueces-2026/", MUNICIPAL)
        self.assertEqual(ev["title"], "Cascanueces")
        html = "<html><body><h1>Teatro Municipal</h1><p>Lunes 14 de diciembre – 19:00 horas</p></body></html>"
        self.assertIsNone(self.extract(html, "https://municipal.cl/espectaculos/cascanueces-2026/", MUNICIPAL))

    def test_too_many_dates_looks_like_a_listing(self):
        blocks = [f"{d} de noviembre" for d in range(1, 20)]
        self.assertIsNone(self.extract(page("Programa del mes", *blocks),
                                       "https://municipal.cl/espectaculos/programa/", MUNICIPAL))

    def test_generic_extract_prefers_jsonld_and_falls_back_to_page(self):
        html = page("Cascanueces", "Lunes 14 de diciembre – 19:00 horas")
        events, possibles = generic_events.extract(html, "https://municipal.cl/espectaculos/cascanueces-2026/",
                                                   MUNICIPAL, CHILE, REF)
        self.assertEqual([e["title"] for e in events], ["Cascanueces"])
        self.assertEqual(possibles, [])
        events, possibles = generic_events.extract(html, "https://municipal.cl/", MUNICIPAL, CHILE, REF)
        self.assertEqual(events, [])
        self.assertTrue(possibles)


class RealCrawlRegressionTests(unittest.TestCase):
    """Casos mal publicados en el primer rastreo real (2026-10-24 15:02 UTC)."""

    def extract(self, html, url, source):
        return event_page.event_from_page(html, url, source, CHILE, REF)

    def test_municipal_news_slugs_are_not_events(self):
        coronel = dict(MUNI, name="Municipalidad de Coronel", url="https://www.coronel.cl/", commune="Coronel")
        cases = [
            (MUNI, "https://municanete.cl/v2/conoce-los-seleccionados-feria-todos-los-santos-2026/",
             "CONOCE LOS SELECCIONADOS FERIA TODOS LOS SANTOS 2026", "Del 26 al 31 de octubre, 13:00 hrs"),
            (MUNI, "https://municanete.cl/v2/municipalidad-de-canete-abre-postulaciones-para-la-feria/",
             "Municipalidad de Cañete abre postulaciones para la Feria", "31 de octubre"),
            (coronel, "https://www.coronel.cl/noticias/inauguran-feria-de-emprendedores/",
             "Inauguran Feria de Emprendedores de Coronel", "3 de noviembre"),
        ]
        for source, url, title, when in cases:
            self.assertIsNone(self.extract(page(title, when), url, source), url)

    def test_administrative_titles_are_not_events(self):
        nacimiento = dict(MUNI, name="Municipalidad de Nacimiento", url="https://nacimiento.cl/",
                          commune="Nacimiento")
        for title in ("CALENDARIO DE TALLERES DEPORTIVOS Y RECREATIVOS 2026", "Beneficios y fondos Concursables"):
            self.assertIsNone(self.extract(page(title, "30 de noviembre de 2026"),
                                           "https://nacimiento.cl/actividades/x-id-1", nacimiento), title)
        ev = self.extract(page("Taller de Calistenia", "25 de noviembre de 2026"),
                          "https://nacimiento.cl/actividades/taller-de-calistenia-id-165377", nacimiento)
        self.assertEqual(ev["title"], "Taller de Calistenia")
        title = "Seremi de las Culturas selecciona candidatos para los Premios Regionales"
        self.assertIsNone(self.extract(page(title, "19 de noviembre, Antofagasta"),
                                       "https://www.cultura.gob.cl/agendacultural/seremi/", MINISTERIO))

    def test_category_page_with_child_links_is_a_listing(self):
        m100 = dict(MUNICIPAL, name="Matucana 100", url="https://www.m100.cl/", commune="Estación Central")
        links = "".join(f'<a href="/programacion/artes-visuales/obra-{i}/">Obra {i}</a>' for i in range(4))
        html = page("Artes Visuales", "27/10/26 al 24/01/27").replace("</body>", links + "</body>")
        self.assertIsNone(self.extract(html, "https://www.m100.cl/programacion/artes-visuales/", m100))
        detail = page("Odisea del Espacio: 25 años de Matucana 100", "27/10/26 al 24/01/27")
        url = "https://www.m100.cl/programacion/artes-visuales/odisea-del-espacio-25-anos/"
        self.assertEqual(self.extract(detail, url, m100)["date"], "2026-10-27")

    def test_end_date_ignores_far_away_dates(self):
        html = page("Noche de grandes coreógrafos", "Martes 27 de octubre – 19:00 horas",
                    "Jueves 29 de octubre – 19:00 horas", "Próxima temporada: 20 de enero de 2027")
        ev = self.extract(html, "https://municipal.cl/espectaculos/noche-de-grandes-coreografos-2026/", MUNICIPAL)
        self.assertEqual((ev["date"], ev["end_date"]), ("2026-10-27", "2026-10-29"))

    def test_region_names_are_not_communes(self):
        url = "https://www.cultura.gob.cl/agendacultural/dia-del-patrimonio-magallanes/"
        html = page("Día del Patrimonio Cultural Regional", "25 de octubre, Región de Magallanes y de la Antártica Chilena")
        self.assertIsNone(self.extract(html, url, MINISTERIO))
        html = page("Gira de BAFONA", "28 de octubre en La Unión, Región de Los Ríos")
        self.assertEqual(self.extract(html, url, MINISTERIO)["commune"], "La Unión")


if __name__ == "__main__":
    unittest.main()
