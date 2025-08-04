import requests
import uuid
import json
import hashlib
import time
import numpy as np
import qrcode
import io
import base64
from .config import app_state

class MihoyoAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'okhttp/4.8.0'})
        self.session.trust_env = False # 禁用系统代理

    def _get_ds(self, salt_type="app", query="", body=""):
        settings = app_state.api_settings
        salt_map = {"web": settings.salt_web, "app": settings.salt_app}
        salt = salt_map.get(salt_type)
        t = str(int(time.time()))
        r = ''.join(np.random.choice(list('abcdefghijklmnopqrstuvwxyz0123456789'), 6)) if salt_type == "web" else str(np.random.randint(100001, 200000))
        b_str = json.dumps(body, separators=(',', ':')) if isinstance(body, dict) else body
        q_str = query.split('?')[1] if '?' in query else query
        hash_string = f"salt={salt}&t={t}&r={r}&b={b_str}&q={q_str}"
        c = hashlib.md5(hash_string.encode()).hexdigest()
        return f"{t},{r},{c}"

    def fetch_qr_code(self):
        settings = app_state.api_settings
        device_id = str(uuid.uuid4()).upper()
        url = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch"
        payload = {"app_id": settings.qr_login_app_id, "device": device_id}
        headers = {
            'x-rpc-device_id': device_id,
            'x-rpc-app_version': settings.app_version,
            'x-rpc-client_type': '2',
            'DS': self._get_ds(body=payload)
        }
        try:
            res = self.session.post(url, json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("retcode") == 0 and "data" in data:
                qr_data = data["data"]
                if all(k in qr_data for k in ['url', 'ticket']):
                    img = qrcode.make(qr_data['url'])
                    # 将图片保存到内存中的字节流
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    # 将字节流编码为Base64字符串
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # 构造返回给前端的数据
                    response_data = {
                        "ticket": qr_data["ticket"],
                        "device": device_id,
                        # 前端直接使用此图片数据
                        "qr_image": f"data:image/png;base64,{img_base64}"
                    }
                    return response_data, None
            return None, data.get("message", f"API返回数据异常 {data}")
        except Exception as e:
            return None, f"网络请求失败 {e}"

    def query_qr_status(self, ticket, device_id):
        settings = app_state.api_settings
        url = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query"
        payload = {"app_id": settings.qr_login_app_id, "device": device_id, "ticket": ticket}
        headers = {'x-rpc-device_id': device_id, 'x-rpc-app_version': settings.app_version, 'x-rpc-client_type': '2', 'DS': self._get_ds(body=payload)}
        try:
            res = self.session.post(url, json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            return data, None
        except Exception as e:
            return None, f"网络请求失败 {e}"
            
    def get_stoken_from_game_token(self, uid, game_token):
        url = "https://passport-api.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken"
        payload = {"account_id": int(uid), "game_token": game_token}
        try:
            res = self.session.post(url, json=payload, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("retcode") == 0:
                token_info = data.get("data", {})
                stoken = token_info.get("token", {}).get("token")
                mid = token_info.get("user_info", {}).get("mid")
                if not stoken or not mid:
                    raise ValueError("响应中未找到stoken或mid")
                cookie = f"stuid={uid};stoken={stoken};mid={mid};"
                return cookie, None
            return None, data.get("message", "获取Stoken API返回错误")
        except Exception as e:
            return None, str(e)

    def attempt_game_login(self, ticket, game_type, account):
        device = str(uuid.uuid1())
        host = "api-sdk.mihoyo.com"
        
        try:
            # 扫描请求
            scan_path = f"/hk4e_cn/combo/panda/qrcode/scan" if game_type == 4 else f"/hkrpg_cn/combo/panda/qrcode/scan"
            scan_payload = {"app_id": game_type, "device": device, "ticket": ticket}
            res_scan = self.session.post(f"https://{host}{scan_path}", json=scan_payload)
            res_scan.raise_for_status()
            scan_data = res_scan.json()
            if scan_data.get("retcode") != 0: return False, f"Scan失败 {scan_data.get('message', '未知')}"

            # 获取游戏Token
            res_gt = self.session.get("https://api-takumi.mihoyo.com/auth/api/getGameToken", headers={'cookie': account.cookie})
            res_gt.raise_for_status()
            gt_data = res_gt.json()
            if gt_data.get("retcode") != 0: return False, f"获取GameToken失败 {gt_data.get('message', 'Stoken可能失效')}"
            game_token = gt_data["data"]["game_token"]

            # 确认登录
            confirm_path = f"/hk4e_cn/combo/panda/qrcode/confirm" if game_type == 4 else f"/hkrpg_cn/combo/panda/qrcode/confirm"
            confirm_payload = {
                "app_id": game_type, "device": device, "ticket": ticket,
                "payload": {"proto": "Account", "raw": json.dumps({"uid": account.uid, "token": game_token})}
            }
            res_confirm = self.session.post(f"https://{host}{confirm_path}", json=confirm_payload)
            res_confirm.raise_for_status()
            confirm_data = res_confirm.json()
            
            return confirm_data.get("retcode") == 0, confirm_data.get("message", "登录确认成功")
        except Exception as e:
            return False, f"网络请求异常 {e}"