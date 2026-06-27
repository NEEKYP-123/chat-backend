from fastapi import APIRouter, Header, HTTPException
from database import contacts_col, users_col
from models.contact import AddContactRequest
from services.auth_service import decode_token, hash_password
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import httpx, re

class SyncContactsRequest(BaseModel):
    contacts: List[dict]  # [{"name": "...", "phone": "...", "email": "..."}]

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    return digits[-10:] if len(digits) >= 10 else digits

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

def _fmt(c: dict) -> dict:
    return {
        "id": str(c["_id"]),
        "name": c["name"],
        "phone": c.get("phone"),
        "email": c.get("email"),
        "user_id": c.get("user_id"),
        "avatar_url": c.get("avatar_url"),
        "created_at": c["created_at"].isoformat(),
    }

@router.get("/")
async def get_contacts(authorization: str = Header(...), q: str = ""):
    owner_id = get_user_id(authorization)
    query = {"owner_id": owner_id}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    cursor = contacts_col.find(query).sort("name", 1)
    return [_fmt(c) async for c in cursor]

@router.post("/")
async def add_contact(body: AddContactRequest, authorization: str = Header(...)):
    owner_id = get_user_id(authorization)

    if not body.phone and not body.email:
        raise HTTPException(status_code=400, detail="Provide phone or email")

    matched_user = None
    normalized = None
    if body.phone:
        normalized = _normalize_phone(body.phone)
        matched_user = await users_col.find_one({"phone_normalized": normalized})
    if not matched_user and body.email:
        matched_user = await users_col.find_one({"email": body.email})

    contact = {
        "owner_id":        owner_id,
        "name":            body.name,
        "phone":           body.phone,
        "phone_normalized": normalized,
        "email":           body.email,
        "user_id":         str(matched_user["_id"]) if matched_user else None,
        "avatar_url":      matched_user.get("avatar_url") if matched_user else None,
        "created_at":      datetime.utcnow(),
    }
    result = await contacts_col.insert_one(contact)
    contact["_id"] = result.inserted_id
    return _fmt(contact)

@router.post("/sync")
async def sync_contacts(body: SyncContactsRequest, authorization: str = Header(...)):
    owner_id = get_user_id(authorization)

    # Build a map of phone_normalized -> registered user for fast lookup
    phone_to_user = {}
    async for user in users_col.find({"phone_normalized": {"$exists": True}}):
        phone_to_user[user["phone_normalized"]] = user

    upserted = 0
    for c in body.contacts:
        name = (c.get("name") or "").strip()
        raw_phone = (c.get("phone") or "").strip() or None
        email = (c.get("email") or "").strip() or None

        if not name or not raw_phone:
            continue

        normalized = _normalize_phone(raw_phone)

        # match against registered users by normalized phone, fall back to email
        matched_user = phone_to_user.get(normalized)
        if not matched_user and email:
            matched_user = await users_col.find_one({"email": email})

        user_id = str(matched_user["_id"]) if matched_user else None
        avatar_url = matched_user.get("avatar_url") if matched_user else None

        # upsert: update existing or insert new
        await contacts_col.update_one(
            {"owner_id": owner_id, "phone_normalized": normalized},
            {"$set": {
                "owner_id":       owner_id,
                "name":           name,
                "phone":          raw_phone,
                "phone_normalized": normalized,
                "email":          email,
                "user_id":        user_id,
                "avatar_url":     avatar_url,
                "updated_at":     datetime.utcnow(),
            }, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )
        upserted += 1

    # count how many of those are actual app users
    matched = await contacts_col.count_documents(
        {"owner_id": owner_id, "user_id": {"$ne": None}}
    )
    return {"synced": upserted, "matched": matched}

@router.post("/sync-random")
async def sync_random_contacts(authorization: str = Header(...)):
    """Clear existing contacts, fetch fresh random users from randomuser.me, seed and add them."""
    owner_id = get_user_id(authorization)

    # wipe all existing contacts for this user so phone contacts don't bleed through
    await contacts_col.delete_many({"owner_id": owner_id})

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://randomuser.me/api/", params={"results": 10})
        resp.raise_for_status()
        random_users = resp.json()["results"]

    saved = 0
    for ru in random_users:
        name = f"{ru['name']['first']} {ru['name']['last']}"
        email = ru["email"]
        phone = ru["phone"]
        avatar_url = ru["picture"]["thumbnail"]

        existing_user = await users_col.find_one({"email": email})
        if existing_user:
            user_id = str(existing_user["_id"])
        else:
            result = await users_col.insert_one({
                "username": ru["login"]["username"],
                "email": email,
                "password": hash_password(ru["login"]["password"]),
                "avatar_url": avatar_url,
                "onesignal_player_id": None,
            })
            user_id = str(result.inserted_id)

        await contacts_col.insert_one({
            "owner_id": owner_id,
            "name": name,
            "phone": phone,
            "email": email,
            "user_id": user_id,
            "avatar_url": avatar_url,
            "created_at": datetime.utcnow(),
        })
        saved += 1

    return {"synced": saved}


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, authorization: str = Header(...)):
    owner_id = get_user_id(authorization)
    result = await contacts_col.delete_one(
        {"_id": ObjectId(contact_id), "owner_id": owner_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"deleted": True}
