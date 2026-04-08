"""
A-bao 四站點餐系統 — 後端
FastAPI + WebSocket 廣播
所有訂單存在記憶體中（免費方案足夠測試）
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime
import json, asyncio, uuid

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 資料層 ──────────────────────────────────────────────
# menu_items: 菜單主資料（station 決定送往 drink 或 kitchen）
MENU = [
    {"id": "m01", "name": "奶茶",       "category": "飲料", "station": "drink",   "price": 30, "options": ["甜度", "冰量"]},
    {"id": "m02", "name": "紅茶",       "category": "飲料", "station": "drink",   "price": 20, "options": ["甜度", "冰量"]},
    {"id": "m03", "name": "多穀豆漿",   "category": "飲料", "station": "drink",   "price": 35, "options": ["甜度", "冰量"]},
    {"id": "m04", "name": "鮮奶茶",     "category": "飲料", "station": "drink",   "price": 45, "options": ["甜度", "冰量"]},
    {"id": "m05", "name": "咖啡",       "category": "飲料", "station": "drink",   "price": 40, "options": ["甜度", "冰量"]},
    {"id": "m06", "name": "日式雞排蛋餅","category": "蛋餅", "station": "kitchen", "price": 55, "options": []},
    {"id": "m07", "name": "牛肉蛋漢堡", "category": "漢堡", "station": "kitchen", "price": 65, "options": []},
    {"id": "m08", "name": "手拍厚牛堡", "category": "漢堡", "station": "kitchen", "price": 80, "options": []},
    {"id": "m09", "name": "法式麵包",   "category": "麵包", "station": "kitchen", "price": 45, "options": []},
    {"id": "m10", "name": "起司蛋餅",   "category": "蛋餅", "station": "kitchen", "price": 40, "options": []},
    {"id": "m11", "name": "薯餅",       "category": "炸物", "station": "kitchen", "price": 25, "options": []},
    {"id": "m12", "name": "厚片吐司",   "category": "吐司", "station": "kitchen", "price": 35, "options": []},
]

# orders: { order_id: { ... } }
orders: dict = {}
order_counter = 100  # A101, A102, ...

# ── WebSocket 連線池 ────────────────────────────────────
connections: list[WebSocket] = []

async def broadcast(msg: dict):
    """廣播給所有連線中的 client"""
    data = json.dumps(msg, ensure_ascii=False)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)

# ── 工具函式 ────────────────────────────────────────────
def calc_order_status(order):
    """根據 order_items 的狀態計算整單狀態"""
    items = order["items"]
    if not items:
        return "empty"
    statuses = [it["status"] for it in items]
    if all(s == "done" for s in statuses):
        return "ready"       # 全部完成 → 可交單
    if any(s == "making" for s in statuses):
        return "making"      # 有人在做
    if all(s == "pending" for s in statuses):
        return "pending"     # 全部待做
    return "partial"         # 部分完成

def get_full_state():
    """回傳完整狀態（用於新連線同步）"""
    return {
        "type": "full_state",
        "menu": MENU,
        "orders": orders,
    }

# ── WebSocket 端點 ──────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    # 新連線先送完整狀態
    try:
        await websocket.send_text(json.dumps(get_full_state(), ensure_ascii=False))
    except Exception:
        connections.remove(websocket)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "create_order":
                await handle_create_order(msg)
            elif action == "update_item_status":
                await handle_update_item_status(msg)
            elif action == "mark_delivered":
                await handle_mark_delivered(msg)
            elif action == "get_state":
                await websocket.send_text(json.dumps(get_full_state(), ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        if websocket in connections:
            connections.remove(websocket)

# ── 動作處理 ────────────────────────────────────────────
async def handle_create_order(msg):
    global order_counter
    order_counter += 1
    oid = f"A{order_counter}"
    order = {
        "id": oid,
        "type": msg.get("order_type", "外帶"),    # 內用/外帶
        "table": msg.get("table", ""),              # 桌號
        "items": [],
        "status": "pending",
        "created_at": datetime.now().strftime("%H:%M"),
        "delivered": False,
    }
    for it in msg.get("items", []):
        menu_item = next((m for m in MENU if m["id"] == it["menu_id"]), None)
        if not menu_item:
            continue
        order["items"].append({
            "id": str(uuid.uuid4())[:8],
            "menu_id": it["menu_id"],
            "name": menu_item["name"],
            "station": menu_item["station"],
            "qty": it.get("qty", 1),
            "sugar": it.get("sugar", ""),
            "ice": it.get("ice", ""),
            "note": it.get("note", ""),
            "status": "pending",  # pending → making → done
        })
    order["status"] = calc_order_status(order)
    orders[oid] = order
    await broadcast({"type": "order_created", "order": order})

async def handle_update_item_status(msg):
    oid = msg.get("order_id")
    item_id = msg.get("item_id")
    new_status = msg.get("status")  # "making" or "done"
    if oid not in orders or new_status not in ("making", "done"):
        return
    order = orders[oid]
    for it in order["items"]:
        if it["id"] == item_id:
            it["status"] = new_status
            break
    order["status"] = calc_order_status(order)
    await broadcast({"type": "order_updated", "order": order})

async def handle_mark_delivered(msg):
    oid = msg.get("order_id")
    if oid not in orders:
        return
    orders[oid]["delivered"] = True
    orders[oid]["status"] = "delivered"
    await broadcast({"type": "order_updated", "order": orders[oid]})

# ── HTTP 端點 ───────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "orders": len(orders), "connections": len(connections)}

@app.get("/api/menu")
async def get_menu():
    return MENU

@app.get("/")
async def root():
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
