from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/windows", summary="获取可见窗口列表")
async def get_windows():
    try:
        import pygetwindow as gw
        import win32gui
        
        windows = gw.getAllWindows()
        window_list = [
            {"title": w.title, "hwnd": w._hWnd}
            for w in windows
            if w.title and w.width > 100 and win32gui.IsWindowVisible(w._hWnd)
        ]
        return window_list
    except ImportError:
        raise HTTPException(status_code=501, detail="此功能仅在Windows上可用")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))