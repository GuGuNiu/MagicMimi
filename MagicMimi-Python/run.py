import uvicorn
import threading
import time
import webview
import sys
import os
import tempfile
import mss

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.append(os.path.join(application_path))
else:
    application_path = os.path.dirname(__file__)

from backend.main import app

HOST = "127.0.0.1"
PORT = 8181
server = None
desktop_bg_path = None

def run_server():
    global server
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    server.run()

class Api:
    def minimize(self):
        if webview.windows:
            webview.windows[0].minimize()

    def close(self):
        if webview.windows:
            webview.windows[0].destroy()
    
    def get_desktop_background(self):
        if desktop_bg_path:
            return 'file://' + desktop_bg_path.replace('\\', '/')
        return ''

if __name__ == "__main__":
    print("--- 咕咕牛万能咪咪 (MagicMimi) 正在启动 ---")
    
    try:
        with mss.mss() as sct:
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            desktop_bg_path = temp_file.name
            temp_file.close()

            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=desktop_bg_path)
            print(f"桌面背景已截取并保存到: {desktop_bg_path}")
    except Exception as e:
        print(f"错误：截取桌面背景失败: {e}")
        desktop_bg_path = ''

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(2) 
    
    print(f"后端服务已在 http://{HOST}:{PORT} 启动")

    js_api = Api()
    
    window = webview.create_window(
        '咕咕牛万能咪咪',
        f'http://{HOST}:{PORT}',
        width=1100,
        height=720,
        resizable=True,
        frameless=True,
        transparent=False, # 保持False，避免点击穿透
        on_top=False,
        js_api=js_api
    )
    
    print("--- 正在启动前端界面 ---")
    
    webview.start(debug=True) # 在调试时开启debug=True，可以看到浏览器控制台错误

    if desktop_bg_path and os.path.exists(desktop_bg_path):
        try:
            os.remove(desktop_bg_path)
            print("临时截图文件已清理")
        except Exception as e:
            print(f"清理临时文件失败: {e}")

    print("\n--- 程序已关闭 ---")