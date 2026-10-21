#!/usr/bin/env python3
"""Capturas y controles de funcionamiento responsive de la web local."""
import argparse
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

WIDTHS = (320, 375, 768, 1024, 1440)


async def check(html, output):
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for width in WIDTHS:
            page = await browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(html.resolve().as_uri(), wait_until="domcontentloaded")
            async def no_overflow(stage):
                overflowing = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
                if overflowing:
                    offenders = await page.evaluate("""() => Array.from(document.querySelectorAll('body *'))
                        .map(el => ({tag:el.tagName, cls:String(el.className).slice(0,80),
                                     right:Math.round(el.getBoundingClientRect().right)}))
                        .filter(el => el.right > innerWidth + 2).slice(0,10)""")
                    raise AssertionError(f"Desborde horizontal a {width}px en {stage}: {offenders}")
            await no_overflow("portada")
            # Ninguna miniatura debe dejar un bloque vacío por debajo del texto.
            gaps = await page.evaluate("""() => Array.from(document.querySelectorAll(
                ".section-grid .feature, .section-grid .compact"))
                .filter(card => card.getClientRects().length)
                .map(card => {
                    const image = card.querySelector(".media");
                    const body = card.querySelector(".news-body");
                    if (!image || !body || getComputedStyle(image).display === "none") return null;
                    return {gap: Math.round(body.getBoundingClientRect().height -
                                            image.getBoundingClientRect().height),
                            photo: Math.round(image.getBoundingClientRect().height),
                            body: Math.round(body.getBoundingClientRect().height)};
                }).filter(Boolean).slice(0, 12)""")
            assert gaps, f"No se encontraron miniaturas para comprobar a {width}px"
            assert all(item["gap"] <= 4 for item in gaps), (
                f"Miniaturas sin ocupar la altura disponible a {width}px: {gaps}")
            await page.screenshot(path=str(output / f"home-{width}.png"), full_page=True, animations="disabled")
            await page.locator("#view-options-toggle").click()
            assert await page.locator("#view-options-panel").is_visible(), f"Menú visual oculto a {width}px"
            await no_overflow("preferencias")
            await page.screenshot(path=str(output / f"preferences-{width}.png"), full_page=False, animations="disabled")
            await page.locator("#density-switch").click()
            await page.locator("#density-switch").click()
            assert await page.locator("#contenido").evaluate("(el) => el.classList.contains('is-headlines')"), f"Vista titulares inactiva a {width}px"
            await page.screenshot(path=str(output / f"headlines-{width}.png"), full_page=False, animations="disabled")
            await page.locator("#view-options-toggle").click()
            # Validar botones reales en una tarjeta, no solo el panel de favoritos.
            favorite = page.locator(".save-story:visible").first
            share = page.locator(".share-story:visible").first
            assert await favorite.count() and await share.count(), f"Faltan acciones en tarjetas a {width}px"
            await favorite.click()
            assert await favorite.get_attribute("aria-pressed") == "true", f"No se guardó favorito a {width}px"
            await no_overflow("acciones de tarjeta")
            await page.locator("#library-toggle").click()
            assert await page.locator("#library-panel").is_visible(), f"Favoritos ocultos a {width}px"
            assert await page.locator("#saved-stories a").count() >= 1, f"Biblioteca no sincronizada a {width}px"
            await no_overflow("guardadas")
            await page.screenshot(path=str(output / f"saved-{width}.png"), full_page=False, animations="disabled")
            await page.locator('[data-close-panel="library-panel"]').click()
            footer = page.locator(".site-footer")
            await footer.scroll_into_view_if_needed()
            links = await page.locator(".site-footer .footer-nav a").evaluate_all(
                "(nodes) => nodes.map(a => a.getAttribute('href'))")
            assert links == ["#contenido", "#categorias", "boletin-diario.html", "rss.xml"], (
                f"Enlaces de pie no válidos a {width}px: {links}")
            assert await page.locator("#categorias").count() == 1
            assert await page.locator(".footer-updated").is_visible()
            await no_overflow("pie de página")
            await page.screenshot(path=str(output / f"footer-{width}.png"), full_page=False, animations="disabled")
            await page.locator('.site-footer a[href="#categorias"]').click()
            assert await page.evaluate("window.location.hash") == "#categorias", (
                f"Enlace a categorías falló a {width}px")
            if errors:
                raise AssertionError(f"Errores JavaScript a {width}px: {errors}")
            await page.close()
            # Página SEO permanente: diseño accesible y sin desbordamiento responsive.
            about_file = html.resolve().parent / "sobre-el-portal.html"
            about = await browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
            await about.goto(about_file.as_uri(), wait_until="domcontentloaded")
            assert await about.locator("h1").count() == 1, f"Falta H1 único en Sobre a {width}px"
            assert await about.locator('link[rel="canonical"]').count() == 1
            about_overflows = await about.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
            assert not about_overflows, f"Desborde horizontal en Sobre a {width}px"
            await about.screenshot(path=str(output / f"about-{width}.png"), full_page=True, animations="disabled")
            await about.close()
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="public/index.html")
    parser.add_argument("--output", default="artifacts/visual-qa")
    args = parser.parse_args()
    asyncio.run(check(Path(args.html), Path(args.output)))
