# api/ichancy.py - باستخدام Camoufox (أقوى حل حالياً)

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
        self.context = None
        self.page = None

    async def _init_camoufox(self):
        """تهيئة Camoufox مع أقصى حماية"""
        if self.page:
            return

        self.browser = await AsyncCamoufox(
            headless=True,
            geoip=True,                    # مهم جداً
            humanize=True,                 # سلوك بشري
            locale="en-US",
        ).start()

        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # تسجيل الدخول
        await self.page.goto("https://agents.ichancy.com", timeout=90000)
        await self.page.wait_for_timeout(5000)

        # تسجيل الدخول عبر fetch
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
        logger.info("✅ تم تسجيل الدخول بـ Camoufox")

    async def _make_request(self, endpoint: str, body: dict):
        await self._init_camoufox()

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
            # إعادة تهيئة في حال الفشل
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

    async def deposit(self, player_id, amount):
        return await self._make_request("/Player/depositToPlayer", {
            "amount": amount,
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def withdraw(self, player_id, amount):
        return await self._make_request("/Player/withdrawFromPlayer", {
            "amount": -abs(amount),
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def get_balance(self, player_id):
        return await self._make_request("/Player/getPlayerBalanceById", {
            "playerId": player_id
        })

    async def get_statistics(self, start=0, limit=10):
        return await self._make_request("/Statistics/getPlayersStatisticsPro", {
            "start": start,
            "limit": limit,
            "filter": {}
        })


api = IchancyAPI()
