import httpx
from config import ONESIGNAL_APP_ID, ONESIGNAL_API_KEY

ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"

async def send_push(player_ids: list[str], title: str, body: str, data: dict = {}):
    if not player_ids:
        return

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "include_player_ids": player_ids,
        "headings": {"en": title},
        "contents": {"en": body},
        "data": data,
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            ONESIGNAL_URL,
            json=payload,
            headers={
                "Authorization": f"Basic {ONESIGNAL_API_KEY}",
                "Content-Type": "application/json",
            },
        )
