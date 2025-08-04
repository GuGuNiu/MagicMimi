import asyncio
import time
import re
import cv2
import numpy as np
from pyzbar import pyzbar

try:
    import win32gui
    import win32ui
    import win32con
except ImportError:
    pass

from .config import AppState, ScanSettings

class WindowScanner:
    def __init__(self, app_state: AppState, websocket_manager):
        self.app_state = app_state
        self.websocket_manager = websocket_manager
        self.last_qr_data = None
        self.last_qr_time = 0
        self._scan_task = None # 用于持有asyncio任务

    def start(self, settings: ScanSettings):
        if self.app_state.is_scanning:
            return False, "扫描任务已在运行中"
        
        self.app_state.is_scanning = True
        # 创建一个异步任务 并在FastAPI的事件循环中运行它
        self._scan_task = asyncio.create_task(self._scan_loop(settings))
        return True, "扫描任务已启动"

    def stop(self):
        if not self.app_state.is_scanning or not self._scan_task:
            return False, "没有正在运行的扫描任务"

        # 取消异步任务
        if not self._scan_task.done():
            self._scan_task.cancel()
        
        # 立即更新状态
        self.app_state.is_scanning = False
        self._scan_task = None
        
        # 创建一个一次性任务来广播停止日志
        asyncio.create_task(self._post_stop_cleanup())
        
        return True, "扫描任务已停止"
    
    async def _post_stop_cleanup(self):
        await self.websocket_manager.broadcast_log("扫描已停止", "INFO")
        await self.websocket_manager.broadcast_fps(0.0)

    def _capture_frame(self, hwnd):
        # 这是一个纯同步的截图函数 不适合直接await
        # 它会在异步循环中被调用
        try:
            rect = win32gui.GetClientRect(hwnd)
            width, height = rect[2], rect[3]
            if width <= 0 or height <= 0: return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            # 使用PrintWindow截图 支持后台窗口
            win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
            
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8').reshape((height, width, 4))
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            return img_gray
        except Exception:
            return None

    async def _scan_loop(self, settings: ScanSettings):
        from .mihoyo_api import MihoyoAPI
        mihoyo_api = MihoyoAPI()
        
        scan_interval = 0.5 # 秒
        
        while self.app_state.is_scanning:
            start_time = time.time()
            
            # 检查窗口句柄是否有效
            if not win32gui.IsWindow(settings.hwnd):
                await self.websocket_manager.broadcast_log("目标窗口已关闭 扫描自动停止", "ERROR")
                break
            
            # 在事件循环中运行同步的截图函数 避免阻塞
            frame = await asyncio.to_thread(self._capture_frame, settings.hwnd)
            
            if frame is None:
                # 截图失败可能因为窗口最小化
                await asyncio.sleep(1)
                continue
            
            codes = pyzbar.decode(frame, symbols=[pyzbar.ZBarSymbol.QRCODE])
            if codes:
                for code in codes:
                    try:
                        qr_data = code.data.decode('utf-8')
                        if qr_data == self.last_qr_data and time.time() - self.last_qr_time < 5:
                            continue
                        
                        match = re.search(r"ticket=([a-fA-F0-9]+)", qr_data)
                        if match:
                            self.last_qr_data = qr_data
                            self.last_qr_time = time.time()
                            await self.websocket_manager.broadcast_log("发现有效游戏二维码", "SUCCESS")
                            
                            account = self.app_state.accounts.get(settings.account_name)
                            if not account:
                                await self.websocket_manager.broadcast_log(f"错误 找不到账户 {settings.account_name}", "ERROR")
                                continue
                            
                            # 在事件循环中运行同步的网络请求函数
                            success, message = await asyncio.to_thread(
                                mihoyo_api.attempt_game_login,
                                match.group(1),
                                settings.game_type,
                                account
                            )
                            
                            log_level = "SUCCESS" if success else "ERROR"
                            game_name = "原神" if settings.game_type == 4 else "星穹铁道"
                            log_message = f"抢码成功 账户 {account.uid[:4]}... 游戏 {game_name}" if success else f"抢码失败 {message}"
                            await self.websocket_manager.broadcast_log(log_message, log_level)
                            
                            if success: await asyncio.sleep(5) # 成功后等待一下
                            break
                    except Exception as e:
                        await self.websocket_manager.broadcast_log(f"处理二维码时出错 {e}", "WARN")

            elapsed = time.time() - start_time
            fps = 1 / elapsed if elapsed > 0 else 0
            await self.websocket_manager.broadcast_fps(fps)

            sleep_time = scan_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 循环结束后重置状态 确保主线程知道任务已停止
        if self.app_state.is_scanning:
            self.stop()