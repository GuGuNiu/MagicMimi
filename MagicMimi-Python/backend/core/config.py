from pydantic import BaseModel, Field
import json
import os

SETTINGS_FILE = "api_settings.json"
ACCOUNTS_FILE = "mihoyo_accounts.json"

class Account(BaseModel):
    uid: str
    cookie: str

class ScanSettings(BaseModel):
    account_name: str
    hwnd: int
    game_type: int

class ApiSettings(BaseModel):
    app_version: str = Field(default="2.70.1", description="米游社App版本号")
    salt_web: str = Field(default="sjdNFJB7XxyDWGIAk0eTV8AOCfMJmyEo", description="Web请求用Salt")
    salt_app: str = Field(default="S9Hrn38d2b55PamfIR9BNA3Tx9sQTOem", description="App请求用Salt")
    qr_login_app_id: int = Field(default=2, description="扫码登录用的App ID")

class AppState:
    def __init__(self):
        self.is_scanning: bool = False
        # 不再需要scanner_thread和stop_event
        self.api_settings: ApiSettings = self.load_api_settings()
        self.accounts: dict[str, Account] = self.load_accounts()

    def load_api_settings(self) -> ApiSettings:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return ApiSettings(**data)
            except (json.JSONDecodeError, TypeError):
                # 文件损坏或格式不匹配则使用默认值
                return ApiSettings()
        return ApiSettings()

    def save_api_settings(self):
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.api_settings.model_dump(), f, indent=4) # 使用新版pydantic的model_dump
    
    def load_accounts(self) -> dict[str, Account]:
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 将字典转换为Account模型
                    return {name: Account(**acc_data) for name, acc_data in data.items()}
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def save_accounts(self):
        # 将Account模型转换回字典进行存储
        data_to_save = {name: acc.model_dump() for name, acc in self.accounts.items()}
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

# 创建一个全局单例
app_state = AppState()