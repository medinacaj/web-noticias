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
            await page.locator("#library-toggle").click()
            assert await page.locator("#library-panel").is_visible(), f"Favoritos ocultos a {width}px"
            await no_overflow("guardadas")
            await page.screenshot(path=str(output / f"saved-{width}.png"), full_page=False, animations="disabled")
            await page.locator('[data-close-panel="library-panel"]').click()
            if errors:
                raise AssertionError(f"Errores JavaScript a {width}px: {errors}")
            await page.close()
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="public/index.html")
    parser.add_argument("--output", default="artifacts/visual-qa")
    args = parser.parse_args()
    asyncio.run(check(Path(args.html), Path(args.output)))
