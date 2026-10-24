"""Checks against the real generated document and Chromium; run explicitly."""
import asyncio
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
        await self.page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        self.assertEqual(await self.page.locator('html').get_attribute('data-theme'), 'dark')
        await self.page.locator('#view-options-toggle').click()
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

    async def test_carousel_next_previous_and_keyboard(self):
        track = self.page.locator('.breaking-track')
        self.assertGreaterEqual(await track.locator('a').count(), 3)
        await self.page.locator('[data-carousel-next]').click()
        await self.page.wait_for_function("document.querySelector('.breaking-track').scrollLeft > 10")
        await self.page.locator('[data-carousel-prev]').click()
        await self.page.wait_for_function("document.querySelector('.breaking-track').scrollLeft < 2")
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
            for figure in await self.page.locator('.media--source:not(.media--date)').all():
                self.assertFalse(await figure.is_visible())
        ARTIFACTS.mkdir(exist_ok=True)
        for theme in ('light', 'dark'):
            await self.page.emulate_media(color_scheme=theme)
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

    async def test_blocked_storage_does_not_disable_controls(self):
        await self.context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked')}})")
        await self.page.reload()
        await self.page.locator('#menu-toggle').click()
        self.assertFalse(await self.page.locator('#site-nav').is_visible())
        await self.page.locator('#theme-toggle').click()
        self.assertIn(await self.page.locator('html').get_attribute('data-theme'), ('light', 'dark'))


if __name__ == '__main__': unittest.main()
