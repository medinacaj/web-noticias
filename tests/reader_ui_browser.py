"""Checks against the real generated document and Chromium; run explicitly."""
import asyncio
import json
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from pathlib import Path
import unittest
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/tmp/web-noticias-ux-captures')


class ReaderBrowserTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "public")))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    async def asyncSetUp(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        self.context = await self.browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme='light', reduced_motion='reduce')
        # Third-party image/font availability is not a prerequisite for interaction tests.
        await self.context.route('https://**/*', lambda route: route.abort())
        self.page = await self.context.new_page()
        self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        await self.page.goto(self.url)

    async def asyncTearDown(self):
        await self.context.close()
        await self.browser.close()
        await self.pw.stop()
        self.assertEqual(self.errors, [])

    async def test_reading_hierarchy_and_control_labels(self):
        self.assertTrue(await self.page.locator('#search-toggle .control-label').is_visible())
        self.assertTrue(await self.page.locator('#view-options-toggle .control-label').is_visible())
        desktop_gap = await self.page.locator('.section').first.evaluate('el => parseFloat(getComputedStyle(el).marginTop)')
        self.assertLessEqual(desktop_gap, 48)
        await self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertFalse(await self.page.locator('#search-toggle .control-label').is_visible())
        lead_size = await self.page.locator('.lead-title').evaluate('el => parseFloat(getComputedStyle(el).fontSize)')
        self.assertLessEqual(lead_size, 34)
        await self.page.locator('#search-toggle').click()
        self.assertTrue(await self.page.locator('#search-input').is_visible())

    async def test_latam_visuals_are_visible_and_respect_reader_density(self):
        figures = self.page.locator('.cat-latinoamerica .media--region')
        self.assertGreater(await figures.count(), 0)
        for width in (320, 390, 768, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            self.assertTrue(await figures.first.is_visible(), width)
            self.assertTrue(await figures.first.locator('.region-label').is_visible(), width)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
        # Las miniaturas también deben poder ocultarse al elegir una vista densa.
        await self.page.locator('#contenido').evaluate("el => el.classList.add('is-compact')")
        self.assertFalse(await figures.first.is_visible())
        await self.page.locator('#contenido').evaluate("el => {el.classList.remove('is-compact'); el.classList.add('is-headlines')}")
        self.assertFalse(await figures.first.is_visible())

    async def load_latam_lead_fixture(self):
        import sys, tempfile
        from datetime import datetime, timezone
        sys.path.insert(0, str(ROOT))
        import fetch_noticias as news
        now = datetime(2026, 10, 26, 2, tzinfo=timezone.utc)
        stories = [{"category": "latinoamerica", "title": f"Brasil y México cooperan {i}",
                    "link": f"https://medio{i}.example/nota", "source_url": f"https://medio{i}.example",
                    "sources": [f"Medio {i}"], "image": "", "summary": "", "metadata_only": True,
                    "coverage_countries": ["BR", "MX"], "published": now.isoformat()}
                   for i in range(12)]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, now, folder)
            body = Path(folder, 'index.html').read_text()
        await self.page.route('**/?latam-visual=1', lambda route: route.fulfill(status=200, content_type='text/html', body=body))
        await self.page.goto(self.url + '?latam-visual=1')

    async def test_latam_lead_respects_dense_views(self):
        await self.load_latam_lead_fixture()
        figure = self.page.locator('.lead .media--region')
        self.assertTrue(await figure.is_visible())
        for density in ('is-compact', 'is-headlines'):
            await self.page.locator('#contenido').evaluate('(el, density) => el.className=density', density)
            self.assertFalse(await figure.is_visible(), density)

    async def test_latam_rail_countries_and_mark_fit_inside_thumbnail(self):
        await self.load_latam_lead_fixture()
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            figure = self.page.locator('.rail-item .media--region').first
            bounds = await figure.bounding_box()
            for selector in ('.source-mark', '.region-label'):
                box = await figure.locator(selector).bounding_box()
                self.assertGreaterEqual(box['y'], bounds['y'], (width, selector))
                self.assertLessEqual(box['y'] + box['height'], bounds['y'] + bounds['height'], (width, selector))
    async def prime_previous_edition(self):
        await self.page.evaluate("""() => {
          const edition = Date.parse(document.querySelector('#updated-at').dateTime);
          localStorage.setItem('noticias:last-edition:v1:' + location.pathname, String(edition - 25 * 3600000));
        }""")
        await self.page.reload()

    async def test_visit_updates_are_quiet_first_time_and_not_repeated_on_reload(self):
        self.assertFalse(await self.page.locator('#visit-updates').is_visible())
        await self.prime_previous_edition()
        button = self.page.locator('#visit-updates')
        self.assertTrue(await button.is_visible())
        self.assertGreater(await self.page.locator('.new-story-label').count(), 0)
        await button.click()
        self.assertTrue(await self.page.evaluate("document.activeElement.matches('a[data-first-seen]')"))
        await self.page.reload()
        self.assertFalse(await button.is_visible())
        self.assertEqual(await self.page.locator('.new-story-label').count(), 0)

    async def test_visit_updates_respect_filters_and_reset_preserves_order(self):
        await self.prime_previous_edition()
        total = await self.page.locator('#visit-updates').text_content()
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#source-sort').select_option('recent')
        category = self.page.locator('#category-preference')
        await category.select_option(index=1)
        self.assertTrue(await self.page.locator('#preferences-reset').is_visible())
        expected = await self.page.evaluate("""() => [...document.querySelectorAll('.new-story-label')]
            .filter(el => !el.closest('[data-source-hidden],[data-filtered],[hidden]')).length""")
        self.assertEqual(await self.page.locator('#visit-updates').is_visible(), expected > 0)
        if expected:
            self.assertTrue((await self.page.locator('#visit-updates').text_content()).startswith(str(expected) + ' '))
        await self.page.locator('#preferences-reset').click()
        self.assertEqual(await category.input_value(), '')
        self.assertEqual(await self.page.locator('#source-sort').input_value(), 'recent')
        self.assertEqual(await self.page.locator('#visit-updates').text_content(), total)
        await self.page.locator('#view-options-toggle').click()
        for width in (320, 390, 768, 1024, 1440, 1920, 2560):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
        await self.page.set_viewport_size({'width': 390, 'height': 1000})
        await self.page.screenshot(path='/tmp/news-discovery-return-390.png')
        await self.page.set_viewport_size({'width': 1440, 'height': 1000})
        await self.page.screenshot(path='/tmp/news-discovery-return-1440.png')

    async def test_visit_updates_ignore_corrupt_and_newer_watermarks(self):
        for value in ('broken', '-1', 'Infinity', '99999999999999'):
            await self.page.evaluate("v => localStorage.setItem('noticias:last-edition:v1:' + location.pathname, v)", value)
            await self.page.reload()
            self.assertFalse(await self.page.locator('#visit-updates').is_visible(), value)
        await self.page.evaluate("""() => {
          const newer = Date.parse(document.querySelector('#updated-at').dateTime) + 60000;
          localStorage.setItem('noticias:last-edition:v1:' + location.pathname, String(newer));
        }""")
        before = await self.page.evaluate("localStorage.getItem('noticias:last-edition:v1:' + location.pathname)")
        await self.page.reload()
        self.assertFalse(await self.page.locator('#visit-updates').is_visible())
        self.assertEqual(await self.page.evaluate("localStorage.getItem('noticias:last-edition:v1:' + location.pathname)"), before)

    async def test_article_back_navigation_preserves_scroll_and_preferences(self):
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#text-size').select_option('large')
        await self.page.locator('#view-options-toggle').click()
        link = self.page.locator('.section-grid h3 a').first
        await link.scroll_into_view_if_needed()
        before = await self.page.evaluate('scrollY')
        destination = await link.get_attribute('href')
        await self.page.route(destination, lambda route: route.fulfill(status=200, content_type='text/html', body='<h1>Artículo original</h1>'))
        await link.click()
        await self.page.wait_for_url(destination)
        self.assertEqual(len(self.context.pages), 1)
        await self.page.go_back()
        self.assertEqual(await self.page.locator('#text-size').input_value(), 'large')
        await self.page.wait_for_function('Math.abs(scrollY - ' + str(before) + ') < 40')

    async def test_back_restores_expanded_news_and_position(self):
        more = self.page.locator('[data-show-more]:visible').first
        grid = self.page.locator('#' + await more.get_attribute('aria-controls'))
        link = grid.locator('[data-extra] h3 a').first
        destination = await link.get_attribute('href')
        link = grid.locator('h3 a[href=' + json.dumps(destination) + ']').first
        await more.click()
        await link.scroll_into_view_if_needed()
        before = await self.page.evaluate('scrollY')
        await self.page.route(destination, lambda route: route.fulfill(status=200, content_type='text/html', body='<h1>Artículo original</h1>'))
        await link.click()
        await self.page.wait_for_url(destination)
        await self.page.go_back()
        self.assertTrue(await link.is_visible())
        await self.page.wait_for_function('Math.abs(scrollY - ' + str(before) + ') < 40')

    async def test_back_restores_search_and_results(self):
        await self.page.locator('#search-toggle').click()
        await self.page.locator('#search-category').select_option('cultura')
        before = await self.page.locator('#search-results li').count()
        self.assertGreater(before, 0)
        link = self.page.locator('#search-results a').first
        destination = await link.get_attribute('href')
        await self.page.route(destination, lambda route: route.fulfill(status=200, content_type='text/html', body='<h1>Artículo original</h1>'))
        await link.click()
        await self.page.wait_for_url(destination)
        await self.page.go_back()
        self.assertTrue(await self.page.locator('#search-panel').is_visible())
        self.assertEqual(await self.page.locator('#search-category').input_value(), 'cultura')
        self.assertEqual(await self.page.locator('#search-results li').count(), before)

    async def test_mobile_theme_control_is_visible_and_works(self):
        for width in (320, 360, 375, 390, 479):
            await self.page.set_viewport_size({'width': width, 'height': 844})
            toggle = self.page.locator('#theme-toggle')
            self.assertTrue(await toggle.is_visible(), width)
            self.assertTrue(await toggle.evaluate('el => {const r=el.getBoundingClientRect(); return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}'), width)
            self.assertLessEqual((await self.page.locator('.site-header').bounding_box())['height'], 80)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
        await self.page.locator('#theme-toggle').click()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.locator('#theme-toggle').click()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')

    async def test_menu_covers_all_published_categories_and_real_targets(self):
        missing = await self.page.evaluate("""() => {
          const categories = new Set([...document.querySelectorAll('main h2 a[data-key],main h3 a[data-key]')].map(a=>a.dataset.key));
          // Salud se publica dentro de Ciencia y tecnología, sin entrada propia en el menú.
          return [...categories].filter(key=>key!=='salud-ciencia'&&!document.querySelector('#site-nav a[href="#cat-'+key+'"]'));
        }""")
        self.assertEqual(missing, [])
        self.assertTrue(await self.page.evaluate("""() => [...document.querySelectorAll('#site-nav a')]
          .every(a=>document.getElementById(a.hash.slice(1)))"""))
        self.assertEqual(await self.page.locator('#site-nav a[href="#cat-medioambiente"]').inner_text(), 'Medioambiente')
        self.assertEqual(await self.page.locator('#site-nav a[href="#cat-salud-ciencia"]').count(), 0)
        self.assertEqual(await self.page.locator('#site-nav a[href="#cat-tecnologia"]').inner_text(), 'Ciencia y tecnología')

    async def test_grouped_menu_topics_reveal_and_highlight_their_news(self):
        for width in (1440, 390):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            await self.page.reload()
            for category in ('medioambiente', 'tecnologia'):
                if width < 1024:
                    await self.page.locator('#menu-toggle').click()
                link = self.page.locator('#site-nav a[href="#cat-' + category + '"]')
                await link.click()
                target = self.page.locator('#cat-' + category)
                self.assertTrue(await target.is_visible(), (width, category))
                self.assertTrue(await target.locator('a[data-key="' + category + '"]').count())
                await self.page.wait_for_function("document.querySelector('#site-nav a[href=\"#cat-" + category + "\"]').getAttribute('aria-current') === 'location'")
                if width < 1024:
                    self.assertFalse(await self.page.locator('#site-nav').is_visible())
        await self.page.set_viewport_size({'width': 1440, 'height': 1000})
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#site-nav a[href="#cat-medioambiente"]').click()
        self.assertTrue(await self.page.locator('#cat-medioambiente').is_visible())
        self.assertEqual(await self.page.locator('#category-preference').input_value(), '')
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#site-nav a[href="#cat-nacional"]').click()
        self.assertTrue(await self.page.locator('#cat-nacional .feature').is_visible())
        self.assertEqual(await self.page.locator('#category-preference').input_value(), '')

    async def test_grouped_category_hash_works_on_direct_load_and_reload(self):
        # Salud conserva su ancla (enlaces ya compartidos) aunque no tenga entrada en el menú.
        for category in ('tecnologia', 'salud-ciencia'):
            if not await self.page.locator('#cat-' + category).count():
                continue  # Una edición real puede no publicar este tema; el caso Salud se prueba con fixture propio.
            await self.page.goto(self.url + '?category-entry=1#cat-' + category)
            target = self.page.locator('#cat-' + category)
            await target.wait_for(state='visible', timeout=2000)
            await self.page.wait_for_function("document.querySelector('#cat-" + category + "').getBoundingClientRect().top > 0 && document.querySelector('#cat-" + category + "').getBoundingClientRect().top < 180")
            await self.page.reload()
            self.assertTrue(await target.is_visible())

    async def test_back_to_topic_hash_preserves_later_category_filter(self):
        await self.page.locator('#site-nav a[href="#cat-medioambiente"]').click()
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.page.locator('#view-options-toggle').click()
        hidden = await self.page.locator('[data-source-hidden]').count()
        link = self.page.locator('.section-grid h3 a[data-key="cultura"]').first
        destination = await link.get_attribute('href')
        await self.page.route(destination, lambda route: route.fulfill(status=200, content_type='text/html', body='<h1>Noticia</h1>'))
        await link.click()
        await self.page.wait_for_url(destination)
        await self.page.go_back()
        self.assertEqual(await self.page.locator('#category-preference').input_value(), 'cultura')
        self.assertEqual(await self.page.evaluate('JSON.parse(localStorage.getItem("noticias:category:v1"))'), 'cultura')
        self.assertEqual(await self.page.locator('[data-source-hidden]').count(), hidden)

    async def test_sidebar_arrow_is_centered_on_desktop_and_mobile(self):
        for width in (320, 390, 768, 1440):
            await self.page.set_viewport_size({'width':width,'height':844})
            if width < 1024:
                await self.page.locator('#menu-toggle').click()
            bounds = await self.page.locator('#site-nav').bounding_box()
            edge = await self.page.locator('#sidebar-edge').bounding_box()
            self.assertAlmostEqual(edge['y'] + edge['height']/2, bounds['y'] + bounds['height']/2, delta=1, msg=width)
            if width < 1024:
                await self.page.locator('#menu-toggle').click()

    async def test_archive_preserves_manual_theme_and_has_no_mobile_overflow(self):
        await self.page.locator('#theme-toggle').click()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.goto(self.url + 'archivo/index.html')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        toggle = self.page.locator('#theme-toggle')
        self.assertTrue(await toggle.is_visible())
        await toggle.click()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        for width in (320,390,768,1440):
            await self.page.set_viewport_size({'width':width,'height':844})
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
            self.assertTrue(await toggle.is_visible())
        await self.page.screenshot(path='/tmp/news-pending-archive-light.png')
        await self.page.goto(self.url)
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')

    async def test_legacy_health_url_reveals_grouped_news_without_extra_menu_entry(self):
        from datetime import datetime, timezone
        import tempfile
        import fetch_noticias as news
        now = datetime(2026,10,25,15,tzinfo=timezone.utc)
        stories = [{'title':f'Nota {category} {i}', 'category':category, 'sources':[f'Medio {i}'],
                    'link':f'https://editor{i}.example/{category}', 'published':now.isoformat(), 'image':'', 'summary':''}
                   for i,category in enumerate(['tecnologia']*12 + ['salud-ciencia']*4)]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, now, folder)
            body = Path(folder,'index.html').read_text()
        await self.page.route('**/?legacy-health=1', lambda route: route.fulfill(status=200,content_type='text/html',body=body))
        await self.page.goto(self.url + '?legacy-health=1#cat-salud-ciencia')
        await self.page.locator('#cat-salud-ciencia').wait_for(state='visible', timeout=2000)
        self.assertEqual(await self.page.locator('#site-nav a[href="#cat-salud-ciencia"]').count(), 0)
        await self.page.wait_for_function("document.querySelector('#site-nav a[href=\"#cat-tecnologia\"]').getAttribute('aria-current') === 'location'")

    async def test_defaults_are_light_normal_recent_and_sections_have_no_rules(self):
        await self.page.emulate_media(color_scheme='dark')
        await self.page.reload()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        self.assertEqual(await self.page.locator('#text-size').input_value(), 'normal')
        self.assertEqual(await self.page.locator('#source-sort').input_value(), 'recent')
        for selector, edge in (('.section-head','borderBottomWidth'),('.rail-title','borderTopWidth')):
            self.assertEqual(await self.page.locator(selector).first.evaluate('(el, edge) => getComputedStyle(el)[edge]', edge), '0px')

    async def test_recent_and_editorial_sort_include_the_first_card(self):
        grid = self.page.locator('.section-grid').first
        await grid.evaluate("""grid => {
          const cards=[...grid.querySelectorAll('.feature,.compact-list li')];
          cards.forEach((card,i)=>card.dataset.originalOrder=String(i+2));
          cards[0].dataset.originalOrder='1'; cards[1].dataset.originalOrder='0';
          cards[0].querySelector('time').dateTime=new Date().toISOString();
        }""")
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#source-sort').select_option('relevance')
        self.assertFalse(await grid.locator('.feature,.compact-list li').first.evaluate("el=>el.classList.contains('feature')"))
        await self.page.locator('#source-sort').select_option('recent')
        self.assertTrue(await grid.locator('.feature,.compact-list li').first.evaluate("el=>el.classList.contains('feature')"))
        dates = await grid.evaluate("grid=>[...grid.querySelectorAll('.feature,.compact-list li')].map(el=>Date.parse(el.querySelector('time').dateTime)||0)")
        self.assertEqual(dates, sorted(dates, reverse=True))

    async def test_desktop_sidebar_defaults_visible_and_choice_survives_reload(self):
        nav, toggle = self.page.locator('#site-nav'), self.page.locator('#menu-toggle')
        self.assertTrue(await nav.is_visible())
        self.assertEqual(await toggle.get_attribute('aria-expanded'), 'true')
        await toggle.click()
        self.assertFalse(await nav.is_visible())
        await self.page.reload()
        self.assertFalse(await nav.is_visible())
        await toggle.click()
        self.assertTrue(await nav.is_visible())
        self.assertFalse(await nav.evaluate("el => el.scrollWidth > el.clientWidth + 2"))

    async def test_mobile_closes_on_escape_and_navigation_then_restores_desktop(self):
        await self.page.set_viewport_size({"width": 390, "height": 844})
        nav, toggle = self.page.locator('#site-nav'), self.page.locator('#menu-toggle')
        self.assertFalse(await nav.is_visible())
        await toggle.click()
        self.assertTrue(await nav.is_visible())
        await self.page.keyboard.press('Escape')
        self.assertFalse(await nav.is_visible())
        self.assertTrue(await toggle.evaluate('el => el === document.activeElement'))
        await toggle.click()
        await nav.locator('a').first.click()
        self.assertFalse(await nav.is_visible())
        await self.page.set_viewport_size({"width": 1440, "height": 1000})
        self.assertTrue(await nav.is_visible())

    async def test_theme_follows_system_and_manual_choice_is_retained(self):
        await self.page.emulate_media(color_scheme='dark')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#theme-select').select_option('system')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.locator('#theme-select').select_option('light')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.page.reload()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.page.locator('#view-options-toggle').click()
        await self.page.locator('#theme-select').select_option('system')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.emulate_media(color_scheme='light')
        await self.page.wait_for_function("document.documentElement.dataset.theme === 'light'")
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')

    async def test_carousel_is_clean_and_keeps_keyboard_navigation(self):
        track = self.page.locator('.breaking-track')
        self.assertGreaterEqual(await track.locator('a').count(), 3)
        self.assertEqual(await self.page.locator('[data-carousel-prev],[data-carousel-next],.carousel-controls').count(), 0)
        pause = self.page.locator('[data-carousel-pause]')
        self.assertEqual(await pause.text_content(), 'Lo último')
        self.assertEqual(await pause.evaluate('el => getComputedStyle(el).borderTopWidth'), '0px')
        await track.focus()
        await self.page.keyboard.press('ArrowRight')
        await self.page.wait_for_function("document.querySelector('.breaking-track').scrollLeft > 10")

    async def test_signature_and_typographic_fallback_across_widths(self):
        signature = self.page.locator('.designer-signature')
        self.assertEqual(await signature.get_attribute('href'), 'https://www.linkedin.com/in/medinacaj/')
        self.assertEqual(await signature.get_attribute('target'), '_blank')
        self.assertIn('noopener', await signature.get_attribute('rel'))
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
            for figure in await self.page.locator('.media--source:not(.media--date):not(.media--region)').all():
                self.assertFalse(await figure.is_visible())
        ARTIFACTS.mkdir(exist_ok=True)
        for theme in ('light', 'dark'):
            await self.page.locator('#view-options-toggle').click()
            await self.page.locator('#theme-select').select_option(theme)
            await self.page.locator('#view-options-toggle').click()
            for width in (390, 1440):
                await self.page.set_viewport_size({"width": width, "height": 1000})
                await self.page.evaluate('scrollTo(0,0)')
                await self.page.screenshot(path=str(ARTIFACTS / f'{theme}-{width}.png'))
                await signature.scroll_into_view_if_needed()
                await self.page.screenshot(path=str(ARTIFACTS / f'footer-{theme}-{width}.png'))

    async def test_header_buttons_do_not_overlap_and_text_lead_is_compact(self):
        lead = await self.page.locator('.lead').bounding_box()
        self.assertLess(lead['height'], 420)
        for width in (320, 390, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            boxes = [await item.bounding_box() for item in await self.page.locator('.bar-inner .icon-btn:visible').all()]
            boxes.sort(key=lambda box: box['x'])
            self.assertTrue(all(a['x'] + a['width'] <= b['x'] for a, b in zip(boxes, boxes[1:])), boxes)

    async def test_menu_and_search_preferences_do_not_cover_each_other(self):
        await self.page.set_viewport_size({"width": 390, "height": 844})
        await self.page.locator('#search-toggle').click()
        await self.page.locator('#menu-toggle').click()
        self.assertFalse(await self.page.locator('#search-panel').is_visible())
        await self.page.locator('#view-options-toggle').click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        self.assertTrue(await self.page.locator('#view-options-panel').is_visible())

    async def test_active_navigation_returns_to_portada(self):
        await self.page.locator('.site-footer').scroll_into_view_if_needed()
        await self.page.wait_for_timeout(100)
        await self.page.evaluate('scrollTo(0,0)')
        await self.page.wait_for_function("document.querySelector('.site-nav a[href=\"#portada\"]').getAttribute('aria-current') === 'location'", timeout=2500)

    async def test_existing_search_and_saved_stories_work_with_new_layout(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts.visual_qa import check_search, check_view_options_bounds
        async def no_overflow(stage):
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), stage)
        for width in (390, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            await check_search(self.page, width, no_overflow)
            await self.page.locator('#view-options-toggle').click()
            await check_view_options_bounds(self.page, width)
            await self.page.locator('#view-options-toggle').click()
        await self.page.locator('.save-story:visible').first.click()
        await self.page.locator('#library-toggle').click()
        self.assertGreater(await self.page.locator('#saved-stories a').count(), 0)

    async def test_without_javascript_news_and_navigation_remain_available(self):
        context = await self.browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        await context.route('https://**/*', lambda route: route.abort())
        page = await context.new_page()
        await page.goto(self.url)
        self.assertTrue(await page.locator('#site-nav').is_visible())
        self.assertGreater(await page.locator('main h2 a, main h3 a').count(), 0)
        self.assertGreaterEqual(await page.locator('.breaking-track a').count(), 3)
        self.assertFalse(await page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))
        await context.close()

    async def test_latest_is_one_compact_line_at_every_width(self):
        await self.page.locator('.breaking-track a').first.evaluate("el => el.textContent = 'Un titular muy largo sobre noticias internacionales y cultura '.repeat(12)")
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            box = await self.page.locator('.breaking').bounding_box()
            self.assertLessEqual(box['height'], 60, (width, box))
            track = self.page.locator('.breaking-track')
            self.assertEqual(await track.evaluate("el => getComputedStyle(el).scrollbarWidth"), 'none')
            first = await track.locator('li').first.bounding_box()
            self.assertAlmostEqual(first['width'], await track.evaluate('el => el.clientWidth'), delta=2)
            title = await track.locator('a').first.bounding_box()
            self.assertLessEqual(title['height'], 26)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))

    async def test_edge_chevron_collapses_and_reopens_sidebar(self):
        edge = self.page.locator('#sidebar-edge')
        self.assertEqual(await edge.count(), 1)
        self.assertTrue(await edge.is_visible())
        self.assertEqual(await edge.get_attribute('aria-expanded'), 'true')
        await edge.click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        self.assertTrue(await edge.is_visible())
        self.assertEqual(await edge.get_attribute('aria-expanded'), 'false')
        self.assertLessEqual((await edge.bounding_box())['x'], 2)
        await self.page.reload()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        await edge.click()
        self.assertTrue(await self.page.locator('#site-nav').is_visible())
        self.assertEqual(await self.page.locator('#menu-toggle').get_attribute('aria-expanded'), 'true')
        await self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertFalse(await edge.is_visible())
        await self.page.locator('#menu-toggle').click()
        self.assertTrue(await edge.is_visible())
        await edge.click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        self.assertFalse(await self.page.locator('#nav-backdrop').is_visible())

    async def test_themes_are_neutral_and_card_text_has_real_contrast(self):
        def hex_value(color):
            import re
            rgb = [int(number) for number in re.findall(r'\d+', color)[:3]]
            return '#' + ''.join(f'{value:02x}' for value in rgb)
        def luminance(color):
            values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            return sum(w * (v / 12.92 if v <= .04045 else ((v + .055)/1.055)**2.4)
                       for w, v in zip((.2126, .7152, .0722), values))
        def contrast(first, second):
            a, b = sorted((luminance(first), luminance(second)), reverse=True)
            return (a + .05)/(b + .05)
        for theme in ('light', 'dark'):
            await self.page.locator('#view-options-toggle').click()
            await self.page.locator('#theme-select').select_option(theme)
            await self.page.locator('#view-options-toggle').click()
            await self.page.wait_for_function('theme => document.documentElement.dataset.theme === theme', arg=theme)
            colors = await self.page.evaluate("""() => {
                const card = document.querySelector('.lead');
                const style = getComputedStyle(card);
                return {paper:getComputedStyle(document.body).backgroundColor,
                    nav:getComputedStyle(document.querySelector('.site-nav')).backgroundColor,
                    card:style.backgroundColor, ink:style.color,
                    muted:getComputedStyle(card.querySelector('.meta')).color,
                    label:getComputedStyle(document.querySelector('.breaking-label')).color,
                    strip:getComputedStyle(document.querySelector('.breaking')).backgroundColor};
            }""")
            colors = {key: hex_value(value) for key, value in colors.items()}
            for surface in ('paper', 'nav', 'card'):
                values = [int(colors[surface][i:i+2], 16) for i in (1, 3, 5)]
                self.assertLessEqual(max(values)-min(values), 24, (theme, surface, colors))
            self.assertGreaterEqual(contrast(colors['label'], colors['strip']), 4.5)
            self.assertGreaterEqual(contrast(colors['ink'], colors['card']), 4.5)
            self.assertGreaterEqual(contrast(colors['muted'], colors['card']), 4.5)
            favorite = self.page.locator('.lead .save-story')
            if await favorite.get_attribute('aria-pressed') != 'true': await favorite.click()
            await self.page.mouse.move(0, 0)
            chosen = await favorite.evaluate("el => ({ink:getComputedStyle(el).color, bg:getComputedStyle(el).backgroundColor})")
            self.assertGreaterEqual(contrast(hex_value(chosen['ink']), hex_value(chosen['bg'])), 4.5)
            if theme == 'dark':
                self.assertGreaterEqual(contrast(colors['paper'], colors['card']), 1.5)
            else:
                self.assertGreater(luminance(colors['card']), .9)

    async def test_date_is_right_aligned_and_count_matches_published_cards(self):
        expected = await self.page.locator('main .lead h2 a, main .rail-item h3 a, main .feature h3 a, main .compact h3 a').evaluate_all('nodes => new Set(nodes.map(a => a.href)).size')
        count = self.page.locator('.edition-count')
        self.assertEqual(await count.count(), 1)
        self.assertEqual(int(await count.get_attribute('data-news-count')), expected)
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            date = self.page.locator('.header-updated')
            self.assertTrue(await date.is_visible(), width)
            bounds = await date.bounding_box()
            bar = await self.page.locator('.bar-inner').bounding_box()
            self.assertGreater(bounds['x'] + bounds['width'], bar['x'] + bar['width'] - 40)
            self.assertTrue(await count.is_visible())
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))

    async def test_footer_has_only_useful_links_attribution_and_signature(self):
        footer = self.page.locator('.site-footer')
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            await footer.scroll_into_view_if_needed()
            text = await footer.inner_text()
            self.assertNotIn('Datos de esta edición', text)
            self.assertNotIn('Última actualización', text)
            self.assertNotIn('©', text)
            self.assertTrue(await footer.locator('.designer-signature').is_visible())
            self.assertTrue(await footer.locator('.designer-signature').evaluate("el => {const r=el.getBoundingClientRect(); return [r.x+8,r.x+r.width/2,r.right-8].every(x => el.contains(document.elementFromPoint(x,r.y+r.height/2))); }"), width)
            self.assertLessEqual((await footer.bounding_box())['height'], 140 if width >= 1024 else 280)

    async def test_latest_slides_continuously_and_pauses(self):
        await self.page.emulate_media(reduced_motion='no-preference')
        await self.page.reload()
        await self.page.mouse.move(0, 0)
        track = self.page.locator('.breaking-track')
        await self.page.wait_for_timeout(600)
        first = await track.evaluate('el => el.scrollLeft')
        self.assertGreater(first, 10)
        await self.page.wait_for_timeout(600)
        second = await track.evaluate('el => el.scrollLeft')
        self.assertGreater(second, first + 10)
        self.assertLess(second - first, 70)
        await track.hover()
        before = await track.evaluate('el => el.scrollLeft')
        await self.page.wait_for_timeout(400)
        self.assertAlmostEqual(await track.evaluate('el => el.scrollLeft'), before, delta=2)
        pause = self.page.locator('[data-carousel-pause]')
        await pause.click()
        await self.page.mouse.move(0, 0)
        before = await track.evaluate('el => el.scrollLeft')
        await self.page.wait_for_timeout(400)
        self.assertAlmostEqual(await track.evaluate('el => el.scrollLeft'), before, delta=2)
        await pause.click()
        await self.page.mouse.move(0, 0)
        await self.page.locator('.brand-link').focus()
        await self.page.wait_for_function('document.querySelector(".breaking-track").scrollLeft > ' + str(before + 10))
        clone = track.locator('[data-carousel-clone]')
        self.assertEqual(await clone.get_attribute('aria-hidden'), 'true')
        self.assertEqual(await clone.locator('a').get_attribute('tabindex'), '-1')
        await track.hover()
        await track.evaluate('el => el.scrollLeft = el.clientWidth * 5.8')
        destination = await clone.locator('a').get_attribute('href')
        await self.page.route(destination, lambda route: route.fulfill(status=200, content_type='text/html', body='<h1>Artículo original</h1>'))
        await clone.locator('a').click()
        await self.page.wait_for_url(destination)
        self.assertEqual(len(self.context.pages), 1)
        await self.page.go_back()
        await self.page.locator('.brand-link').focus()
        await self.page.mouse.move(0, 0)
        await track.evaluate('el => el.scrollLeft = el.clientWidth * 6 - 5')
        await self.page.wait_for_function('document.querySelector(".breaking-track").scrollLeft < 100')
        self.assertLess(await self.page.locator('.breaking-track').evaluate('el => el.scrollLeft'), 100)

    async def test_reduced_motion_does_not_auto_start(self):
        pause = self.page.locator('[data-carousel-pause]')
        self.assertEqual(await pause.count(), 1)
        self.assertEqual(await pause.get_attribute('aria-pressed'), 'true')
        await self.page.wait_for_timeout(6500)
        self.assertEqual(await self.page.locator('.breaking-track').evaluate('el => el.scrollLeft'), 0)

    async def test_shared_grid_aligns_all_bands_open_and_closed(self):
        for width in (320, 390, 768, 1024, 1440, 1920, 2560):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            for collapsed in ((False, True) if width >= 1024 else (False,)):
                if width >= 1024:
                    actual = await self.page.locator('html').get_attribute('data-sidebar')
                    if (actual == 'hidden') != collapsed: await self.page.locator('#menu-toggle').click()
                boxes = await self.page.evaluate("""() => {
                    const selectors=['.bar-inner','.breaking-inner','main.container','.newsletter-invite-inner','.site-footer > .container'];
                    return selectors.map(selector => {const el=document.querySelector(selector), r=el.getBoundingClientRect(), css=getComputedStyle(el);
                      return {selector,x:r.x,width:r.width,left:r.x+parseFloat(css.paddingLeft),right:r.right-parseFloat(css.paddingRight)};});
                }""")
                main = boxes[2]
                for box in boxes:
                    self.assertAlmostEqual(box['left'], main['left'], delta=1, msg=(width, collapsed, boxes))
                    self.assertAlmostEqual(box['right'], main['right'], delta=1, msg=(width, collapsed, boxes))
                if width >= 1920: self.assertGreaterEqual(main['width'], 1400)
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        ARTIFACTS.mkdir(exist_ok=True)
        for collapsed in (False, True):
            actual = await self.page.locator('html').get_attribute('data-sidebar')
            if (actual == 'hidden') != collapsed: await self.page.locator('#menu-toggle').click()
            await self.page.screenshot(path=str(ARTIFACTS / f'aligned-1920-{collapsed}.png'))

    async def test_header_is_compact_without_losing_controls(self):
        for width in (320, 390, 768, 1024, 1440, 1920, 2560):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            header = await self.page.locator('.site-header').bounding_box()
            self.assertLessEqual(header['height'], 80 if width < 1024 else 68, (width, header))
            for selector in ('#menu-toggle','#theme-toggle','#search-toggle','#view-options-toggle','#library-toggle','.header-updated','.edition-count'):
                self.assertTrue(await self.page.locator(selector).is_visible(), (width, selector))
            boxes = [await item.bounding_box() for item in await self.page.locator('.bar-inner .icon-btn:visible').all()]
            boxes.sort(key=lambda box: box['x'])
            self.assertTrue(all(a['x']+a['width'] <= b['x'] for a,b in zip(boxes, boxes[1:])), (width, boxes))
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))

    async def test_search_keeps_sidebar_navigation_unobstructed(self):
        await self.page.locator('#search-toggle').click()
        link = self.page.locator('.site-nav a').first
        self.assertTrue(await link.evaluate("el => {const r=el.getBoundingClientRect(); return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}"))
        await self.page.keyboard.press('Escape')
        self.assertFalse(await self.page.locator('#search-panel').is_visible())

    async def test_blocked_storage_does_not_disable_controls(self):
        await self.context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked')}})")
        await self.page.reload()
        await self.page.locator('#menu-toggle').click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        await self.page.locator('#theme-toggle').click()
        self.assertIn(await self.page.locator('html').get_attribute('data-theme'), ('light', 'dark'))


if __name__ == '__main__': unittest.main()
