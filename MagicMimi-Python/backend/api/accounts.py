from fastapi import APIRouter, HTTPException, Body
from ..core.config import app_state, Account
from pydantic import BaseModel
from ..core.mihoyo_api import MihoyoAPI
import json

router = APIRouter()
mihoyo_api = MihoyoAPI()

@router.get("/accounts", summary="获取所有已保存账户")
async def get_accounts():
    return {name: acc.model_dump() for name, acc in app_state.accounts.items()}

@router.delete("/accounts/{name}", summary="删除指定账户")
async def delete_account(name: str):
    if name not in app_state.accounts:
        raise HTTPException(status_code=404, detail="账户不存在")
    del app_state.accounts[name]
    app_state.save_accounts()
    return {"message": f"账户 {name} 已删除"}

@router.get("/login/qr", summary="请求登录二维码")
async def get_login_qr():
    qr_data, error = mihoyo_api.fetch_qr_code()
    if error:
        raise HTTPException(status_code=500, detail=error)
    return qr_data

@router.get("/login/status", summary="查询二维码登录状态")
async def get_login_status(ticket: str, device: str):
    status_data, error = mihoyo_api.query_qr_status(ticket, device)
    if error:
        raise HTTPException(status_code=500, detail=error)
        
    # 如果状态是已确认 则在后端获取Stoken
    if status_data.get("retcode") == 0 and status_data.get("data", {}).get("stat") == "Confirmed":
        try:
            raw_payload = json.loads(status_data["data"]["payload"]["raw"])
            uid, game_token = raw_payload['uid'], raw_payload['token']
            
            cookie, stoken_error = mihoyo_api.get_stoken_from_game_token(uid, game_token)
            if stoken_error:
                raise HTTPException(status_code=500, detail=f"获取Stoken失败 {stoken_error}")

            # 成功后将新账户信息附加到响应中
            status_data["new_account"] = {"uid": uid, "cookie": cookie}
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"处理扫码确认数据时出错 {e}")

    return status_data

# 定义一个用于接收POST body的模型
class SaveAccountPayload(BaseModel):
    name: str
    uid: str
    cookie: str

@router.post("/login/save", summary="保存新登录的账户")
async def save_new_account(payload: SaveAccountPayload = Body(...)):
    if payload.name in app_state.accounts:
        raise HTTPException(status_code=409, detail="该账户名已存在")
    
    # 从payload创建Account模型
    new_account = Account(uid=payload.uid, cookie=payload.cookie)
    app_state.accounts[payload.name] = new_account
    app_state.save_accounts()
    return {"message": f"账户 {payload.name} 已成功保存"}