# v6 — curl_cffi (يقلّد Chrome لتجاوز Cloudflare) + إدارة جلسة كاملة
import logging
from typing import Optional

from curl_cffi.requests import AsyncSession

from config import (
    BASE_URL,
    AGENT_USERNAME,
    AGENT_PASSWORD,
    CURRENCY_CODE,
    MONEY_STATUS,
    PARENT_ID,
    HTTP_TIMEOUT,
)

logger = logging.getLogger(__name__)


class IchancyAPI:
    """
    عميل API لـ ichancy100.com مع إدارة جلسة كاملة + تجاوز Cloudflare.

    لماذا curl_cffi بدل httpx؟
    ─────────────────────────
    الداشبورد محمي بـ Cloudflare. Cloudflare يفحص بصمة TLS للمتصفح (JA3/JA4)
    وليس فقط الـ headers. httpx يفشل → 403 Forbidden (صفحة تحدي).
    curl_cffi يقلّد بصمة Chrome الحقيقية → يتجاوز الفحص.

    آلية العمل:
    ──────────
    1. login() على /User/signIn للحصول على كوكيز الجلسة
    2. كل الطلبات التالية تستخدم نفس الـ session (يحمل الكوكيز تلقائياً)
    3. إذا انتهت الجلسة (401/403 أو result=false بسبب auth) → re-login + retry
    """

    LOGIN_ENDPOINT = "/User/signIn"
    DASHBOARD_URL = "https://agents.ichancy100.com/"

    # Headers التي تجعل الطلب يبدو كمتصفح حقيقي
    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Origin": "https://agents.ichancy100.com",
        "Referer": "https://agents.ichancy100.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self._session: Optional[AsyncSession] = None
        self._logged_in: bool = False

    # ---------- إدارة الـ session ----------
    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(
                impersonate="chrome124",  # يقلّد بصمة TLS لمتصفح Chrome 124
                timeout=HTTP_TIMEOUT,
                headers=self.DEFAULT_HEADERS,
            )
        return self._session

    async def _reset_session(self) -> None:
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
        self._session = None
        self._logged_in = False

    async def close(self) -> None:
        await self._reset_session()
        logger.info("🔌 API session closed")

    # ---------- تسجيل الدخول ----------
    async def login(self) -> dict:
        session = await self._get_session()
        url = f"{self.base_url}{self.LOGIN_ENDPOINT}"
        try:
            # 1. زيارة الصفحة الرئيسية أولاً (للحصول على __cf_bm)
            try:
                warmup = await session.get(self.DASHBOARD_URL)
                logger.info(f"🔥 Warmup GET / → {warmup.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Warmup failed (continuing): {e}")

            # 2. تسجيل الدخول
            r = await session.post(
                url,
                json={
                    "username": self.username,
                    "password": self.password,
                },
            )
            logger.info(f"🔐 Login → {r.status_code} | {r.text[:200]}")

            if r.status_code not in (200, 201):
                return {
                    "error": f"Login HTTP failed: {r.status_code}: {r.text[:200]}"
                }

            try:
                data = r.json()
            except ValueError:
                return {"error": f"Invalid login JSON: {r.text[:200]}"}

            if isinstance(data, dict) and data.get("result") is False:
                self._logged_in = False
                msg = self._extract_notifications(data)
                return {"error": f"Login failed: {msg or 'invalid credentials'}"}

            self._logged_in = True
            cookies = {c: session.cookies.get(c) for c in session.cookies.keys()}
            logger.info(
                f"🍪 Cookies: {list(cookies.keys()) or '(none)'}"
            )
            return {"ok": True, "cookies": cookies}

        except Exception as e:
            logger.error(f"❌ Login error: {type(e).__name__}: {e}")
            return {"error": str(e)}

    async def _ensure_login(self) -> dict:
        if self._logged_in:
            return {"ok": True}
        return await self.login()

    # ---------- تنفيذ الطلب ----------
    async def _request(self, endpoint: str, body: dict) -> dict:
        lr = await self._ensure_login()
        if "error" in lr:
            return lr

        return await self._do_post(endpoint, body)

    async def _do_post(self, endpoint: str, body: dict) -> dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        try:
            r = await session.post(url, json=body)
            logger.info(
                f"📤 POST {endpoint} → {r.status_code} | {r.text[:200]}"
            )

            if r.status_code in (200, 201):
                return self._parse_response(endpoint, r)

            if r.status_code in (401, 403):
                logger.warning(
                    f"⚠️ Session expired on {endpoint} (HTTP {r.status_code}), re-logging in..."
                )
                return await self._retry_with_relogin(endpoint, body)

            return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}

        except Exception as e:
            logger.error(f"❌ {endpoint} error: {type(e).__name__}: {e}")
            return {"error": str(e)}

    async def _retry_with_relogin(self, endpoint: str, body: dict) -> dict:
        await self._reset_session()
        lr = await self.login()
        if "error" in lr:
            return lr
        return await self._do_post(endpoint, body)

    # ---------- تحليل الاستجابة ----------
    def _parse_response(self, endpoint: str, response) -> dict:
        try:
            data = response.json()
        except ValueError:
            return {"error": f"Invalid JSON from {endpoint}: {response.text[:200]}"}

        if not isinstance(data, dict):
            return data

        if data.get("result") is False:
            msg = self._extract_notifications(data)
            logger.warning(f"⚠️ {endpoint} failed: {msg or 'result=false'}")
            return {
                "error": msg or f"{endpoint} failed",
                "_raw": data,
            }

        return data

    @staticmethod
    def _extract_notifications(data: dict) -> str:
        notifications = data.get("notification") or []
        if isinstance(notifications, list) and notifications:
            return "; ".join(
                str(n.get("content", ""))
                for n in notifications
                if isinstance(n, dict)
            )
        return ""

    # ---------- العمليات ----------
    async def register_player(
        self, email: str, password: str, login: str, country: str = "SY"
    ) -> dict:
        return await self._request(
            "/Player/registerPlayer",
            {
                "player": {
                    "email": email,
                    "password": password,
                    "parentId": PARENT_ID,
                    "login": login,
                    "countryCode": country,
                }
            },
        )

    async def deposit(self, player_id, amount) -> dict:
        return await self._request(
            "/Player/depositToPlayer",
            {
                "amount": amount,
                "playerId": player_id,
                "currencyCode": CURRENCY_CODE,
                "moneyStatus": MONEY_STATUS,
                "comment": None,
            },
        )

    async def withdraw(self, player_id, amount) -> dict:
        return await self._request(
            "/Player/withdrawFromPlayer",
            {
                "amount": -abs(amount),
                "playerId": player_id,
                "currencyCode": CURRENCY_CODE,
                "moneyStatus": MONEY_STATUS,
                "comment": None,
            },
        )

    async def get_balance(self, player_id) -> dict:
        return await self._request(
            "/Player/getPlayerBalanceById",
            {"playerId": player_id},
        )

    async def get_statistics(self, start: int = 0, limit: int = 10) -> dict:
        return await self._request(
            "/Statistics/getPlayersStatisticsPro",
            {"start": start, "limit": limit, "filter": {}},
        )


# Singleton
api = IchancyAPI()
