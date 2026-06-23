# api/ichancy.py (نسخة محسنة - جربها)

import json
import logging
from curl_cffi import requests as cf_requests
from config import BASE_URL, AGENT_USERNAME, AGENT_PASSWORD, CURRENCY_CODE, MONEY_STATUS, PARENT_ID

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = AGENT_USERNAME
        self.password = AGENT_PASSWORD
        self.base_url = BASE_URL

        # === ضع الكوكيز الجديدة هنا ===
        self.cookie_string = "PHPSESSID_3a07edcde6f57a008f3251235df79776a424dd7623e40d4250e37e4f1f15fadf=f608cfb6e18a5696ddd1ed6425767567; cf_clearance=p75pkpIrPCEUduL.Np8KXnhZNIjyW3KGTLYq8s_3f7I-1782251181-1.2.1.1-5WXiJLuHO7.MzCxLbgtsxrtnpvR2mQpgIPCUa.9ph.rwy7eY14at3TEQJNvK3c30aGYmQmTpf8rZgQaK_46VkABlZKA15ves.EuU9jR7tJXDUOMwvmEXPxMZJNCSAq0S.l00o96D8C8bUe4I5HOcbxO9g8JXXmyv8A53symubGsVMvhuKh.NxoiTShKwgFH8PyAmPoE9R7vUT8H2Ybvwwx13Zb_8xmb6ECnaax3FDNSwZb0xcrqX59C2j_qKiI_wqxBbmkKnberIBE4u7v3av5ECeMrW.r2ZT9U4IGCIt0sWTqcnnef._Tphj5q7WqTPNPXYjbsfbSrNe_vSdpmlXY.kYuRl6yF0LZj6.26_7qNLNT.sKwGhvrI2X7HKVsn6gtoMLA57sRDABA.1HPAlTYJK8jAgY8PyitoPpt1siZN_M1gZ5psKRHNDQFETe6Wa"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://agents.ichancy.com",
            "Referer": "https://agents.ichancy.com/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def _make_request(self, endpoint: str, body: dict):
        url = self.base_url + endpoint
        auth = (self.username, self.password)

        try:
            response = cf_requests.post(
                url,
                json=body,
                headers=self.headers,
                cookies=self.cookie_string,      # نستخدم الـ string
                auth=auth,
                impersonate="chrome124",
                timeout=30
            )

            logger.info(f"[{endpoint}] Status: {response.status_code} | Body: {response.text[:200]}")

            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"error": response.text}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text[:400]}"}

        except Exception as e:
            logger.error(f"خطأ في {endpoint}: {e}")
            return {"error": str(e)}

    # ==================== الدوال ====================
    async def register_player(self, email, password, login, country="SY"):
        return self._make_request("/Player/registerPlayer", {
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
