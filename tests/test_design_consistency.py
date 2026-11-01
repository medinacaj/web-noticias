"""Coherencia visual: nada de colores fuera de la paleta ni secciones con estructura propia.

Lección de la Agenda (PR #87/#88): se crearon un color, etiquetas y tarjetas propias y la
sección se veía ajena al resto del portal. Ver la regla de coherencia en CLAUDE.md.
"""
import os
import re
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_noticias as news
from scripts.agenda import upcoming_events

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)

# Paleta aprobada (tokens de :root, modo oscuro y tintes ya existentes al 2026-10-24).
# Agregar un color aquí requiere la aprobación del usuario.
PALETTE = {
    "#000", "#061424", "#07192E", "#0A2540", "#182639", "#1F5F8B", "#2E6B4F", "#346E99", "#388450",
    "#39766C", "#3C5067", "#5B3F9E", "#6D7480", "#74D0A4", "#7CC0EE", "#83C4B5", "#8BDC9D", "#8DA4BA",
    "#90C6E4", "#9C2F6F", "#A35334", "#A8BCD0", "#B1C3D4", "#B39AF5", "#B4530A", "#B7C9DA", "#B9C0C8",
    "#C1CFDE", "#C5CFDA", "#C5E1FF", "#C8102E", "#C8D4DF", "#CAD5E0", "#D7E8F8", "#DCE6EF", "#EE8BC6",
    "#EEF2F6", "#EFA98C", "#F0F4F8", "#F5A35C", "#FF6B7D", "#FFE0A4", "#FFF", "#FFF0AE", "#FFFFFF",
    # Revisión de paleta pedida por el usuario: neutros, coral y verde (2026-10-24).
    "#E9E8E2", "#F2F1ED", "#FAFAF7", "#282C30", "#626970", "#D7DBD4", "#343A43", "#31584A", "#C04C3E",
    "#272D31", "#202529", "#F7F6F2", "#CED1D6", "#E7EDE6", "#526257", "#9EAEA1", "#C4C7CC",
    "#151719", "#111315", "#1C1F23", "#4C545E", "#CCD1D6", "#66717D", "#B4DCC8", "#FF907F",
    "#94B9E4", "#93CDB5", "#C7B2E8", "#F2BE86", "#E7ACD1", "#E6C773", "#27362F", "#DEEDDE",
    "#BED0C4", "#789087",
    # Referencia Rootly adjunta y adaptación legible solicitadas por el usuario (2026-10-29).
    "#F3F1F8", "#FBFAFF", "#100F12", "#65646E", "#DDD7E9", "#44434E", "#4A3E8A",
    "#EBE5FF", "#D9CFFA", "#D0CCD9", "#121116", "#1B1921", "#554D64", "#6A607C",
    "#30283F", "#F0EBFF", "#8D6FDE", "#383441",
    # Editorial Mineral, seleccionado por el usuario el 2026-11-01 tras auditoría #193.
    "#252C2C", "#637070", "#285D63", "#DDEBEA", "#D5D9D5",
    "#14191B", "#1B2224", "#F1F4F2", "#BCC5C5", "#9ED0CC",
    "#283B3D", "#404A4C",
    # Color propio de la Agenda (dorado), pedido por el usuario el 2026-10-24.
    "#8A6100", "#F2C14E",
    # Cabecera y controles con más color, solicitados por el usuario el 2026-10-28.
    "#F3D5CD", "#E9DDEA", "#D9E8E1", "#BDAFB8", "#8A5D18", "#24675C",
    "#6845A4", "#A33E62", "#594763", "#312931", "#302F45", "#243C35",
    "#776779", "#E8BC78", "#98D6C1", "#CBB4F2", "#EBAAC5", "#CDC0E0",
}
# Secciones que no son categorías de noticias pero tienen color propio aprobado.
EXTRA_SECTIONS = {"agenda", "cine-streaming"}


def template_css():
    page = (ROOT / "template.html").read_text(encoding="utf-8")
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", page, re.S))


class PaletteTests(unittest.TestCase):
    def test_no_colors_outside_the_palette(self):
        used = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{3,8}\b", template_css())}
        self.assertEqual(sorted(used - PALETTE), [],
                         "Color nuevo en template.html: usa un token existente o pide aprobación")

    def test_category_classes_match_real_categories(self):
        keys = {c["key"] for c in news.CATEGORIES} | EXTRA_SECTIONS
        defined = set(re.findall(r"^\s*\.cat-([a-z-]+)\{", template_css(), re.M))
        self.assertEqual(sorted(defined - keys), [],
                         "Clase .cat-* sin categoría real: reutiliza el color de una categoría existente")


class SectionStructureTests(unittest.TestCase):
    def test_every_section_shares_the_news_structure(self):
        stories = [{"category": cat, "title": f"Nota {i} de {cat}", "summary": "", "image": "",
                    "sources": [f"Medio {i}"], "link": f"https://medio{i}.cl/nota",
                    "published": f"2026-10-24T{10 - i % 5:02d}:00:00Z"}
                   for i, cat in enumerate(["nacional", "deportes", "cultura"] * 4)]
        agenda = upcoming_events({"events": [
            {"title": "Concierto", "date": "2026-10-30", "time": "19:00", "commune": "Talca",
             "region": "Maule", "category": "Cultura", "price_status": "free",
             "source": "Teatro Regional del Maule", "source_url": "https://www.teatroregional.cl/e/1"},
        ]}, date(2026, 10, 24))
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            news.build_site(stories, NOW, folder, agenda=agenda)
            page = Path(folder, "index.html").read_text(encoding="utf-8")
        sections = re.findall(r'<section class="section[^"]*" id="cat-[^"]+".*?</section>', page, re.S)
        self.assertGreaterEqual(len(sections), 2)
        self.assertTrue(any('id="cat-agenda"' in s for s in sections))
        for number, section in enumerate(sections, start=1):
            name = re.search(r'id="(cat-[^"]+)"', section).group(1)
            self.assertIn(f'<span class="section-num">{number:02d}</span>', section, name)
            self.assertRegex(section, r'<h2 id="titulo-[^"]+">', name)
            self.assertIn('<span class="section-count"', section, name)
            self.assertIn('class="section-grid', section, name)
            self.assertRegex(section, r'<article class="(feature|compact)">', name)
            self.assertIn('<p class="kicker">', section, name)
            self.assertIn('<p class="meta">', section, name)


if __name__ == "__main__":
    unittest.main()
