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

    async def toggle_view_options(self):
        button = self.page.locator('#view-options-toggle')
        if not await button.is_visible():
            await self.page.locator('#menu-toggle').click()
        await button.click()

    async def toggle_library(self):
        button = self.page.locator('#library-toggle')
        if not await button.is_visible():
            await self.page.locator('#menu-toggle').click()
        await button.click()

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

    async def test_header_clock_uses_the_device_timezone(self):
        from datetime import datetime, timezone
        context = await self.browser.new_context(timezone_id='America/Santiago')
        try:
            await context.route('https://**/*', lambda route: route.abort())
            page = await context.new_page()
            await page.clock.install(time=datetime(2026, 10, 27, 18, 6, tzinfo=timezone.utc))
            await page.goto(self.url)
            clock = page.locator('#site-clock')
            self.assertEqual(await clock.count(), 1)
            self.assertEqual(await clock.inner_text(), '15:06')
            self.assertIn('America/Santiago', await clock.get_attribute('title'))
            self.assertFalse(await page.locator('#updated-at').is_visible())
            self.assertNotIn('Actualizado', await page.locator('.header-status').inner_text())
            await page.clock.fast_forward(60000)
            self.assertEqual(await clock.inner_text(), '15:07')
        finally:
            await context.close()

    async def test_refresh_bar_reports_estimate_and_pending_publication(self):
        from datetime import datetime, timedelta
        self.assertTrue(await self.page.locator('#refresh-progress').count())
        stamp = await self.page.locator('#updated-at').get_attribute('datetime')
        edition = datetime.fromisoformat(stamp)
        scheduled = edition.replace(minute=7, second=0, microsecond=0)
        if scheduled <= edition:
            scheduled += timedelta(hours=1)
        await self.page.clock.install(time=scheduled - timedelta(minutes=15))
        await self.page.reload()
        progress = self.page.locator('#refresh-progress')
        self.assertIn('15 min', await self.page.locator('#refresh-help').text_content())
        self.assertIn('prevista', await progress.get_attribute('aria-valuetext'))
        await progress.focus()
        await self.page.clock.fast_forward(16 * 60000)
        self.assertIn('pendiente', await self.page.locator('#refresh-help').text_content())
        self.assertEqual(await progress.get_attribute('aria-valuenow'), '0')

    async def test_initial_bar_has_no_loading_animation(self):
        fill = self.page.locator('#refresh-fill')
        self.assertEqual(await fill.evaluate('el => getComputedStyle(el).transitionDuration'), '0s')

    async def test_header_groups_remain_in_one_row_and_mobile_tools_are_reachable(self):
        for width in (320, 375, 390, 768, 1024, 1440, 2560):
            await self.page.set_viewport_size({'width': width, 'height': 900})
            boxes = [await self.page.locator(s).bounding_box() for s in
                     ('.brand-link','#theme-toggle','#search-toggle','#site-clock','.edition-count','#refresh-now')]
            centers = [b['y'] + b['height'] / 2 for b in boxes]
            self.assertLessEqual(max(centers) - min(centers), 4, (width, centers))
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
            if width < 1024:
                self.assertFalse(await self.page.locator('#view-options-toggle').is_visible())
                await self.page.locator('#menu-toggle').click()
                self.assertTrue(await self.page.locator('#nav-tools #view-options-toggle').is_visible())
                self.assertTrue(await self.page.locator('#nav-tools #library-toggle').is_visible())
                await self.page.locator('#menu-toggle').click()

    async def test_cards_lift_smoothly_and_respect_reduced_motion(self):
        await self.page.emulate_media(reduced_motion='no-preference')
        card = self.page.locator('.section-grid .feature').first
        await card.scroll_into_view_if_needed()
        original = await card.evaluate('el => ({top:el.offsetTop,height:el.offsetHeight})')
        await card.hover()
        await self.page.wait_for_function("getComputedStyle(document.querySelector('.section-grid .feature')).transform !== 'none'")
        moved = await card.evaluate('el => ({top:el.offsetTop,height:el.offsetHeight})')
        self.assertEqual(original, moved)
        await self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(await card.evaluate('el => getComputedStyle(el).transform'), 'none')

    async def test_resizing_with_view_settings_open_keeps_keyboard_focus_visible(self):
        await self.page.set_viewport_size({'width': 900, 'height': 900})
        await self.toggle_view_options()
        await self.page.locator('#text-size').focus()
        await self.page.set_viewport_size({'width': 1200, 'height': 900})
        await self.page.wait_for_function("document.querySelector('#view-options-toggle').closest('#header-actions')")
        self.assertFalse(await self.page.locator('#view-options-panel').is_visible())
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'view-options-toggle')
        await self.toggle_view_options()
        await self.page.locator('#text-size').focus()
        await self.page.set_viewport_size({'width': 900, 'height': 900})
        await self.page.wait_for_function("document.querySelector('#view-options-toggle').closest('#nav-tools')")
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'menu-toggle')

    async def test_related_media_open_with_their_own_dates_without_extra_cards(self):
        import sys
        import tempfile
        from datetime import datetime, timezone
        sys.path.insert(0, str(ROOT))
        import fetch_noticias as news
        now = datetime(2026, 10, 28, 13, tzinfo=timezone.utc)
        story = {'category': 'internacional', 'title': 'Cobertura internacional de prueba',
                 'sources': ['BioBioChile'], 'source_url': 'https://www.biobiochile.cl',
                 'link': 'https://www.biobiochile.cl/nota', 'published': now.isoformat(),
                 'related_coverages': [
                     {'source': 'CNN Chile', 'source_url': 'https://www.cnnchile.com',
                      'title': 'Titular original de CNN Chile',
                      'link': 'https://news.google.com/rss/articles/testCNN',
                      'published': '2026-10-28T10:55:00Z'},
                     {'source': 'Teletrece', 'source_url': 'https://www.t13.cl',
                      'title': 'Titular original de Teletrece',
                      'link': 'https://news.google.com/rss/articles/testT13',
                      'published': '2026-10-28T11:05:00Z'}]}
        with tempfile.TemporaryDirectory() as folder:
            news.build_site([story], now, folder)
            body = Path(folder, 'index.html').read_text()
        await self.page.route('**/?related-fixture=1', lambda route: route.fulfill(
            status=200, content_type='text/html', body=body))
        for width in (390, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 900})
            await self.page.goto(self.url + '?related-fixture=1')
            self.assertEqual(await self.page.locator('.edition-count').get_attribute('data-news-count'), '1')
            trigger = self.page.locator('[data-coverage-trigger]')
            await trigger.click()
            dialog = self.page.locator('.coverage-dialog')
            self.assertTrue(await dialog.is_visible())
            self.assertIn('CNN Chile', await dialog.inner_text())
            self.assertIn('Teletrece', await dialog.inner_text())
            row = dialog.locator('li').filter(has_text='Titular original de CNN Chile')
            self.assertEqual(await row.locator('time').get_attribute('datetime'), '2026-10-28T10:55:00Z')
            self.assertIsNone(await row.locator('a').get_attribute('target'))
            self.assertFalse(await dialog.evaluate('el=>el.scrollWidth > el.clientWidth + 2'))
            await self.page.keyboard.press('Escape')
            self.assertFalse(await dialog.is_visible())
            self.assertTrue(await trigger.evaluate('el=>document.activeElement === el'))

    async def test_refresh_same_edition_preserves_reading_position(self):
        button = self.page.locator('#refresh-now')
        self.assertEqual(await button.count(), 1)
        body = json.dumps({'updated': await self.page.locator('#updated-at').get_attribute('datetime')})
        requests = []
        async def current_edition(route):
            requests.append((route.request.method, route.request.url))
            await route.fulfill(content_type='application/json', body=body)
        await self.page.route('**/edition.json?edition_check=*', current_edition)
        await self.page.evaluate('window.scrollTo(0, 400)')
        before = await self.page.evaluate('scrollY')
        box = await button.bounding_box()
        await self.page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        await self.page.wait_for_function("document.querySelector('#refresh-status').textContent.includes('No hay una edición')")
        self.assertEqual(await self.page.evaluate('scrollY'), before)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], 'GET')
        self.assertTrue(requests[0][1].startswith(self.url))
        self.assertTrue(await button.is_enabled())
        self.assertEqual(await button.get_attribute('aria-busy'), 'false')

    async def test_refresh_loads_new_edition_and_keeps_search_context(self):
        from datetime import datetime, timedelta
        self.assertEqual(await self.page.locator('#refresh-now').count(), 1)
        previous = await self.page.locator('#updated-at').get_attribute('datetime')
        newer = (datetime.fromisoformat(previous) + timedelta(minutes=1)).isoformat()
        body = (ROOT / 'public/index.html').read_text().replace(previous, newer)
        await self.page.route('**/edition.json?edition_check=*', lambda route: route.fulfill(content_type='application/json', body=json.dumps({'updated': newer})))
        await self.page.route(self.url + '?edition=*', lambda route: route.fulfill(content_type='text/html', body=body))
        await self.page.locator('#search-toggle').click()
        await self.page.locator('#search-input').fill('Brasil')
        history_length = await self.page.evaluate('history.length')
        await self.page.locator('#refresh-now').click()
        await self.page.wait_for_function('stamp => document.querySelector("#updated-at").dateTime === stamp', arg=newer)
        self.assertEqual(await self.page.locator('#search-input').input_value(), 'Brasil')
        self.assertTrue(await self.page.locator('#search-panel').is_visible())
        self.assertEqual(await self.page.evaluate('history.length'), history_length)

    async def test_refresh_failure_keeps_news_available_and_allows_retry(self):
        button = self.page.locator('#refresh-now')
        self.assertEqual(await button.count(), 1)
        stamp = await self.page.locator('#updated-at').get_attribute('datetime')
        responses = [(503, 'Servicio no disponible'), (200, json.dumps({'updated': 'fecha inválida'})),
                     (200, json.dumps({'updated': stamp}))]
        async def respond(route):
            status, body = responses.pop(0)
            await route.fulfill(status=status, content_type='application/json', body=body)
        await self.page.route('**/edition.json?edition_check=*', respond)
        for _ in range(2):
            await button.click()
            await self.page.wait_for_function("document.querySelector('#refresh-status').textContent.includes('No se pudo comprobar')")
            self.assertTrue(await self.page.locator('.lead-title').is_visible())
            self.assertTrue(await button.is_enabled())
        await button.click()
        await self.page.wait_for_function("document.querySelector('#refresh-status').textContent.includes('No hay una edición')")

    async def test_refresh_timeout_releases_the_button(self):
        button = self.page.locator('#refresh-now')
        self.assertEqual(await button.count(), 1)
        await self.page.clock.install()
        pending = []
        await self.page.route('**/edition.json?edition_check=*', lambda route: pending.append(route))
        await button.click()
        await self.page.wait_for_function("document.querySelector('#refresh-now').getAttribute('aria-busy') === 'true'")
        await self.page.clock.fast_forward(12000)
        await self.page.wait_for_function("document.querySelector('#refresh-now').getAttribute('aria-busy') === 'false'")
        self.assertIn('No se pudo comprobar', await self.page.locator('#refresh-status').inner_text())
        self.assertTrue(await button.is_enabled())

    async def test_refresh_help_is_visible_on_hover_focus_and_touch(self):
        progress = self.page.locator('#refresh-progress')
        help_text = self.page.locator('#refresh-help')
        self.assertEqual(await help_text.count(), 1)
        await progress.hover()
        self.assertTrue(await help_text.is_visible())
        await help_text.hover()
        self.assertTrue(await help_text.is_visible())
        await self.page.keyboard.press('Escape')
        self.assertFalse(await help_text.is_visible())
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 900})
            await self.page.locator('.brand-link').focus()
            await progress.focus()
            self.assertTrue(await help_text.is_visible(), width)
            bounds = await help_text.bounding_box()
            self.assertGreaterEqual(bounds['x'], 0, width)
            self.assertLessEqual(bounds['x'] + bounds['width'], width, width)
            await self.page.keyboard.press('Escape')
            self.assertFalse(await help_text.is_visible())
        context = await self.browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
        try:
            await context.route('https://**/*', lambda route: route.abort())
            page = await context.new_page()
            await page.goto(self.url)
            await page.locator('#refresh-progress').tap()
            self.assertTrue(await page.locator('#refresh-help').is_visible())
            await page.touchscreen.tap(10, 400)
            self.assertFalse(await page.locator('#refresh-help').is_visible())
        finally:
            await context.close()

    async def test_view_selector_shows_current_mode_and_preserves_choice(self):
        await self.toggle_view_options()
        selector = self.page.get_by_label('Vista', exact=True)
        self.assertEqual(await selector.evaluate('el => el.tagName'), 'SELECT')
        self.assertEqual(await selector.input_value(), 'editorial')
        self.assertEqual(await selector.locator('option:checked').inner_text(), 'Normal')
        for mode, css_class in (('compact', 'is-compact'), ('headlines', 'is-headlines'), ('editorial', '')):
            await selector.select_option(mode)
            self.assertEqual(await self.page.locator('#contenido').evaluate("el => [...el.classList].filter(c => c === 'is-compact' || c === 'is-headlines').join(' ')"), css_class)
            await self.page.reload()
            await self.toggle_view_options()
            self.assertEqual(await selector.input_value(), mode)
        await self.page.locator('#text-size').select_option('large')
        await selector.select_option('compact')
        self.assertEqual(await self.page.locator('#text-size').input_value(), 'large')

    async def test_history_can_be_opened_with_keyboard_without_javascript(self):
        from scripts.editorial_signals import render_signals
        published = '2026-10-26T10:16:00+00:00'
        timeline = render_signals([], [[{'title': 'Publicación de prueba',
            'link': 'https://example.org/historia', 'published': published}]])
        body = (ROOT / 'public/index.html').read_text().replace('</main>', timeline.replace('timeline-title-0', 'qa-timeline') + '</main>')
        context = await self.browser.new_context(java_script_enabled=False)
        try:
            await context.route('https://**/*', lambda route: route.abort())
            await context.route('**/?timeline-qa=1', lambda route: route.fulfill(content_type='text/html', body=body))
            page = await context.new_page()
            await page.goto(self.url + '?timeline-qa=1')
            history = page.locator('details[aria-labelledby="qa-timeline"]')
            self.assertFalse(await history.locator('a').is_visible())
            await history.locator('summary').focus()
            await page.keyboard.press('Enter')
            self.assertTrue(await history.locator('a').is_visible())
            self.assertEqual(await history.locator('time').get_attribute('datetime'), published)
            self.assertEqual(await history.locator('time').inner_text(), '26 oct 2026, 07:16')
        finally:
            await context.close()

    async def test_card_actions_leave_category_clear_and_have_separate_touch_targets(self):
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 900})
            cards = self.page.locator('.lead,.rail-list li,.section-grid .feature,.section-grid .compact-list li').filter(has=self.page.locator('.save-story'))
            for card in await cards.all():
                if not await card.is_visible():
                    continue
                self.assertEqual(await card.locator('.kicker .card-actions').count(), 0, width)
                footer = card.locator('.card-footer')
                self.assertEqual(await footer.locator('.meta').count(), 1)
                buttons = await footer.locator('.save-story,.share-story').all()
                boxes = [await b.bounding_box() for b in buttons]
                for box in boxes:
                    self.assertGreaterEqual(box['width'], 44, width)
                    self.assertGreaterEqual(box['height'], 44, width)
                self.assertLessEqual(boxes[0]['x'] + boxes[0]['width'], boxes[1]['x'], width)

    async def test_section_photos_keep_landscape_ratio_with_long_headlines(self):
        await self.page.route('https://images.example/*.png', lambda route: route.fulfill(
            content_type='image/png', body=(ROOT / 'static' / 'icon-192.png').read_bytes()))
        await self.load_latam_lead_fixture('<meta property="og:image" content="https://images.example/{publisher}.png">')
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 900})
            card = self.page.locator('.section-grid .feature').first
            await card.locator('h3 a').evaluate("el => el.textContent = 'Un titular excepcionalmente largo sobre ciencia, salud y tecnología que conserva todo su texto sin alargar ni deformar la fotografía de la noticia'")
            image = await card.locator('.media').bounding_box()
            self.assertAlmostEqual(image['width'] / image['height'], 4 / 3, delta=.03, msg=str(width))
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)

    async def test_latam_visuals_are_visible_and_respect_reader_density(self):
        await self.load_latam_lead_fixture(coverage_countries=['AR', 'BR', 'CO', 'MX'])
        figures = self.page.locator('.cat-latinoamerica .media--region')
        self.assertGreater(await figures.count(), 0)
        for width in (320, 390, 768, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            self.assertTrue(await figures.first.is_visible(), width)
            self.assertTrue(await figures.first.locator('.region-label').is_visible(), width)
            fallback = self.page.locator('.section-grid .media--region:visible').first
            box = await fallback.bounding_box()
            for part in ('.source-mark', '.region-label'):
                child = await fallback.locator(part).bounding_box()
                self.assertGreaterEqual(child['y'], box['y'], (width, part))
                self.assertLessEqual(child['y'] + child['height'], box['y'] + box['height'], (width, part))
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'), width)
        # Las miniaturas también deben poder ocultarse al elegir una vista densa.
        await self.page.locator('#contenido').evaluate("el => el.classList.add('is-compact')")
        self.assertFalse(await figures.first.is_visible())
        await self.page.locator('#contenido').evaluate("el => {el.classList.remove('is-compact'); el.classList.add('is-headlines')}")
        self.assertFalse(await figures.first.is_visible())

    async def load_latam_lead_fixture(self, publisher_html=None, coverage_countries=None):
        import sys, tempfile
        from datetime import datetime, timezone
        sys.path.insert(0, str(ROOT))
        import fetch_noticias as news
        now = datetime(2026, 10, 26, 2, tzinfo=timezone.utc)
        stories = [{"category": "latinoamerica", "title": f"Brasil y México cooperan {i}",
                    "link": f"https://medio{i}.example/nota", "source_url": f"https://medio{i}.example",
                    "sources": [f"Medio {i}"], "image": "", "summary": "", "metadata_only": True,
                    "coverage_countries": coverage_countries or ["BR", "MX"], "published": now.isoformat()}
                   for i in range(12)]
        if publisher_html:
            from unittest.mock import patch
            from urllib.parse import urlsplit
            from scripts.article_images import enrich_visible_images, image_from_html
            for story in stories:
                story['metadata_only'] = False
            with patch('scripts.article_images.permitted_url', return_value=True):
                enrich_visible_images(stories, news.select(stories, now), now,
                                      fetch_image=lambda url: image_from_html(
                                          publisher_html.replace('{publisher}', urlsplit(url).hostname), url))
            self.assertTrue(all(story['image'] for story in stories))
        with tempfile.TemporaryDirectory() as folder:
            if publisher_html:
                history = Path(folder, 'history.json')
                news.save_history(history, stories, now)
                stories = news.load_history(history)
            news.build_site(stories, now, folder)
            body = Path(folder, 'index.html').read_text()
        await self.page.route('**/?latam-visual=1', lambda route: route.fulfill(status=200, content_type='text/html', body=body))
        await self.page.goto(self.url + '?latam-visual=1')

    async def test_latam_photos_survive_enrichment_history_and_load_as_images(self):
        # Recurso controlado de prueba, nunca se publica como foto de una noticia.
        await self.page.route('https://images.example/*.png', lambda route: route.fulfill(
            content_type='image/png', body=(ROOT / 'static' / 'icon-192.png').read_bytes()))
        await self.load_latam_lead_fixture('<meta property="og:image" content="https://images.example/{publisher}.png">')
        for width in (390, 1440):
            await self.page.set_viewport_size({'width': width, 'height': 1000})
            image = self.page.locator('.section-grid .media > img').first
            await image.scroll_into_view_if_needed()
            await self.page.wait_for_function("[...document.querySelectorAll('.section-grid .media > img')].some(img=>img.complete&&img.naturalWidth>0)")
            self.assertGreater(await image.evaluate('img=>img.naturalWidth'), 0)
            self.assertEqual(await self.page.locator('.media--region').count(), 0)

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
        await self.toggle_view_options()
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
        await self.toggle_view_options()
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
        await self.toggle_view_options()
        await self.page.locator('#text-size').select_option('large')
        await self.toggle_view_options()
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
        await self.toggle_view_options()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.toggle_view_options()
        await self.page.locator('#site-nav a[href="#cat-medioambiente"]').click()
        self.assertTrue(await self.page.locator('#cat-medioambiente').is_visible())
        self.assertEqual(await self.page.locator('#category-preference').input_value(), '')
        await self.toggle_view_options()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.toggle_view_options()
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
        await self.toggle_view_options()
        await self.page.locator('#category-preference').select_option('cultura')
        await self.toggle_view_options()
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
        await self.toggle_view_options()
        await self.page.locator('#source-sort').select_option('relevance')
        self.assertFalse(await grid.locator('.feature,.compact-list li').first.evaluate("el=>el.classList.contains('feature')"))
        await self.page.locator('#source-sort').select_option('recent')
        self.assertTrue(await grid.locator('.feature,.compact-list li').first.evaluate("el=>el.classList.contains('feature')"))
        dates = await grid.evaluate("grid=>[...grid.querySelectorAll('.feature,.compact-list li')].map(el=>Date.parse(el.querySelector('time').dateTime)||0)")
        self.assertEqual(dates, sorted(dates, reverse=True))

    async def test_desktop_sidebar_defaults_visible_and_choice_survives_reload(self):
        nav, toggle = self.page.locator('#site-nav'), self.page.locator('#sidebar-edge')
        self.assertFalse(await self.page.locator('#menu-toggle').is_visible())
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

    async def test_mobile_menu_starts_at_sections_and_closes_before_background_focus(self):
        await self.page.set_viewport_size({'width':390,'height':844})
        await self.page.locator('#menu-toggle').click()
        self.assertTrue(await self.page.evaluate("!!document.activeElement.closest('#site-nav')"))
        await self.page.locator('#site-nav a').last.focus()
        await self.page.keyboard.press('Tab')
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'view-options-toggle')
        await self.page.keyboard.press('Tab')
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'library-toggle')
        await self.page.keyboard.press('Tab')
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'sidebar-edge')
        await self.page.keyboard.press('Tab')
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        self.assertFalse(await self.page.locator('#nav-backdrop').is_visible())
        self.assertTrue(await self.page.evaluate("document.activeElement.matches('[data-carousel-pause]')"))

    async def test_reopening_scrolled_mobile_menu_keeps_focused_link_visible(self):
        await self.page.set_viewport_size({'width':844,'height':390})
        await self.page.locator('#menu-toggle').click()
        await self.page.locator('#site-nav').evaluate('el=>el.scrollTop=el.scrollHeight')
        await self.page.locator('#sidebar-edge').click()
        before = await self.page.evaluate('scrollY')
        await self.page.locator('#menu-toggle').click()
        bounds = await self.page.locator('#site-nav').bounding_box()
        focused = await self.page.evaluate("""()=>{const r=document.activeElement.getBoundingClientRect();return {top:r.top,bottom:r.bottom,inNav:!!document.activeElement.closest('#site-nav')}}""")
        self.assertTrue(focused['inNav'])
        self.assertGreaterEqual(focused['top'], bounds['y'])
        self.assertLessEqual(focused['bottom'], bounds['y'] + bounds['height'])
        self.assertEqual(await self.page.evaluate('scrollY'), before)

    async def test_theme_follows_system_and_manual_choice_is_retained(self):
        await self.page.emulate_media(color_scheme='dark')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.toggle_view_options()
        await self.page.locator('#theme-select').select_option('system')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.locator('#theme-select').select_option('light')
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.page.reload()
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'light')
        await self.toggle_view_options()
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
            await self.toggle_view_options()
            await self.page.locator('#theme-select').select_option(theme)
            await self.toggle_view_options()
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
        await self.toggle_view_options()
        self.assertTrue(await self.page.locator('#site-nav').is_visible())
        self.assertTrue(await self.page.locator('#view-options-panel').is_visible())
        await self.page.keyboard.press('Escape')
        self.assertFalse(await self.page.locator('#site-nav').is_visible())

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
            await self.toggle_view_options()
            await check_view_options_bounds(self.page, width)
            await self.toggle_view_options()
        await self.page.locator('.save-story:visible').first.click()
        await self.toggle_library()
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
        self.assertTrue(await edge.evaluate("el=>{const r=el.getBoundingClientRect();return document.elementFromPoint(r.left-1,r.top+r.height/2)?.closest('#sidebar-edge')===el}"))
        self.assertEqual(await edge.get_attribute('aria-expanded'), 'true')
        await edge.click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        self.assertTrue(await edge.is_visible())
        self.assertEqual(await edge.get_attribute('aria-expanded'), 'false')
        self.assertLessEqual((await edge.bounding_box())['x'], 2)
        self.assertTrue(await edge.evaluate("el=>{const r=el.getBoundingClientRect();return document.elementFromPoint(r.right+3,r.top+r.height/2)?.closest('#sidebar-edge')===el}"))
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
            await self.toggle_view_options()
            await self.page.locator('#theme-select').select_option(theme)
            await self.toggle_view_options()
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
            chosen = await favorite.evaluate("""async el => {
                await Promise.allSettled(el.getAnimations().map(animation => animation.finished));
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 1;
                const ctx = canvas.getContext('2d');
                const rgb = color => {
                    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = color; ctx.fillRect(0, 0, 1, 1);
                    return 'rgb(' + [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 3).join(',') + ')';
                };
                return {ink:rgb(getComputedStyle(el).color), bg:rgb(getComputedStyle(el).backgroundColor)};
            }""")
            self.assertGreaterEqual(contrast(hex_value(chosen['ink']), hex_value(chosen['bg'])), 4.5)
            if theme == 'dark':
                self.assertGreaterEqual(contrast(colors['paper'], colors['card']), 1.5)
            else:
                self.assertGreater(luminance(colors['card']), .9)

    async def test_clock_is_right_aligned_and_count_matches_published_cards(self):
        expected = await self.page.locator('main .lead h2 a, main .rail-item h3 a, main .section:not(.cat-agenda) .feature h3 a, main .section:not(.cat-agenda) .compact h3 a').evaluate_all('nodes => new Set(nodes.map(a => a.href)).size')
        count = self.page.locator('.edition-count')
        self.assertEqual(await count.count(), 1)
        self.assertEqual(int(await count.get_attribute('data-news-count')), expected)
        for width in (320, 390, 768, 1024, 1440):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            date = self.page.locator('#site-clock')
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
                    if (actual == 'hidden') != collapsed: await self.page.locator('#sidebar-edge').click()
                boxes = await self.page.evaluate("""() => {
                    const selectors=['.bar-inner','.breaking-inner','main.container','.newsletter-invite-inner','.site-footer > .container'];
                    return selectors.map(selector => {const el=document.querySelector(selector), r=el.getBoundingClientRect(), css=getComputedStyle(el);
                      return {selector,x:r.x,width:r.width,left:r.x+parseFloat(css.paddingLeft),right:r.right-parseFloat(css.paddingRight)};});
                }""")
                main = boxes[2]
                for box in boxes:
                    if box['selector'] == '.breaking-inner':
                        self.assertAlmostEqual(box['x'], 0, delta=1, msg=(width, collapsed, boxes))
                        self.assertAlmostEqual(box['width'], width, delta=1, msg=(width, collapsed, boxes))
                        continue
                    self.assertAlmostEqual(box['left'], main['left'], delta=1, msg=(width, collapsed, boxes))
                    self.assertAlmostEqual(box['right'], main['right'], delta=1, msg=(width, collapsed, boxes))
                sidebar = 216 if width >= 1024 and not collapsed else 0
                gutter = 12 if width <= 360 else 16 if width <= 767 else 32
                self.assertAlmostEqual(main['left'], sidebar + gutter, delta=1, msg=(width, collapsed, boxes))
                self.assertAlmostEqual(main['right'], width - gutter, delta=1, msg=(width, collapsed, boxes))
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 2'))
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        ARTIFACTS.mkdir(exist_ok=True)
        for collapsed in (False, True):
            actual = await self.page.locator('html').get_attribute('data-sidebar')
            if (actual == 'hidden') != collapsed: await self.page.locator('#sidebar-edge').click()
            await self.page.screenshot(path=str(ARTIFACTS / f'aligned-1920-{collapsed}.png'))

    async def test_latest_is_36px_edge_to_edge_with_navigation_below_it(self):
        for width in (320,390,768,1024,1440,1920,2560):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.evaluate('scrollTo(0,0)')
            for scrolled in (False,True):
                if scrolled: await self.page.evaluate('scrollTo(0,300)')
                strip=await self.page.locator('.breaking').bounding_box()
                self.assertAlmostEqual(strip['x'],0,delta=1,msg=(width,scrolled,strip))
                self.assertAlmostEqual(strip['width'],width,delta=1,msg=(width,scrolled,strip))
                self.assertAlmostEqual(strip['height'],36,delta=1,msg=(width,scrolled,strip))
                if width<1024: await self.page.locator('#menu-toggle').click()
                nav=await self.page.locator('#site-nav').bounding_box()
                self.assertAlmostEqual(nav['y'],strip['y']+strip['height'],delta=1,msg=(width,scrolled,nav,strip))
                self.assertTrue(await self.page.locator('.breaking').evaluate('el=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(24,r.y+r.height/2));}'))
                if width<1024: await self.page.locator('#menu-toggle').click()
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth+2'))

    async def test_photo_lead_and_highlights_share_top_and_bottom_without_blank_padding(self):
        import tempfile
        from datetime import datetime,timezone
        import fetch_noticias as news
        now=datetime(2026,10,28,18,tzinfo=timezone.utc)
        titles=('Titular principal de prueba con una fotografía y varias líneas para comprobar toda la portada',
                'Una noticia destacada breve sin fotografía',
                'Una segunda noticia de prueba con una fotografía cuadrada y un titular de varias líneas',
                'Tercera noticia destacada con fotografía y otras fuentes para consultar',
                'Una noticia adicional de reserva para conservar la sección del portal')
        stories=[{'category':'internacional','title':title,'link':f'https://fixture.example/news/{i}',
                  'sources':[f'Fuente informativa {n}' for n in range(4 if i==0 else 2)],
                  'published':now.isoformat(),'image':'https://fixture.example/photo.png' if i!=1 else ''}
                 for i,title in enumerate(titles)]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories,now,folder)
            body=Path(folder,'index.html').read_text()
        await self.page.route('**/?photo-alignment=1',lambda route:route.fulfill(status=200,content_type='text/html',body=body))
        # Recurso local decodificable: ejercita la fotografía cargada, sin depender de un editor externo.
        await self.page.route('https://fixture.example/photo.png',lambda route:route.fulfill(status=200,content_type='image/png',body=(ROOT/'static/og-image.png').read_bytes()))
        await self.page.goto(self.url+'?photo-alignment=1')
        await self.page.wait_for_function('document.querySelector(".lead .media > img").naturalWidth>0')
        await self.page.wait_for_function('[...document.querySelectorAll(".rail-item .media > img")].every(img=>img.naturalWidth>0)')
        for width in (1280,1440,1920,2560):
            await self.page.set_viewport_size({'width':width,'height':1100})
            for collapsed in (False,True):
                actual=await self.page.locator('html').get_attribute('data-sidebar')
                if (actual=='hidden')!=collapsed: await self.page.locator('#sidebar-edge').click()
                for text_size in ('normal','large'):
                    await self.page.locator('#contenido').evaluate('(el,size)=>el.dataset.textSize=size',text_size)
                    # También cubre el rótulo que gana altura al mostrar las novedades de una visita.
                    await self.page.locator('#visit-updates').evaluate('el=>{el.hidden=false;el.textContent="12 nuevas · Ver";}')
                    lead=await self.page.locator('.lead').bounding_box()
                    cards=await self.page.locator('.rail-list > li').all()
                    first,last=await cards[0].bounding_box(),await cards[-1].bounding_box()
                    self.assertAlmostEqual(lead['y'],first['y'],delta=1,msg=(width,collapsed,text_size,lead,first))
                    self.assertAlmostEqual(lead['y']+lead['height'],last['y']+last['height'],delta=1,msg=(width,collapsed,text_size,lead,last))
                    title=await self.page.locator('.lead-title').bounding_box()
                    footer=await self.page.locator('.lead > .card-footer').bounding_box()
                    self.assertLessEqual(footer['y']-(title['y']+title['height']),40,(width,collapsed,text_size))
                    image=self.page.locator('.lead > .media > img')
                    self.assertGreater(await image.evaluate('el=>el.naturalWidth'),0)
                    self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth+2'))
        # Si hay menos destacadas, no se reserva una fila vacía para la tercera.
        await self.page.set_viewport_size({'width':1440,'height':1100})
        for remaining in (2,1):
            await self.page.locator('.rail-list > li').last.evaluate('el=>el.remove()')
            self.assertEqual(await self.page.locator('.rail-list > li').count(),remaining)
            lead=await self.page.locator('.lead').bounding_box()
            last=await self.page.locator('.rail-list > li').last.bounding_box()
            self.assertAlmostEqual(lead['y']+lead['height'],last['y']+last['height'],delta=1,msg=remaining)
        await self.page.locator('.lead .media > img').evaluate('el=>el.src="https://fixture.example/missing.jpg"')
        await self.page.wait_for_function('document.querySelector(".lead > .media").classList.contains("media--source")')
        self.assertFalse(await self.page.locator('.lead-heading').is_visible())
        self.assertLess((await self.page.locator('.lead').bounding_box())['height'],420)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth+2'))

    async def test_header_has_a_solid_neutral_surface_in_both_themes(self):
        for theme in ('light', 'dark'):
            await self.page.locator('html').evaluate('(el,theme)=>el.dataset.theme=theme', theme)
            colors = await self.page.locator('.sticky-bar').evaluate('''el=>{
                const style=getComputedStyle(el);
                const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
                ctx.fillStyle=style.backgroundColor;ctx.fillRect(0,0,1,1);
                return {image:style.backgroundImage,rgba:[...ctx.getImageData(0,0,1,1).data]};
            }''')
            self.assertEqual(colors['image'], 'none', (theme, colors))
            self.assertEqual(colors['rgba'][3], 255)
            self.assertLessEqual(max(colors['rgba'][:3])-min(colors['rgba'][:3]), 16)

    async def test_radar_cards_keep_counts_close_and_wrap_long_titles(self):
        import tempfile
        from datetime import datetime, timezone
        import fetch_noticias as news
        now = datetime(2026, 10, 28, 13, tzinfo=timezone.utc)
        stories = [{'category':'internacional', 'title':title,
                    'link':f'https://qa.example/radar/{index}',
                    'sources':['A','B','C','D'], 'published':now.isoformat()}
                   for index,title in enumerate(('Una noticia breve',
                     'Un titular internacional extenso que debe conservar su lectura dentro de la tarjeta del radar de cobertura',
                     'Unapalabrasinespacios' * 12))]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, now, folder)
            body = Path(folder, 'index.html').read_text()
        await self.page.route('**/?radar-fixture=1', lambda route: route.fulfill(status=200,content_type='text/html',body=body))
        await self.page.goto(self.url + '?radar-fixture=1')
        for width in (320,390,768,1024,1440,1920,2560):
            await self.page.set_viewport_size({'width':width,'height':1000})
            cards = self.page.locator('.coverage-radar ul > li')
            self.assertEqual(await cards.count(), 3)
            metrics = await cards.evaluate_all('''els=>els.map(el=>{
                const r=el.getBoundingClientRect(),a=el.querySelector('a').getBoundingClientRect(),s=el.querySelector('span').getBoundingClientRect(),css=getComputedStyle(el);
                return {x:r.x,y:r.y,right:r.right,height:r.height,titleX:a.x,titleY:a.y,titleRight:a.right,countX:s.x,countBottom:s.bottom,bg:css.backgroundColor,border:parseFloat(css.borderTopWidth),overflow:el.scrollWidth>el.clientWidth+1};
            })''')
            for card in metrics:
                self.assertEqual(card['border'], 1, (width,metrics))
                self.assertFalse(card['overflow'], (width,metrics))
                self.assertAlmostEqual(card['titleX'],card['countX'],delta=1)
                self.assertGreaterEqual(card['titleY'],card['countBottom'])
                self.assertLessEqual(card['titleY']-card['countBottom'],16)
                self.assertLessEqual(card['titleRight'],card['right'])
            columns = 1 if width < 768 else 2 if width < 1380 else 3
            self.assertEqual(sum(abs(card['y']-metrics[0]['y'])<1 for card in metrics),columns,(width,metrics))
            overflow = await self.page.evaluate('''() => [...document.querySelectorAll('main h2,main h3,main .coverage-radar li')]
                .filter(el=>el.getBoundingClientRect().right>innerWidth+2)
                .map(el=>({tag:el.tagName,cls:el.className,right:el.getBoundingClientRect().right})).slice(0,8)''')
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth+2'), (width,overflow))
        await cards.first.locator('a').focus()
        self.assertTrue(await cards.first.locator('a').evaluate('el=>document.activeElement===el'))
        self.assertIsNone(await cards.first.locator('a').get_attribute('target'))

    async def test_header_is_compact_without_losing_controls(self):
        for width in (320, 390, 768, 1024, 1440, 1920, 2560):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            header = await self.page.locator('.site-header').bounding_box()
            self.assertLessEqual(header['height'], 80 if width < 1024 else 68, (width, header))
            self.assertEqual(await self.page.locator('#menu-toggle').is_visible(), width < 1024, width)
            for selector in ('#theme-toggle','#search-toggle','#site-clock','#refresh-progress','#refresh-now','.edition-count'):
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
        await self.page.locator('#sidebar-edge').click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        await self.page.locator('#theme-toggle').click()
        self.assertIn(await self.page.locator('html').get_attribute('data-theme'), ('light', 'dark'))


if __name__ == '__main__': unittest.main()
