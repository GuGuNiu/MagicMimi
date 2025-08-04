from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..core.window_scanner import WindowScanner
from ..core.config import app_state, ScanSettings
from .ws import manager
import asyncio

router = APIRouter()
scanner_instance = WindowScanner(app_state, manager)

@router.post("/scan/start", summary="启动窗口扫描任务")
async def start_scan(settings: ScanSettings, background_tasks: BackgroundTasks):
    if app_state.is_scanning:
        raise HTTPException(status_code=400, detail="扫描任务已在运行")
    
    # 验证账户是否存在
    if settings.account_name not in app_state.accounts:
         raise HTTPException(status_code=404, detail=f"账户 '{settings.account_name}' 未找到")

    app_state.is_scanning = True
    app_state.stop_event = asyncio.Event() # 使用asyncio的Event
    
    # 使用后台任务来运行同步的扫描循环
    background_tasks.add_task(run_scanner_in_thread, settings, app_state.stop_event)

    await manager.broadcast_log(f"扫描任务已启动，目标窗口句柄: {settings.hwnd}", "INFO")
    return {"message": "扫描任务已启动"}

def run_scanner_in_thread(settings: ScanSettings, stop_event: asyncio.Event):
    # 这个函数将在一个独立的线程中被后台任务调用
    # 它创建一个新的事件循环来运行异步的扫描循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scanner_instance._scan_loop(settings, stop_event))
    loop.close()

@router.post("/scan/stop", summary="停止窗口扫描任务")
async def stop_scan():
    if not app_state.is_scanning:
        raise HTTPException(status_code=400, detail="没有正在运行的扫描任务")
    
    if app_state.stop_event:
        app_state.stop_event.set() # 发送停止信号
    
    # 重置状态
    app_state.is_scanning = False
    
    # 等待线程结束（可选，但最好有）
    if app_state.scanner_thread and app_state.scanner_thread.is_alive():
        app_state.scanner_thread.join(timeout=2.0)

    await manager.broadcast_log("扫描任务已手动停止。", "INFO")
    return {"message": "扫描任务已停止"}

@router.get("/scan/status", summary="获取当前扫描状态")
async def get_scan_status():
    return {"is_scanning": app_state.is_scanning}