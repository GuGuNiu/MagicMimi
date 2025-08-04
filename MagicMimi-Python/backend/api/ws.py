from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import time

router = APIRouter()

class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # 使用json.dumps确保数据格式正确
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

    async def broadcast_log(self, message: str, level: str = "INFO"):
        log_entry = {
            "type": "log",
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message
        }
        await self.broadcast(log_entry)

    async def broadcast_fps(self, fps: float):
        fps_data = {"type": "fps", "value": f"{fps:.1f}"}
        await self.broadcast(fps_data)

manager = WebSocketManager()

@router.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接开放，等待断开
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)