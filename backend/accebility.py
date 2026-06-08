import asyncio
import json
from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def init_browser(self):
        async with self._lock:
            if not self.browser:
                # تشغيل Playwright وفتح متصفح كروميوم
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=False)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            elif self.page.is_closed(): 
                self.page = await self.context.new_page()
            return self.page

    async def close_all(self):
        if self.playwright:
            await self.playwright.stop()

async def main():
    # إنشاء نسخة من مدير المتصفح
    browser_manager = BrowserManager()
    
    try:
        # 1. تهيئة الصفحة
        page = await browser_manager.init_browser()
        
        # 2. الانتقال إلى الموقع المطلوب
        target_url = "http://localhost:7061/Product/Product"
        print(f"Navigating to: {target_url} ...")
        await page.goto(target_url, wait_until="domcontentloaded")
        
        # الانتظار قليلاً للتأكد من تحميل العناصر التفاعلية
        await asyncio.sleep(2)

        # 3. استخراج شجرة الوصول باستخدام CDP (الحل البديل والأقوى)
        print("Capturing Accessibility Tree via CDP Session...")
        
        # إنشاء جلسة بروتوكول أدوات المطور
        cdp_session = await page.context.new_cdp_session(page)
        
        # طلب شجرة الوصول الكاملة (Full Accessibility Tree)
        # هذا الأمر يعيد هيكلية الصفحة الدلالية بالكامل
        result = await cdp_session.send("Accessibility.getFullAXTree")
        
        # 4. عرض النتائج بشكل منظم
        print("\n" + "="*50)
        print("ACCESSIBILITY TREE CAPTURED SUCCESSFULLY")
        print("="*50)
        
        # طباعة أول 5 عناصر كمثال للتأكد من العمل (لأن الشجرة قد تكون ضخمة)
        nodes = result.get("nodes", [])
        print(f"Found {len(nodes)} semantic nodes in the tree.\n")
        
        # طباعة البيانات بتنسيق JSON مقروء
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000] + "...\n[Output Truncated for Readability]")
        
        print("="*50)

    except Exception as e:
        print(f"\n[!] An error occurred: {e}")
    
    finally:
        # 5. إغلاق المتصفح تماماً لتوفير الموارد
        print("\nClosing browser...")
        await browser_manager.close_all()

if __name__ == "__main__":
    # تشغيل الحدث الرئيسي
    asyncio.run(main())