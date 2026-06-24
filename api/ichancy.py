import httpx
import asyncio
import logging
import json
from playwright.async_api import async_playwright
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS, PARENT_ID

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL

    async def _run_in_browser(self, endpoint, body):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto("https://agents.ichancy.com", wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(5000)

                # تسجيل الدخول — تمرير المتغيرات عبر injection آمن
                login_script = f"""
                    (async () => {{
                        await fetch('/global/api/User/signIn', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{username: {json.dumps(self.username)}, password: {json.dumps(self.password)}}})
                        }});
                    }})()
                """
                await page.evaluate(login_script, None)
                await page.wait_for_timeout(2000)

                # الطلب الفعلي
                url = self.base_url + endpoint
                credentials = f"{self.username}:{self.password}"
                import base64
                b64 = base64.b64encode(credentials.encode()).decode()

                request_script = f"""
                    (async () => {{
                        const res = await fetch({json.dumps(url)}, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Authorization': 'Basic {b64}'
                            }},
                            body: JSON.stringify({json.dumps(body)})
                        }});
                        return {{status: res.status, body: await res.text()}};
                    }})()
                """
                result = await page.evaluate(request_script, None)
                logger.info(f"رد {endpoint} ({result['status']}): {result['body'][:300]}")

                if result['status'] == 200:
                    try:
                        return json.loads(result['body'])
                    except:
                        return {"error": result['body']}
                else:
                    return {"error": f"HTTP {result['status']}: {result['body'][:300]}"}

            except Exception as e:
                logger.error(f"خطأ في المتصفح {endpoint}: {e}")
                return {"error": str(e)}
            finally:
                await browser.close()

    async def login(self):
        pass

    async def register_player(self, email, password, login, country="SY"):
        return await self._run_in_browser("/Player/registerPlayer", {
            "player": {
                "email": email,
                "password": password,
                "parentId": PARENT_ID,
                "login": login,
                "countryCode": country
            }
        })

    async def deposit(self, player_id, amount):
        return await self._run_in_browser("/Player/depositToPlayer", {
            "amount": amount,
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def withdraw(self, player_id, amount):
        return await self._run_in_browser("/Player/withdrawFromPlayer", {
            "amount": -abs(amount),
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def get_balance(self, player_id):
        return await self._run_in_browser("/Player/getPlayerBalanceById", {
            "playerId": player_id
        })

    async def get_statistics(self, start=0, limit=10):
        return await self._run_in_browser("/Statistics/getPlayersStatisticsPro", {
            "start": start,
            "limit": limit,
            "filter": {}
        })

api = IchancyAPI()
