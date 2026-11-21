import asyncio

from playwright.async_api import async_playwright

import config


class BrowserManager:
    """Owns one shared Chromium page that all tools act on."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def init_browser(self):
        async with self._lock:
            if not self.browser:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=config.HEADLESS)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            elif self.page.is_closed():
                self.page = await self.context.new_page()
            return self.page

    async def close(self):
        async with self._lock:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.playwright = self.browser = self.context = self.page = None


browser = BrowserManager()

# Polled by the Chrome extension through GET /status.
status_store = {"status": "idle", "step": "", "message": ""}
