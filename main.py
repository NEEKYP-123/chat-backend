from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import messages_col, users_col, rooms_col
from routes import auth, rooms, messages, upload, contacts, ai, users, stories
from websocket.manager import manager
from services.auth_service import decode_token
from services.notification_service import send_push
from datetime import datetime
from bson import ObjectId

app = FastAPI(title="Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(messages.router)
app.include_router(upload.router)
app.include_router(contacts.router)
app.include_router(ai.router)
app.include_router(users.router)
app.include_router(stories.router)

@app.get("/")
async def root():
    return {"status": "Chat API running"}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str, token: str):
    user_id = decode_token(token)
    if not user_id:
        await ws.close(code=1008)
        return

    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        await ws.close(code=1008)
        return

    await manager.connect(room_id, ws, user_id)

    # Broadcast online status to room
    await manager.broadcast(room_id, {
        "type": "status",
        "user_id": user_id,
        "online": True,
    }, exclude=ws)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "text")

            # ── Call signaling ────────────────────────────────────────────
            if msg_type in ("call_invite", "call_accept", "call_reject", "call_end"):
                await manager.broadcast(room_id, {
                    "type": msg_type,
                    "sender_id": user_id,
                    "sender_name": user["username"],
                    "call_type": data.get("call_type", "voice"),
                    "channel": room_id,
                }, exclude=ws)
                continue

            # ── Typing indicator ──────────────────────────────────────────
            if msg_type == "typing":
                await manager.broadcast(room_id, {
                    "type": "typing",
                    "sender_id": user_id,
                    "sender_name": user["username"],
                    "is_typing": data.get("is_typing", False),
                }, exclude=ws)
                continue

            # ── Read receipt ──────────────────────────────────────────────
            if msg_type == "read":
                await messages_col.update_many(
                    {"room_id": room_id, "sender_id": {"$ne": user_id}},
                    {"$addToSet": {"read_by": user_id}},
                )
                await manager.broadcast(room_id, {
                    "type": "read_update",
                    "reader_id": user_id,
                    "room_id": room_id,
                }, exclude=ws)
                continue

            # ── Regular message ───────────────────────────────────────────
            content = data.get("content", "")
            file_url = data.get("file_url")
            reply_to_id = data.get("reply_to_id")
            is_encrypted = data.get("is_encrypted", False)
            duration = data.get("duration")  # voice note duration seconds

            reply_to_content = None
            reply_to_sender_name = None
            if reply_to_id:
                rm = await messages_col.find_one({"_id": ObjectId(reply_to_id)})
                if rm:
                    reply_to_content = rm["content"]
                    reply_to_sender_name = rm["sender_name"]

            message = {
                "room_id": room_id,
                "sender_id": user_id,
                "sender_name": user["username"],
                "content": content,
                "type": msg_type,
                "file_url": file_url,
                "reply_to_id": reply_to_id,
                "reply_to_content": reply_to_content,
                "reply_to_sender_name": reply_to_sender_name,
                "is_encrypted": is_encrypted,
                "duration": duration,
                "read_by": [],
                "reactions": [],
                "timestamp": datetime.utcnow(),
            }
            result = await messages_col.insert_one(message)
            message["id"] = str(result.inserted_id)
            message["timestamp"] = message["timestamp"].isoformat()
            del message["_id"]

            # Broadcast to all others in the room (sender sees it optimistically)
            await manager.broadcast(room_id, message, exclude=ws)

            # Push notification to offline members
            room = await rooms_col.find_one({"_id": ObjectId(room_id)})
            if room:
                other_ids = [m for m in room["members"] if m != user_id]
                player_ids = []
                async for member in users_col.find({"_id": {"$in": [ObjectId(i) for i in other_ids]}}):
                    if member.get("onesignal_player_id"):
                        player_ids.append(member["onesignal_player_id"])
                if player_ids:
                    body = content if msg_type == "text" else (
                        "📷 Image" if msg_type == "image" else
                        "🎤 Voice note" if msg_type == "audio" else
                        "Sent an attachment"
                    )
                    await send_push(
                        player_ids=player_ids,
                        title=user["username"],
                        body=body,
                        data={"room_id": room_id},
                    )

    except WebSocketDisconnect:
        manager.disconnect(room_id, ws, user_id)
        await manager.broadcast(room_id, {
            "type": "status",
            "user_id": user_id,
            "online": False,
            "last_seen": datetime.utcnow().isoformat(),
        })
