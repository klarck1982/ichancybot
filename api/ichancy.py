import httpx
import asyncio
import logging
from playwright.async_api import async_playwright
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL
        self.cookies = {}
        self.lock = asyncio.Lock()

    async def login(self):
        logger.info("جاري تسجيل الدخول وحل Cloudflare...")
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
                await page.goto("https://agents.ichancy.com", wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(4000)

                # تسجيل الدخول عبر fetch داخل المتصفح
                result = await page.evaluate(f"""
                    async () => {{
                        const res = await fetch('/global/api/User/signIn', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                username: '{self.username}',
                                password: '{self.password}'
                            }})
                        }});
                        return await res.json();
                    }}
                """)
                logger.info(f"نتيجة تسجيل الدخول: {result}")
                await page.wait_for_timeout(2000)

                raw_cookies = await context.cookies()
                self.cookies = {c['name']: c['value'] for c in raw_cookies}
                logger.info(f"تم استخراج {len(self.cookies)} كوكيز")
            except Exception as e:
                logger.error(f"خطأ في تسجيل الدخول: {e}")
            finally:
                await browser.close()

    async def _post(self, endpoint: str, body: dict):
        async with self.lock:
            if not self.cookies:
                await self.login()

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=body,
                    cookies=self.cookies,
                    auth=(self.username, self.password),
                    headers={
                        "Content-Type": "application/json",
                        "Keep-Alive": "True"
                    }
                )
                if response.status_code in (401, 403):
                    logger.warning("الجلسة انتهت، جاري التجديد...")
                    await self.login()
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        json=body,
                        cookies=self.cookies,
                        auth=(self.username, self.password),
                        headers={"Content-Type": "application/json", "Keep-Alive": "True"}
                    )
                return response.json()
        except Exception as e:
            logger.error(f"خطأ في الطلب {endpoint}: {e}")
            return {"error": str(e)}

    async def register_player(self, email: str, password: str, login: str, country: str = "SY", parent_id: str = "2751155"):
        return await self._post("/Player/registerPlayer", {
            "player": {
                "email": email,
                "password": password,
                "parentId": parent_id,
                "login": login,
                "countryCode": country
            }
        })

    async def deposit(self, player_id: str, amount: float):
        return await self._post("/Player/depositToPlayer", {
            "amount": amount,
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def withdraw(self, player_id: str, amount: float):
        return await self._post("/Player/withdrawFromPlayer", {
            "amount": -abs(amount),
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def get_balance(self, player_id: str):
        return await self._post("/Player/getPlayerBalanceById", {
            "playerId": player_id
        })

    async def get_statistics(self, start: int = 0, limit: int = 10):
        return await self._post("/Statistics/getPlayersStatisticsPro", {
            "start": start,
            "limit": limit,
            "filter": {}
        })

# singleton
api = IchancyAPI()
