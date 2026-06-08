# browser_manager.py

import asyncio
from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def init_browser(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

        elif self.page.is_closed():
            self.page = await self.context.new_page()

        return self.page


browser = BrowserManager()

status_store = {
    "status": "idle",
    "step": "",
    "message": ""
}