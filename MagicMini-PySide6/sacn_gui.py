import sys
import os
import json
import time
import uuid
import re
import http.client
import numpy
import cv2
from pyzbar.pyzbar import decode
import win32gui
import win32ui
import win32con
import win32api

from PySide6.QtCore import Qt, QThread, Signal, QObject, QDateTime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QGroupBox, QLineEdit, QComboBox,
    QTextEdit, QMessageBox
)
from PySide6.QtGui import QPainter, QPen, QColor

ACCOUNTS_FILE_PATH = "accounts.json"

style_sheet_string = """
QWidget {
    font-family: "Microsoft YaHei UI", "SimSun", sans-serif;
    font-size: 13px; color: #333333;
}
QMainWindow, #CentralWidget { background-color: #F5F7FA; }
QGroupBox {
    border: 1px solid #EBEEF5; border-radius: 5px; margin-top: 10px;
    padding: 15px 15px 10px 15px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 5px; margin-left: 10px; background-color: #F5F7FA;
}
QLineEdit, QComboBox, QTextEdit {
    border: 1px solid #DCDFE6; border-radius: 4px;
    padding: 7px; background-color: #FFFFFF;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color: #409EFF; }
QComboBox::drop-down { border: none; }
QPushButton {
    border: none; border-radius: 4px; padding: 8px 12px; font-size: 13px;
}
#PrimaryButton { background-color: #409EFF; color: #FFFFFF; }
#PrimaryButton:hover { background-color: #79BBFF; }
#PrimaryButton:disabled { background-color: #A0CFFF; }
#DangerButton { background-color: #F56C6C; color: white; }
#DangerButton:hover { background-color: #F89898; }
#SecondaryButton {
    background-color: #F2F6FC; color: #606266; border: 1px solid #DCDFE6;
}
#SecondaryButton:hover { background-color: #ECF5FF; color: #409EFF; }
#PinButton:checked {
    background-color: #E6A23C; color: white; border: 1px solid #E6A23C;
}
#LogDisplayBox {
    background-color: #2B2B2B; color: #A9B7C6;
    font-family: "Consolas", "Monaco", monospace;
}
#FpsLabel { font-size: 16px; font-weight: bold; color: #67C23A; }
"""

def load_saved_accounts():
    if not os.path.exists(ACCOUNTS_FILE_PATH): return {}
    try:
        with open(ACCOUNTS_FILE_PATH, 'r', encoding='utf-8') as file: return json.load(file)
    except (json.JSONDecodeError, IOError): return {}

def save_accounts_to_file(accounts):
    try:
        with open(ACCOUNTS_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(accounts, file, indent=4, ensure_ascii=False)
    except IOError as e: print(f"保存账户失败: {e}")

def get_active_windows():
    windows = {}
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows[win32gui.GetWindowText(hwnd)] = hwnd
    win32gui.EnumWindows(callback, None)
    return windows

def extract_uid_from_stoken(stoken_string):
    match = re.search(r"stuid=(\d+)", stoken_string)
    return match.group(1) if match else None

class OverlayRectangle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, 300, 300)
        self.center_on_screen()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor(255, 0, 0, 220), 3))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    def center_on_screen(self):
        screen_geo = QApplication.primaryScreen().geometry()
        self.move((screen_geo.width() - self.width()) // 2, (screen_geo.height() - self.height()) // 2)

# 创建一个线程
class ScannerThread(QThread):
    # 信号
    class ThreadSignals(QObject):
        log_message = Signal(str)
        fps_update = Signal(int)
        scan_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = self.ThreadSignals()
        self.is_running = False
        self.target_window_handle = None
        self.game_type = 4
        self.user_stoken = ""
        self.user_uid = ""
        self.device_id = str(uuid.uuid1())

    def capture_target_area(self):
        is_window_mode = self.target_window_handle is not None
        hwnd = self.target_window_handle if is_window_mode else win32gui.GetDesktopWindow()
        
        if is_window_mode:
            rect = win32gui.GetClientRect(hwnd)
            width, height, source_x, source_y = rect[2], rect[3], 0, 0
        else:
            width, height = 300, 300
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            source_x, source_y = (screen_width - width) // 2, (screen_height - height) // 2
        
        if width <= 0 or height <= 0: return None
        
        window_dc_handle = win32gui.GetWindowDC(hwnd)
        device_context = win32ui.CreateDCFromHandle(window_dc_handle)
        compatible_dc = device_context.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        try:
            bitmap.CreateCompatibleBitmap(device_context, width, height)
            compatible_dc.SelectObject(bitmap)
            compatible_dc.BitBlt((0, 0), (width, height), device_context, (source_x, source_y), win32con.SRCCOPY)
            img_bits = bitmap.GetBitmapBits(True)
            image = numpy.frombuffer(img_bits, dtype='uint8').reshape((height, width, 4))
            return image[:, :, :3]
        finally:
            device_context.DeleteDC()
            compatible_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc_handle)
            win32gui.DeleteObject(bitmap.GetHandle())

    def execute_login_process(self, ticket):
        try:
            conn = http.client.HTTPSConnection("api-sdk.mihoyo.com", timeout=10)
            payload = json.dumps({"app_id": self.game_type, "device": self.device_id, "ticket": ticket})
            endpoint = "/hk4e_cn/combo/panda/qrcode/scan" if self.game_type == 4 else "/hkrpg_cn/combo/panda/qrcode/scan"
            conn.request("POST", endpoint, payload, {})
            data = json.loads(conn.getresponse().read().decode("utf-8"))
            conn.close()
            self.signals.log_message.emit(f"抢码请求返回: {data}")
            if data.get("retcode") != 0:
                self.signals.log_message.emit(f"抢码失败: {data.get('message', '未知错误')}")
                return

            self.signals.log_message.emit("抢码成功, 正在获取游戏Token...")
            conn = http.client.HTTPSConnection("api-takumi.miyoushe.com", timeout=10)
            headers = {'cookie': self.user_stoken}
            conn.request("GET", "/auth/api/getGameToken", '', headers)
            token_data = json.loads(conn.getresponse().read().decode("utf-8"))
            conn.close()
            if token_data.get("retcode") != 0 or not token_data.get("data"):
                self.signals.log_message.emit(f"获取Token失败: {token_data.get('message')}, 请检查Stoken。")
                return

            game_token = token_data["data"]["game_token"]
            self.signals.log_message.emit("Token获取成功, 正在确认登录...")
            conn = http.client.HTTPSConnection("api-sdk.mihoyo.com", timeout=10)
            confirm_payload = json.dumps({
                "app_id": self.game_type, "device": self.device_id, "ticket": ticket,
                "payload": {"proto": "Account", "raw": f'{{"uid":"{self.user_uid}","token":"{game_token}"}}'}
            })
            conn.request("POST", "/hk4e_cn/combo/panda/qrcode/confirm", confirm_payload, headers)
            conn.getresponse().read()
            conn.close()
            self.signals.log_message.emit("登录流程全部成功完成。")
            self.signals.scan_successful.emit()
        except Exception as e:
            self.signals.log_message.emit(f"网络请求或处理时发生错误: {e}")

    def stoppable_sleep(self, duration_seconds):
        for _ in range(int(duration_seconds * 20)):
            if not self.is_running: break
            self.msleep(50)

    # 运行
    def run(self):
        self.is_running = True
        self.signals.log_message.emit("扫描线程已启动。")
        frame_count, start_time = 0, time.time()
        while self.is_running:
            try:
                img = self.capture_target_area()
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    codes = decode(gray)
                    if codes:
                        self.signals.log_message.emit("识别到二维码, 正在处理。")
                        match = re.search(r"ticket=([a-f0-9]+)", codes[0].data.decode())
                        if match:
                            self.execute_login_process(match.group(1))
                            self.stoppable_sleep(3)
                        else:
                            self.signals.log_message.emit("无法识别的二维码格式, 已忽略。")
                            self.stoppable_sleep(1)
                else: self.msleep(1000)
                
                frame_count += 1
                if time.time() - start_time >= 1:
                    self.signals.fps_update.emit(frame_count)
                    frame_count, start_time = 0, time.time()
                self.msleep(50)
            except Exception as e:
                self.signals.log_message.emit(f"扫描循环发生致命错误: {e}")
                break
        self.signals.log_message.emit("扫描线程已停止。")

    # 结束
    def stop_processing(self):
        self.is_running = False

# 创建一个主窗口
class MainApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MagicMini - v1.0.0 @MacacaTaurus")
        self.setFixedWidth(380) # 固定宽度
        self.resize(380, 800) # 设置初始尺寸
        self.accounts = {}
        self.scan_thread = ScannerThread()
        self.overlay_rectangle = OverlayRectangle()
        
        self.setup_user_interface()
        self.connect_ui_signals()
        
        self.load_and_display_accounts()
        self.refresh_window_list_dropdown()
        self.overlay_rectangle.hide()

    def setup_user_interface(self):
        central_widget = QWidget(self); central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10); main_layout.setSpacing(10)
        
        main_layout.addWidget(self.create_top_controls_panel())
        main_layout.addWidget(self.create_bottom_log_panel(), 1) 
    
    def create_top_controls_panel(self):
        # 创建包含所有控制控件的上部面板
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0,0,0,0); layout.setSpacing(10)

        status_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS: --"); self.fps_label.setObjectName("FpsLabel")
        self.pin_button = QPushButton("置顶"); self.pin_button.setObjectName("PinButton")
        self.pin_button.setCheckable(True)
        self.scan_status_label = QLabel("未启动")
        status_layout.addWidget(self.fps_label); status_layout.addStretch()
        status_layout.addWidget(self.scan_status_label)

        self.account_group = QGroupBox("账户管理")
        account_layout = QVBoxLayout()
        self.account_selector = QComboBox()
        self.nickname_input = QLineEdit(); self.nickname_input.setPlaceholderText("账户昵称")
        self.stoken_input = QTextEdit(); self.stoken_input.setPlaceholderText("粘贴Stoken文本")
        self.stoken_input.setFixedHeight(80)
        btn_layout = QHBoxLayout()
        self.save_button = QPushButton("保存"); self.save_button.setObjectName("PrimaryButton")
        self.delete_button = QPushButton("删除"); self.delete_button.setObjectName("DangerButton")
        btn_layout.addWidget(self.save_button); btn_layout.addWidget(self.delete_button)
        account_layout.addWidget(self.account_selector)
        account_layout.addWidget(self.nickname_input)
        account_layout.addWidget(self.stoken_input)
        account_layout.addLayout(btn_layout)
        self.account_group.setLayout(account_layout)

        self.control_group = QGroupBox("扫描控制")
        control_layout = QVBoxLayout()
        self.window_selector = QComboBox()
        self.refresh_button = QPushButton("刷新窗口"); self.refresh_button.setObjectName("SecondaryButton")
        self.game_selector = QComboBox(); self.game_selector.addItems(["原神", "星穹铁道"])
        
        scan_button_layout = QHBoxLayout() # 用于并排放置启动和停止按钮
        self.start_button = QPushButton("启动扫描"); self.start_button.setObjectName("PrimaryButton")
        self.stop_button = QPushButton("停止扫描"); self.stop_button.setObjectName("SecondaryButton")
        self.stop_button.setEnabled(False)
        scan_button_layout.addWidget(self.start_button)
        scan_button_layout.addWidget(self.stop_button)

        control_layout.addWidget(self.window_selector); control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.game_selector)
        control_layout.addLayout(scan_button_layout)
        self.control_group.setLayout(control_layout)
        
        layout.addLayout(status_layout)
        layout.addWidget(self.account_group)
        layout.addWidget(self.control_group)
        layout.addWidget(self.pin_button)
        
        return panel

    def create_bottom_log_panel(self):
        # 创建位于底部的日志面板
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        self.log_display_box = QTextEdit(); self.log_display_box.setObjectName("LogDisplayBox")
        self.log_display_box.setReadOnly(True)
        log_layout.addWidget(self.log_display_box)
        log_group.setLayout(log_layout)
        return log_group

    # 按钮操作
    def connect_ui_signals(self):
        self.save_button.clicked.connect(self.save_or_update_account)
        self.delete_button.clicked.connect(self.delete_selected_account)
        self.account_selector.currentIndexChanged.connect(self.on_account_selection_change)
        self.start_button.clicked.connect(self.start_scan_process)
        self.stop_button.clicked.connect(self.stop_scan_process)
        self.refresh_button.clicked.connect(self.refresh_window_list_dropdown)
        self.pin_button.toggled.connect(self.toggle_window_on_top)
        self.scan_thread.signals.log_message.connect(self.add_log_entry)
        self.scan_thread.signals.fps_update.connect(lambda fps: self.fps_label.setText(f"FPS: {fps}"))
        self.scan_thread.finished.connect(self.handle_scan_finished)
        self.scan_thread.signals.scan_successful.connect(self.stop_scan_process)

    def toggle_window_on_top(self, checked):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.add_log_entry("窗口已置顶。")
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.add_log_entry("窗口已取消置顶。")
        self.show()

    def add_log_entry(self, message):
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.log_display_box.append(f"{timestamp} > {message}")
    
    def set_controls_enabled(self, is_enabled):
        self.account_group.setEnabled(is_enabled)
        self.window_selector.setEnabled(is_enabled)
        self.refresh_button.setEnabled(is_enabled)
        self.game_selector.setEnabled(is_enabled)
        self.start_button.setEnabled(is_enabled)
        self.stop_button.setEnabled(not is_enabled)
        self.pin_button.setEnabled(is_enabled)

    def load_and_display_accounts(self):
        self.accounts = load_saved_accounts()
        self.account_selector.clear()
        if not self.accounts:
            self.account_selector.addItem("无账户")
        else:
            self.account_selector.addItems(self.accounts.keys())
        self.on_account_selection_change()

    def on_account_selection_change(self):
        name = self.account_selector.currentText()
        data = self.accounts.get(name)
        if data:
            self.nickname_input.setText(name)
            self.stoken_input.setPlainText(data.get("stoken", ""))
        else:
            self.nickname_input.clear(); self.stoken_input.clear()

    def save_or_update_account(self):
        name = self.nickname_input.text().strip()
        stoken = self.stoken_input.toPlainText().strip()
        if not name or not stoken:
            QMessageBox.warning(self, "信息不全", "账户昵称和Stoken均不能为空。")
            return
        
        uid = extract_uid_from_stoken(stoken)
        if not uid:
            QMessageBox.warning(self, "Stoken无效", "无法从Stoken中提取有效的UID(stuid)，请检查。")
            return

        self.accounts[name] = {"uid": uid, "stoken": stoken}
        save_accounts_to_file(self.accounts)
        self.add_log_entry(f"账户 '{name}' 已保存 (UID: {uid})")
        self.load_and_display_accounts()
        self.account_selector.setCurrentText(name)

    def delete_selected_account(self):
        name = self.account_selector.currentText()
        if name not in self.accounts: return
        reply = QMessageBox.question(self, "确认删除", f"您确定要删除账户 '{name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.accounts[name]
            save_accounts_to_file(self.accounts)
            self.add_log_entry(f"账户 '{name}' 已删除。")
            self.load_and_display_accounts()

    def refresh_window_list_dropdown(self):
        self.add_log_entry("刷新窗口列表...")
        self.window_selector.clear()
        self.window_selector.addItem("桌面中心 (默认)", userData=None)
        windows = get_active_windows()
        for title, hwnd in windows.items():
            self.window_selector.addItem(title, userData=hwnd)
        self.add_log_entry(f"找到 {len(windows)} 个窗口。")

    def start_scan_process(self):
        name = self.account_selector.currentText()
        if name not in self.accounts:
            QMessageBox.warning(self, "无法启动", "请先选择或添加一个有效的账户。")
            return
        
        account_data = self.accounts[name]
        self.scan_thread.user_stoken = account_data["stoken"]
        self.scan_thread.user_uid = account_data["uid"]
        self.scan_thread.game_type = 4 if self.game_selector.currentText() == "原神" else 8
        self.scan_thread.target_window_handle = self.window_selector.currentData()

        if self.scan_thread.target_window_handle:
            self.overlay_rectangle.hide()
            scan_mode_text = f"窗口模式"
        else:
            self.overlay_rectangle.show()
            scan_mode_text = "桌面模式"
        self.scan_status_label.setText(scan_mode_text)

        self.set_controls_enabled(False)
        self.scan_thread.start()

    def stop_scan_process(self):
        if not self.scan_thread.isRunning(): return
        self.add_log_entry("正在请求停止扫描...")
        self.stop_button.setEnabled(False)
        self.scan_thread.stop_processing()
    
    def handle_scan_finished(self):
        self.set_controls_enabled(True)
        self.overlay_rectangle.hide()
        self.scan_status_label.setText("未启动")
        self.fps_label.setText("FPS: --")

    def closeEvent(self, event):
        self.add_log_entry("正在关闭应用程序。")
        if self.scan_thread.isRunning():
            self.scan_thread.stop_processing()
            self.scan_thread.wait(1000)
        self.overlay_rectangle.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(style_sheet_string)
    main_window = MainApplicationWindow()
    main_window.show()
    sys.exit(app.exec())