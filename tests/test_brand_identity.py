"""Logo, favicon e íconos coherentes (mejora 5 pedida por el usuario, 2026-10-25)."""
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
BRAND = ("#282C30", "#F7F6F2", "#C04C3E")  # grafito, papel y coral editorial


def png_size(path):
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


class BrandIdentityTests(unittest.TestCase):
    def test_svg_symbols_share_brand_colors(self):
        for name in ("favicon.svg", "logo-simbolo.svg", "logo-horizontal.svg"):
            svg = (STATIC / name).read_text(encoding="utf-8")
            for color in BRAND:
                self.assertIn(color, svg, (name, color))
        template = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn('<img class="brand-logo" src="logo-simbolo.svg?v=editorial"', template)
        self.assertNotIn('<svg class="brand-logo"', template)

    def test_png_icons_have_expected_sizes(self):
        for name, size in (("favicon-32.png", 32), ("favicon-48.png", 48), ("apple-touch-icon.png", 180),
                           ("icon-192.png", 192), ("icon-512.png", 512), ("icon-maskable-512.png", 512)):
            self.assertEqual(png_size(STATIC / name), (size, size), name)

    def test_head_links_icons_and_manifest(self):
        template = (ROOT / "template.html").read_text(encoding="utf-8")
        for marker in ('href="favicon.svg?v=editorial" type="image/svg+xml"', 'href="favicon-32.png?v=editorial" sizes="32x32"',
                       'rel="apple-touch-icon" href="apple-touch-icon.png?v=editorial"', 'rel="manifest" href="site.webmanifest"',
                       '<meta name="theme-color" content="#100F12">'):
            self.assertIn(marker, template)
        self.assertNotIn('rel="icon" href="data:', template)
        manifest = json.loads((STATIC / "site.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["theme_color"], "#100F12")
        for icon in manifest["icons"]:
            self.assertTrue((STATIC / icon["src"]).is_file(), icon["src"])
        self.assertTrue(any(i.get("purpose") == "maskable" for i in manifest["icons"]))

    def test_header_does_not_grow(self):
        template = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn(".brand-logo{width:40px;height:40px;flex:none;}", template)


if __name__ == "__main__":
    unittest.main()
