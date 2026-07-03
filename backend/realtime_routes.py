from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict, Any, Set
import json
import asyncio
import logging
import time

logger = logging.getLogger("realtime")

router = APIRouter(prefix="/ws", tags=["realtime"])

class ConnectionManager:
    def __init__(self):
        # tenant_id -> {user_id -> List[WebSocket]}
        self.active_connections: Dict[str, Dict[str, List[WebSocket]]] = {}

    async def connect(self, tenant_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = {}
        if user_id not in self.active_connections[tenant_id]:
            self.active_connections[tenant_id][user_id] = []
        self.active_connections[tenant_id][user_id].append(websocket)
        logger.info(f"User {user_id} connected to real-time feed (Tenant: {tenant_id})")

    def disconnect(self, tenant_id: str, user_id: str, websocket: WebSocket):
        if tenant_id in self.active_connections and user_id in self.active_connections[tenant_id]:
            self.active_connections[tenant_id][user_id].remove(websocket)
            if not self.active_connections[tenant_id][user_id]:
                del self.active_connections[tenant_id][user_id]
            logger.info(f"User {user_id} disconnected (Tenant: {tenant_id})")

    async def broadcast_to_tenant(self, tenant_id: str, message: Dict[str, Any]):
        if tenant_id in self.active_connections:
            for user_id, websockets in self.active_connections[tenant_id].items():
                for websocket in websockets:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Error sending message to {user_id}: {e}")

    async def send_personal_message(self, tenant_id: str, user_id: str, message: Dict[str, Any]):
        if tenant_id in self.active_connections and user_id in self.active_connections[tenant_id]:
            for websocket in self.active_connections[tenant_id][user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending personal message to {user_id}: {e}")

manager = ConnectionManager()

@router.websocket("/{tenant_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str, user_id: str):
    await manager.connect(tenant_id, user_id, websocket)
    try:
        while True:
            # Receive messages from the client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming messages (e.g., presence updates)
            if message.get("type") == "presence":
                item_id = message.get("item_id")
                action = message.get("action", "viewing")
                
                # Broadcast presence to the tenant
                await manager.broadcast_to_tenant(tenant_id, {
                    "type": "presence_update",
                    "item_id": item_id,
                    "user_id": user_id,
                    "action": action,
                    "timestamp": time.time()
                })
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
                
    except WebSocketDisconnect:
        manager.disconnect(tenant_id, user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(tenant_id, user_id, websocket)

# Global accessor for broadcasting from other routes
async def notify_new_items(tenant_id: str, count: int):
    await manager.broadcast_to_tenant(tenant_id, {
        "type": "feed_update",
        "new_items_count": count,
        "message": f"{count} new items prioritized",
        "timestamp": time.time()
    })

async def notify_delegation(tenant_id: str, to_user_id: str, item_id: str, assigned_by: str):
    # Notify the recipient
    await manager.send_personal_message(tenant_id, to_user_id, {
        "type": "delegation_received",
        "item_id": item_id,
        "assigned_by": assigned_by,
        "timestamp": time.time()
    })
    # Also notify the whole tenant for the shared feed view
    await manager.broadcast_to_tenant(tenant_id, {
        "type": "delegation_update",
        "item_id": item_id,
        "to_user_id": to_user_id,
        "assigned_by": assigned_by,
        "timestamp": time.time()
    })
