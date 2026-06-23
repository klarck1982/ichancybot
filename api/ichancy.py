# api/ichancy.py - نسخة Railway (rebrowser-patches)

import json
import logging
from playwright.async_api import async_playwright
from rebrowser_patches.async_api import patch_playwright
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS, PARENT_ID

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL
        self.page = None

    async def _init_browser(self):
        if self.page:
            return

        patched_playwright = await patch_playwright(async_playwright()).start()

        browser = await patched_playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US",
        )

        self.page = await context.new_page()

        # الدخول للموقع
        await self.page.goto("https://agents.ichancy.com", timeout=90000)
        await self.page.wait_for_timeout(6000)

        # تسجيل الدخول
        await self.page.evaluate(f"""
            fetch('/global/api/User/signIn', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    username: {json.dumps(self.username)},
                    password: {json.dumps(self.password)}
                }})
            }})
        """)
        await self.page.wait_for_timeout(3000)
        logger.info("✅ تم تشغيل rebrowser-patches بنجاح")

    async def _make_request(self, endpoint: str, body: dict):
        await self._init_browser()

        url = self.base_url + endpoint

        try:
            result = await self.page.evaluate(f"""
                (async () => {{
                    const res = await fetch("{url}", {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Basic ' + btoa("{self.username}:{self.password}")
                        }},
                        body: JSON.stringify({json.dumps(body)})
                    }});
                    return {{status: res.status, text: await res.text()}};
                }})()
            """)

            if result['status'] == 200:
                try:
                    return json.loads(result['text'])
                except:
                    return {"error": result['text']}
            else:
                return {"error": f"HTTP {result['status']}: {result['text'][:300]}"}

        except Exception as e:
            logger.error(f"خطأ في {endpoint}: {e}")
            self.page = None
            return {"error": str(e)}

    # ==================== الدوال ====================
    async def register_player(self, email, password, login, country="SY"):
        return await self._make_request("/Player/registerPlayer", {
            "player": {
                "email": email,
                "password": password,
                "parentId": PARENT_ID,
                "login": login,
                "countryCode": country
            }
        })

    async def deposit(self, player_id, amount): ...  # نفس الدوال السابقة
    async def withdraw(self, player_id, amount): ...
    async def get_balance(self, player_id): ...
    async def get_statistics(self, start=0, limit=10): ...


api = IchancyAPI()
