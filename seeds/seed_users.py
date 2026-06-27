"""
Run once to seed 25 fake registered users into MongoDB.
  cd backend && source venv/bin/activate && python seeds/seed_users.py
"""
import asyncio, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import users_col
from services.auth_service import hash_password


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    return digits[-10:] if len(digits) >= 10 else digits


async def seed():
    data = json.loads((Path(__file__).parent / 'users_seed.json').read_text())
    inserted = 0
    skipped = 0

    for u in data:
        if await users_col.find_one({'email': u['email']}):
            skipped += 1
            continue
        await users_col.insert_one({
            'username':         u['username'],
            'email':            u['email'],
            'password':         hash_password(u['password']),
            'phone':            u['phone'],
            'phone_normalized': normalize_phone(u['phone']),
            'avatar_url':       u['avatar_url'],
            'onesignal_player_id': None,
        })
        inserted += 1

    print(f'Seeded {inserted} users, skipped {skipped} duplicates.')


asyncio.run(seed())
