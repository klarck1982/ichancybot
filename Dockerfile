# api/ichancy.py - Camoufox (النسخة النهائية)

import json
import logging
from camoufox.async_api import AsyncCamoufox
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS, PARENT_ID

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL
        self.browser = None
        self.page = None

    async def _init_browser(self):
        if self.page:
            return

        self.browser = await AsyncCamoufox(
            headless=True,
            geoip=True,
            humanize=True,
            locale="en-US",
            os="windows",
        ).start()

        context = await self.browser.new_context()
        self.page = await context.new_page()

        # الدخول للموقع
        await self.page.goto("https://agents.ichancy.com", timeout=120000)
        await self.page.wait_for_timeout(8000)

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
        await self.page.wait_for_timeout(4000)
        logger.info("✅ Camoufox جاهز")

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

            logger.info(f"[{endpoint}] Status: {result['status']}")

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

    async def deposit(self, player_id, amount): ...
    async def withdraw(self, player_id, amount): ...
    async def get_balance(self, player_id): ...
    async def get_statistics(self, start=0, limit=10): ...


api = IchancyAPI()
