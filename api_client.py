import aiohttp
from config import PLAYER_INFO_API_URL, LIKE_API_URL, LIKE_API_KEY


class APIConfigurationError(Exception):
    pass


async def player_info(uid, server):
    if not PLAYER_INFO_API_URL:
        raise APIConfigurationError("PLAYER_INFO_API_URL সেট করুন।")
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(PLAYER_INFO_API_URL, params={"uid": uid, "region": server}) as response:
            data = await response.json(content_type=None)
            if response.status != 200:
                raise RuntimeError(f"Player API HTTP {response.status}")
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    if not isinstance(data, dict) or not data.get("uid"):
        raise RuntimeError("Player API response-এ UID পাওয়া যায়নি।")
    return data


async def send_likes(uid, server):
    # Provider contract: POST JSON {"key": ..., "uid": ...}.
    if not LIKE_API_URL or not LIKE_API_KEY:
        raise APIConfigurationError("LIKE_API_URL এবং LIKE_API_KEY Environment Variables-এ সেট করুন।")
    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            LIKE_API_URL,
            json={"key": LIKE_API_KEY, "uid": str(uid)},
            headers={"Content-Type": "application/json"},
        ) as response:
            try:
                data = await response.json(content_type=None)
            except Exception as exc:
                raise RuntimeError(f"Like API valid JSON দেয়নি (HTTP {response.status})") from exc
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Like API HTTP {response.status}: {data}")
    if not isinstance(data, dict):
        raise RuntimeError("Like API response format সঠিক নয়।")
    # API's documented response is top-level {ok, likes, charged, balance}.
    return data
