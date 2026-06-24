# v5.1 — httpx + إدارة جلسة + دعم result:false
import logging
from typing import Optional

import httpx

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
    عميل API لـ ichancy100.com مع إدارة جلسة كاملة:
      1. login() على /User/signIn للحصول على الكوكيز
      2. كل الطلبات التالية تستخدم نفس الـ client (يحمل الكوكيز تلقائياً)
      3. إذا انتهت الجلسة (401/403 أو result=false بسبب auth) → re-login + retry

    ملاحظة مهمة:
      الـ API يعيد HTTP 200 حتى عند فشل العملية، مع body مثل:
        {"status":true, "result":false, "notification":[{"code":1,"content":"..."}]}
      لذلك نتحقق من حقل "result" أيضاً.
    """

    LOGIN_ENDPOINT = "/User/signIn"

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self._client: Optional[httpx.AsyncClient] = None
        self._logged_in: bool = False

    # ---------- إدارة الـ client ----------
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _reset_client(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
        self._client = None
        self._logged_in = False

    async def close(self) -> None:
        await self._reset_client()
        logger.info("🔌 API client closed")

    # ---------- تسجيل الدخول ----------
    async def login(self) -> dict:
        client = await self._get_client()
        url = f"{self.base_url}{self.LOGIN_ENDPOINT}"
        try:
            r = await client.post(
                url,
                json={
                    "username": self.username,
                    "password": self.password,
                },
            )
            logger.info(f"🔐 Login → {r.status_code} | {r.text[:200]}")

            if r.status_code not in (200, 201):
                return {
                    "error": f"Login HTTP failed: {r.status_code}: {r.text[:300]}"
                }

            # تحليل الاستجابة
            try:
                data = r.json()
            except ValueError:
                return {"error": f"Invalid login JSON: {r.text[:200]}"}

            # الـ API قد يعيد HTTP 200 مع result:false
            if isinstance(data, dict) and data.get("result") is False:
                self._logged_in = False
                msg = self._extract_notifications(data)
                return {"error": f"Login failed: {msg or 'invalid credentials'}"}

            self._logged_in = True
            cookies = {c.name: c.value for c in client.cookies.jar}
            logger.info(
                f"🍪 Cookies received: {list(cookies.keys()) or '(none)'}"
            )
            return {"ok": True, "cookies": cookies}

        except httpx.TimeoutException:
            logger.error("⏱️ Login timed out")
            return {"error": "Login timed out"}
        except httpx.RequestError as e:
            logger.error(f"❌ Login network error: {e}")
            return {"error": f"Login network error: {e}"}
        except Exception as e:
            logger.error(f"❌ Unexpected login error: {e}")
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
        client = await self._get_client()
        url = f"{self.base_url}{endpoint}"
        try:
            r = await client.post(url, json=body)
            logger.info(
                f"📤 POST {endpoint} → {r.status_code} | {r.text[:200]}"
            )

            if r.status_code in (200, 201):
                return self._parse_response(endpoint, r)

            # انتهاء الجلسة عبر HTTP
            if r.status_code in (401, 403):
                logger.warning(
                    f"⚠️ Session expired on {endpoint} (HTTP {r.status_code}), re-logging in..."
                )
                return await self._retry_with_relogin(endpoint, body)

            return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}

        except httpx.TimeoutException:
            logger.error(f"⏱️ Timeout {endpoint}")
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            logger.error(f"❌ Network error {endpoint}: {e}")
            return {"error": f"Network error: {e}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error {endpoint}: {e}")
            return {"error": str(e)}

    async def _retry_with_relogin(self, endpoint: str, body: dict) -> dict:
        """إعادة المحاولة بعد تسجيل دخول جديد (مرة واحدة فقط)."""
        await self._reset_client()
        lr = await self.login()
        if "error" in lr:
            return lr
        return await self._do_post(endpoint, body)

    # ---------- تحليل الاستجابة ----------
    def _parse_response(self, endpoint: str, response: httpx.Response) -> dict:
        """
        تحليل استجابة الـ API. الـ API يعيد HTTP 200 دائماً تقريباً، حتى عند
        فشل العملية، مع body مثل:
          {"status":true, "result":false, "notification":[{"content":"..."}]}
        نُحوّل result:false إلى {"error":...} ليتوافق مع توقعات الـ handlers.
        """
        try:
            data = response.json()
        except ValueError:
            return {"error": f"Invalid JSON from {endpoint}: {response.text[:200]}"}

        if not isinstance(data, dict):
            return data

        # فشل العملية → أعد {"error":..., "_raw":...}
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
        """استخراج رسائل الخطأ من notification array."""
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
