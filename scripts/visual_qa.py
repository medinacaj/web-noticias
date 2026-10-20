#!/usr/bin/env python3
"""Capturas y controles responsive de la web HTML local, sin red externa."""
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
            await page.goto(html.resolve().as_uri(), wait_until="domcontentloaded")
            await page.screenshot(path=str(output / f"home-{width}.png"), full_page=True, animations="disabled")
            overflowing = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
            if overflowing:
                offenders = await page.evaluate("""() => Array.from(document.querySelectorAll("body *"))
                    .map(el => ({tag:el.tagName, className:String(el.className).slice(0,80),
                                 right:Math.round(el.getBoundingClientRect().right),
                                 left:Math.round(el.getBoundingClientRect().left)}))
                    .filter(el => el.right > innerWidth + 2 || el.left < -2).slice(0,20)""")
                print(f"Desborde horizontal a {width}px: {offenders}", flush=True)
                raise AssertionError(f"Desborde horizontal a {width}px")
            for panel in ("preferences", "library"):
                await page.locator(f"#{panel}-toggle").click()
                await page.screenshot(path=str(output / f"{panel}-{width}.png"), full_page=False, animations="disabled")
                await page.locator(f'[data-close-panel="{panel}-panel"]').click()
            await page.locator("#preferences-toggle").click()
            await page.locator("#density-switch").click()
            await page.locator("#density-switch").click()
            await page.screenshot(path=str(output / f"headlines-{width}.png"), full_page=False, animations="disabled")
            await page.close()
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="public/index.html")
    parser.add_argument("--output", default="artifacts/visual-qa")
    args = parser.parse_args()
    asyncio.run(check(Path(args.html), Path(args.output)))
