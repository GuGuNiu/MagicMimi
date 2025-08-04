from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .api import system, settings, accounts, scanner, ws

# 定义前端静态文件的路径
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = FastAPI(
    title="咕咕牛万能咪咪API",
    description="为MagicMimi前端提供后端服务的API",
    version="1.0.0"
)

# 包含API路由
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(accounts.router, prefix="/api", tags=["Accounts & Login"])
app.include_router(scanner.router, prefix="/api", tags=["Scanner Control"])
app.include_router(ws.router, tags=["WebSocket"])

# 托管静态文件
app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    file_path = os.path.join(STATIC_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found. Please run 'npm run build' in the frontend directory."}