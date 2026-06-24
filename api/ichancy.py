#v3
import asyncio
import logging
import json
import base64
import os
from playwright.async_api import async_playwright
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS, PARENT_ID

logger = logging.getLogger(__name__)

PROXY_SERVER = os.getenv("PROXY_SERVER", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL

    def _get_proxy(self):
        if not PROXY_SERVER:
            return None
        proxy = {"server": PROXY_SERVER}
        if PROXY_USER:
            proxy["username"] = PROXY_USER
        if PROXY_PASS:
            proxy["password"] = PROXY_PASS
        return proxy

    async def _wait_for_cloudflare(self, page):
        """انتظر حتى تختفي صفحة Cloudflare تماماً"""
        for i in range(20):  # انتظر حتى 20 ثانية
            title = await page.title()
            logger.info(f"عنوان الصفحة ({i+1}): {title}")
            if "Just a moment" not in title and "Cloudflare" not in title:
                logger.info("✅ تم تجاوز Cloudflare")
                return True
            await page.wait_for_timeout(1000)
        logger.warning("⚠️ انتهى وقت انتظار Cloudflare")
        return False

    async def _run_in_browser(self, endpoint, body):
        proxy = self._get_proxy()
        async with async_playwright() as p:
            launch_args = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            }
            if proxy:
                launch_args["proxy"] = proxy
                logger.info(f"استخدام البروكسي: {PROXY_SERVER}")

            browser = await p.chromium.launch(**launch_args)
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 720},
                "java_script_enabled": True,
            }
            if proxy:
                context_args["proxy"] = proxy

            context = await browser.new_context(**context_args)

            # إخفاء علامات Playwright
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ar', 'en-US']});
            """)

            page = await context.new_page()
            try:
                await page.goto("https://agents.ichancy.com", wait_until="domcontentloaded", timeout=60000)

                # انتظر حتى تختفي صفحة Cloudflare
                passed = await self._wait_for_cloudflare(page)
                if not passed:
                    return {"error": "Cloudflare blocking - proxy not working"}

                await page.wait_for_timeout(1000)

                # تسجيل الدخول
                login_script = f"(async()=>{{await fetch('/global/api/User/signIn',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:{json.dumps(self.username)},password:{json.dumps(self.password)}}})}})}})()"
                await page.evaluate(login_script, None)
                await page.wait_for_timeout(1500)

                # الطلب الفعلي
                b64 = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                url = self.base_url + endpoint
                req_script = f"(async()=>{{const r=await fetch({json.dumps(url)},{{method:'POST',headers:{{'Content-Type':'application/json','Authorization':'Basic {b64}'}},body:JSON.stringify({json.dumps(body)})}});return{{status:r.status,body:await r.text()}}}})() "
                result = await page.evaluate(req_script, None)

                logger.info(f"رد {endpoint} ({result['status']}): {result['body'][:300]}")

                if result['status'] == 200:
                    try:
                        return json.loads(result['body'])
                    except:
                        return {"error": result['body']}
                else:
                    return {"error": f"HTTP {result['status']}: {result['body'][:300]}"}

            except Exception as e:
                logger.error(f"خطأ {endpoint}: {e}")
                return {"error": str(e)}
            finally:
                await browser.close()

    async def login(self): pass

    async def register_player(self, email, password, login, country="SY"):
        return await self._run_in_browser("/Player/registerPlayer", {
            "player": {"email": email, "password": password, "parentId": PARENT_ID, "login": login, "countryCode": country}
        })

    async def deposit(self, player_id, amount):
        return await self._run_in_browser("/Player/depositToPlayer", {
            "amount": amount, "playerId": player_id, "currencyCode": CURRENCY_CODE, "moneyStatus": MONEY_STATUS, "comment": None
        })

    async def withdraw(self, player_id, amount):
        return await self._run_in_browser("/Player/withdrawFromPlayer", {
            "amount": -abs(amount), "playerId": player_id, "currencyCode": CURRENCY_CODE, "moneyStatus": MONEY_STATUS, "comment": None
        })

    async def get_balance(self, player_id):
        return await self._run_in_browser("/Player/getPlayerBalanceById", {"playerId": player_id})

    async def get_statistics(self, start=0, limit=10):
        return await self._run_in_browser("/Statistics/getPlayersStatisticsPro", {"start": start, "limit": limit, "filter": {}})

api = IchancyAPI()
