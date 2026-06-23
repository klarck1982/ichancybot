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
        self._playwright = None
        self._browser = None
        self._context = None

    async def _get_context(self):
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            )
        return self._context

    async def login(self):
        logger.info("جاري تسجيل الدخول...")
        context = await self._get_context()
        page = await context.new_page()
        try:
            # افتح الموقع الرئيسي وانتظر حل Cloudflare
            await page.goto("https://agents.ichancy.com", wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(6000)

            # أرسل طلب تسجيل الدخول مباشرة عبر الـ fetch في المتصفح
            # بدون محاولة parse النتيجة
            await page.evaluate("""
                async (username, password) => {
                    await fetch('/global/api/User/signIn', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                }
            """, self.username, self.password)

            await page.wait_for_timeout(3000)

            raw_cookies = await context.cookies()
            self.cookies = {c['name']: c['value'] for c in raw_cookies}
            logger.info(f"تم استخراج {len(self.cookies)} كوكيز")
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
        finally:
            await page.close()

    async def _post(self, endpoint: str, body: dict):
        async with self.lock:
            if not self.cookies:
                await self.login()

        # أولاً حاول عبر httpx بالكوكيز
        try:
            async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=body,
                    cookies=self.cookies,
                    auth=(self.username, self.password),
                    headers={
                        "Content-Type": "application/json",
                        "Keep-Alive": "True",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                    }
                )

                if response.status_code in (401, 403):
                    logger.warning(f"مرفوض ({response.status_code})، جاري تجديد الجلسة...")
                    await self.login()
                    # أعد المحاولة عبر Playwright مباشرة
                    return await self._post_via_browser(endpoint, body)

                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    return response.json()
                else:
                    logger.warning(f"رد HTML ({response.status_code})، أحاول عبر المتصفح...")
                    return await self._post_via_browser(endpoint, body)

        except Exception as e:
            logger.error(f"خطأ httpx في {endpoint}: {e}")
            return await self._post_via_browser(endpoint, body)

    async def _post_via_browser(self, endpoint: str, body: dict):
        """إرسال الطلب مباشرة عبر المتصفح لتجاوز Cloudflare"""
        logger.info(f"إرسال {endpoint} عبر المتصفح...")
        context = await self._get_context()
        page = await context.new_page()
        try:
            await page.goto("https://agents.ichancy.com", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            import json
            result = await page.evaluate(f"""
                async (url, body, username, password) => {{
                    const credentials = btoa(username + ':' + password);
                    const res = await fetch(url, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Basic ' + credentials
                        }},
                        body: JSON.stringify(body)
                    }});
                    const text = await res.text();
                    return {{status: res.status, body: text}};
                }}
            """, f"{self.base_url}{endpoint}", body, self.username, self.password)

            logger.info(f"رد المتصفح ({result['status']}): {result['body'][:100]}")

            if result['status'] == 200:
                import json as json_lib
                try:
                    return json_lib.loads(result['body'])
                except:
                    return {"error": result['body']}
            else:
                return {"error": f"HTTP {result['status']}: {result['body'][:200]}"}

        except Exception as e:
            logger.error(f"خطأ في المتصفح {endpoint}: {e}")
            return {"error": str(e)}
        finally:
            await page.close()

    async def register_player(self, email, password, login, country="SY", parent_id=None):
        from config import PARENT_ID
        return await self._post("/Player/registerPlayer", {
            "player": {
                "email": email,
                "password": password,
                "parentId": parent_id or PARENT_ID,
                "login": login,
                "countryCode": country
            }
        })

    async def deposit(self, player_id, amount):
        return await self._post("/Player/depositToPlayer", {
            "amount": amount,
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def withdraw(self, player_id, amount):
        return await self._post("/Player/withdrawFromPlayer", {
            "amount": -abs(amount),
            "playerId": player_id,
            "currencyCode": CURRENCY_CODE,
            "moneyStatus": MONEY_STATUS,
            "comment": None
        })

    async def get_balance(self, player_id):
        return await self._post("/Player/getPlayerBalanceById", {
            "playerId": player_id
        })

    async def get_statistics(self, start=0, limit=10):
        return await self._post("/Statistics/getPlayersStatisticsPro", {
            "start": start,
            "limit": limit,
            "filter": {}
        })

api = IchancyAPI()
