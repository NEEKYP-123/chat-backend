from __future__ import annotations
from fastapi import WebSocket
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)
        self.online_users: set[str] = set()
        self.user_ws: dict[str, WebSocket] = {}

    async def connect(self, room_id: str, ws: WebSocket, user_id: str):
        await ws.accept()
        self.rooms[room_id].append(ws)
        self.online_users.add(user_id)
        self.user_ws[user_id] = ws

    def disconnect(self, room_id: str, ws: WebSocket, user_id: str):
        if ws in self.rooms[room_id]:
            self.rooms[room_id].remove(ws)
        if self.user_ws.get(user_id) == ws:
            self.online_users.discard(user_id)
            self.user_ws.pop(user_id, None)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.online_users

    async def broadcast(self, room_id: str, message: dict, exclude: WebSocket | None = None):
        dead = []
        for ws in list(self.rooms[room_id]):
            if ws == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.rooms[room_id]:
                self.rooms[room_id].remove(ws)

    async def broadcast_all(self, room_id: str, message: dict):
        await self.broadcast(room_id, message)

manager = ConnectionManager()
