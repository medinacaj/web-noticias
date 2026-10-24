#!/usr/bin/env python3
"""Capturas y controles de funcionamiento responsive de la web local."""
import argparse
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

WIDTHS = (320, 375, 768, 1024, 1440, 1920, 2560)


async def check_view_options_bounds(page, width):
    """A popover can be clipped on the left without increasing scrollWidth."""
    bounds = await page.locator("#view-options-panel").bounding_box()
    assert bounds is not None, f"Opciones de vista ocultas a {width}px"
    assert bounds["x"] >= -1 and bounds["x"] + bounds["width"] <= width + 1, (
        f"Opciones de vista fuera de pantalla a {width}px: {bounds}")


async def check_search(page, width, no_overflow):
    """Exercise the shipped index and filters using only stories in the page."""
    stories = await page.locator("main a[data-cat]").evaluate_all("""links => {
        const seen = new Set();
        return links.filter(link => {
            if (seen.has(link.href)) return false;
            seen.add(link.href);
            return true;
        }).map(link => ({
            href: link.href,
            category: link.getAttribute("data-key"),
            label: link.getAttribute("data-cat"),
            sources: JSON.parse(link.getAttribute("data-sources") || "[]"),
            key: (link.textContent + " " + (link.getAttribute("data-countries") || ""))
                .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase()
        }));
    }""")
    assert stories, f"No hay noticias indexables a {width}px"
    assert all(isinstance(story["sources"], list) and story["sources"]
               and all(isinstance(name, str) and name.strip() for name in story["sources"])
               for story in stories), f"Fuentes individuales incompletas a {width}px"
    for story in stories:
        story["sources"] = list(dict.fromkeys(name.strip() for name in story["sources"]))

    toggle = page.locator("#search-toggle")
    panel = page.locator("#search-panel")
    field = page.locator("#search-input")
    source_filter = page.locator("#search-source")
    category_filter = page.locator("#search-category")
    await toggle.click()
    assert await panel.is_visible(), f"Buscador oculto a {width}px"
    assert await toggle.get_attribute("aria-expanded") == "true"

    async def verify(expected, stage):
        actual = await page.locator("#search-results li > a").evaluate_all(
            "links => links.map(link => link.href)")
        expected_urls = [story["href"] for story in expected]
        assert actual == expected_urls, (
            f"Resultados de {stage} a {width}px: {len(actual)} visibles, "
            f"{len(expected_urls)} esperados; faltantes={set(expected_urls) - set(actual)}")
        status = "1 resultado" if len(expected) == 1 else f"{len(expected)} resultados"
        assert await page.locator("#search-status").inner_text() == status, (
            f"Conteo anunciado incorrecto en {stage} a {width}px")
        await no_overflow(f"buscador: {stage}")

    # Cover an individual outlet that participates in combined coverage when available.
    sources = {name for story in stories for name in story["sources"]}
    options = await source_filter.locator("option").evaluate_all("nodes => nodes.map(node => node.value)")
    assert sources <= set(options), f"Faltan medios individuales en el buscador a {width}px"
    counts = {name: sum(name in story["sources"] for story in stories) for name in sources}
    combined = {name for story in stories if len(story["sources"]) > 1 for name in story["sources"]}
    most_common = max(sorted(sources), key=counts.get)
    individual = max(sorted(combined or sources), key=counts.get)
    for name in dict.fromkeys((individual, most_common)):
        await source_filter.select_option(name)
        await verify([story for story in stories if name in story["sources"]], f"medio {name}")
    await source_filter.select_option("")

    # Keep original categories testable even when their cards share a larger visual group.
    categories = {story["category"]: story["label"] for story in stories}
    category_options = await category_filter.locator("option").evaluate_all(
        "nodes => nodes.map(node => node.value)")
    assert set(categories) <= set(category_options), f"Faltan categorías originales a {width}px"
    category_counts = {key: sum(story["category"] == key for story in stories) for key in categories}
    largest_category = max(sorted(categories), key=category_counts.get)
    originals = [key for key, label in categories.items()
                 if key.lower() in ("salud", "ciencia", "salud-ciencia", "medioambiente", "latinoamerica") or label.lower() in ("salud", "ciencia")]
    for key in dict.fromkeys((*originals, largest_category)):
        await category_filter.select_option(key)
        await verify([story for story in stories if story["category"] == key], f"categoría {key}")
    print(f"Filtros comprobados a {width}px: {', '.join(dict.fromkeys((*originals, largest_category)))}")
    await category_filter.select_option("")

    # A real text query reaches beyond twenty whenever the published headlines allow it.
    # The most frequent character is the widest possible nonempty substring query.
    characters = {char for story in stories for char in story["key"] if char.isalnum()}
    if characters:
        query = max(sorted(characters), key=lambda char: sum(char in story["key"] for story in stories))
        await field.fill(query)
        await verify([story for story in stories if query in story["key"]], f"texto {query!r}")
    await field.fill("")
    await page.keyboard.press("Escape")
    assert not await panel.is_visible(), f"Buscador abierto tras Escape a {width}px"
    assert await toggle.get_attribute("aria-expanded") == "false"
    assert await toggle.evaluate("element => element === document.activeElement"), (
        f"El buscador no devuelve el foco a {width}px")


async def check_shared_alignment(page, width):
    """Todas las bandas utilizan las mismas guías de contenido."""
    boxes = await page.evaluate("""() => ['.bar-inner','.breaking-inner','main.container',
        '.newsletter-invite-inner','.site-footer > .container'].map(selector => {
          const el=document.querySelector(selector), r=el.getBoundingClientRect(), css=getComputedStyle(el);
          return {selector, left:r.x+parseFloat(css.paddingLeft), right:r.right-parseFloat(css.paddingRight), width:r.width};
        })""")
    main = boxes[2]
    assert all(abs(box['left']-main['left']) <= 1 and abs(box['right']-main['right']) <= 1
               for box in boxes), f"Guías desalineadas a {width}px: {boxes}"
    if width >= 1920:
        assert main['width'] >= 1400, f"Contenido estrecho a {width}px: {main}"
    header = await page.locator('.site-header').bounding_box()
    assert header['height'] <= (80 if width < 1024 else 68), f"Cabecera alta a {width}px: {header}"
    aligned_cards = await page.evaluate("""() => {
      const rail=document.querySelector('.rail-list'), grid=document.querySelector('.section-grid');
      if (!rail || !grid || getComputedStyle(rail).gridTemplateColumns.split(' ').length !== 3 ||
          getComputedStyle(grid).gridTemplateColumns.split(' ').length !== 3) return true;
      const first=Array.from(rail.querySelectorAll('li')).slice(0,3);
      const second=Array.from(grid.querySelectorAll('.feature,.compact-list > li')).slice(0,3);
      return first.length === second.length && first.every((el,index) => {
        const a=el.getBoundingClientRect(),b=second[index].getBoundingClientRect();
        return Math.abs(a.x-b.x)<=1 && Math.abs(a.right-b.right)<=1;
      });
    }""")
    assert aligned_cards, f"Columnas de Destacadas y secciones desalineadas a {width}px"


async def check_compact_navigation(page, width, no_overflow):
    """Regresiones del diseño publicado: franja compacta y chevrón lateral."""
    latest = await page.locator(".breaking").bounding_box()
    assert latest and latest["height"] <= 60, f"Lo último deja de ser una franja a {width}px: {latest}"
    await check_shared_alignment(page, width)
    edge = page.locator("#sidebar-edge")
    nav = page.locator("#site-nav")
    assert await edge.count() == 1, "Falta el chevrón lateral"
    if width >= 1024:
        assert await edge.is_visible() and await nav.is_visible()
        await edge.click()
        assert not await nav.is_visible() and await edge.is_visible()
        assert await edge.get_attribute("aria-expanded") == "false"
        await check_shared_alignment(page, width)
        await edge.click()
        assert await nav.is_visible()
    else:
        assert not await edge.is_visible()
        await page.locator("#menu-toggle").click()
        assert await edge.is_visible() and await nav.is_visible()
        await edge.click()
        assert not await nav.is_visible()
        assert not await page.locator("#nav-backdrop").is_visible()
    await check_shared_alignment(page, width)
    await no_overflow("chevrón lateral")


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
            await check_compact_navigation(page, width, no_overflow)
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
            await check_search(page, width, no_overflow)
            await page.locator("#view-options-toggle").click()
            assert await page.locator("#view-options-panel").is_visible(), f"Menú visual oculto a {width}px"
            await check_view_options_bounds(page, width)
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
            assert links == ["#contenido", "#categorias", "boletin-diario.html", "rss.xml", "sobre-el-portal.html"], (
                f"Enlaces de pie no válidos a {width}px: {links}")
            assert await page.locator("#categorias").count() == 1
            assert await page.locator(".header-updated").is_visible()
            assert await page.locator(".edition-count").is_visible()
            assert await footer.locator(".footer-updated,.edition-details").count() == 0
            assert (await footer.bounding_box())["height"] <= (140 if width >= 1024 else 280)
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

