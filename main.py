"""
A-bao 四站點餐系統 — 後端（完整菜單版）
FastAPI + WebSocket 廣播
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime
import json, uuid

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 完整菜單資料 ────────────────────────────────────────
# station: "drink" = 飲料站, "kitchen" = 廚房站
# price_type: "fixed"=固定價, "hot_cold"=冷熱價, "size"=杯型價

DRINK_CATEGORIES = {"多穀豆漿", "鮮奶 / 茶", "古早味豆漿", "純味茶", "義式咖啡", "果汁 / 特調", "鮮奶厚茶"}

MENU_DATA = [
    {
        "category": "板燒漢堡", "emoji": "🍔",
        "items": [
            {"name": "玉米蛋", "price": 30},
            {"name": "火腿蛋", "price": 30},
            {"name": "豬肉蛋", "price": 35},
            {"name": "雞肉蛋", "price": 40},
            {"name": "燻雞蛋", "price": 40},
            {"name": "牛肉蛋", "price": 40},
            {"name": "鮪魚蛋", "price": 45},
            {"name": "日式豬排蛋", "price": 45},
            {"name": "日式蒲燒豬", "price": 45},
            {"name": "鍋燒蛋(豬/雞)", "price": 55},
        ]
    },
    {
        "category": "活力蛋餅", "emoji": "🥙",
        "items": [
            {"name": "原味蛋餅", "price": 25},
            {"name": "肉鬆蛋餅", "price": 30},
            {"name": "玉米蛋餅", "price": 30},
            {"name": "起司蛋餅", "price": 30},
            {"name": "蔬菜蛋餅", "price": 30},
            {"name": "洋芋蛋餅", "price": 30},
            {"name": "火腿蛋餅", "price": 35},
            {"name": "培根蛋餅", "price": 35},
            {"name": "豬肉蛋餅", "price": 40},
            {"name": "鮪魚蛋餅", "price": 35},
            {"name": "燻雞蛋餅", "price": 35},
            {"name": "肉片蛋餅", "price": 40},
        ]
    },
    {
        "category": "日式穀堡", "emoji": "🍙",
        "items": [
            {"name": "日式流沙雞", "price": 35},
            {"name": "日式咖哩", "price": 35},
            {"name": "冰淇淋鮪魚", "price": 50},
            {"name": "大阪豬排", "price": 50},
            {"name": "雙層豬排", "price": 45},
            {"name": "孜然豬排", "price": 50},
        ]
    },
    {
        "category": "厚片", "emoji": "🍞",
        "items": [
            {"name": "果醬厚片", "price": 25},
            {"name": "起司奶油厚片", "price": 30},
            {"name": "鮪魚洋蔥厚片", "price": 35},
            {"name": "爆漿起司厚片", "price": 45},
        ]
    },
    {
        "category": "法國土司", "emoji": "🧈",
        "items": [
            {"name": "果醬法國土司", "price": 25},
            {"name": "日式培根法國土司", "price": 35},
            {"name": "深海鱈魚法國土司", "price": 35},
            {"name": "黃金肉鬆法國土司", "price": 40},
        ]
    },
    {
        "category": "板燒土司", "emoji": "🥪",
        "items": [
            {"name": "蔬菜土司", "price": 25},
            {"name": "玉米蛋土司", "price": 30},
            {"name": "肉鬆蛋土司", "price": 30},
            {"name": "芝士蛋土司", "price": 30},
            {"name": "火腿蛋土司", "price": 35},
            {"name": "培根蛋土司", "price": 35},
            {"name": "豬肉蛋土司", "price": 40},
            {"name": "香雞蛋土司", "price": 40},
            {"name": "鮪魚蛋土司", "price": 45},
            {"name": "鍋燒蛋土司", "price": 45},
        ]
    },
    {
        "category": "起酥堡", "emoji": "🥐",
        "items": [
            {"name": "草莓起酥", "price": 30},
            {"name": "洋芋燻蛋起酥", "price": 35},
            {"name": "香蒜芋玉米起酥", "price": 35},
            {"name": "薯餅茄醬起酥", "price": 35},
            {"name": "酥蛋肉肉起酥", "price": 45},
        ]
    },
    {
        "category": "蔬食捲餅", "emoji": "🌯",
        "items": [
            {"name": "香雞蕃茄捲餅", "price": 40},
            {"name": "黃金肉肉捲餅", "price": 45},
            {"name": "日式雞排捲餅", "price": 50},
            {"name": "海苔花枝捲餅", "price": 50},
            {"name": "鮮味鮪拼捲餅", "price": 50},
            {"name": "美式雞腿捲餅", "price": 55, "note": "辣味"},
        ]
    },
    {
        "category": "法式麵包", "emoji": "🥖",
        "items": [
            {"name": "火腿起司法式麵包", "price": 45},
            {"name": "蕃茄肉肉法式麵包", "price": 45},
            {"name": "昔莓芽起司法式麵包", "price": 45},
            {"name": "陽光香腸法式麵包", "price": 45},
            {"name": "荷苣烤肉法式麵包", "price": 50},
            {"name": "日式燻雞法式麵包", "price": 55},
        ]
    },
    {
        "category": "田園蔬果", "emoji": "🥗",
        "items": [
            {"name": "馬鈴薯土司", "price": 30},
            {"name": "南瓜土司", "price": 30},
            {"name": "全麥茄醬鮪", "price": 35},
            {"name": "全麥苜蓿火腿", "price": 35},
            {"name": "全麥蔬菜沙拉", "price": 35},
            {"name": "田園蔬菜捲", "price": 35},
            {"name": "田園什錦蔬菜", "price": 40},
        ]
    },
    {
        "category": "中式茶點", "emoji": "🥟",
        "items": [
            {"name": "鍋貼", "price": 30},
            {"name": "燒賣", "price": 35},
            {"name": "鮮肉包", "price": 30},
            {"name": "蔥油餅", "price": 30},
            {"name": "蘿蔔糕", "price": 30},
            {"name": "黃金薯餅", "price": 35},
            {"name": "美式雞塊", "price": 40},
            {"name": "炸雞翅", "price": 45},
        ]
    },
    {
        "category": "主廚推薦", "emoji": "⭐",
        "items": [
            {"name": "南瓜燒餅", "price": 40},
            {"name": "地瓜捲餅", "price": 40},
            {"name": "野菜歐姆蛋", "price": 45},
            {"name": "奶油布丁酥(5入)", "price": 40},
            {"name": "米花雞球", "price": 45},
            {"name": "拔絲特酥蛋餅", "price": 50},
            {"name": "手拍厚牛堡", "price": 70},
            {"name": "鐵板雞肉炒麵-小", "price": 50},
            {"name": "鐵板雞肉炒麵-中", "price": 55},
            {"name": "鐵板雞肉炒麵-大", "price": 70},
        ]
    },
    # ── 飲料類 ──
    {
        "category": "多穀豆漿", "emoji": "🥛",
        "items": [
            {"name": "多穀豆漿", "hot": 30, "cold": 30, "L_hot": 40, "L_cold": 40},
            {"name": "多穀紅茶", "hot": 30, "cold": 30, "L_hot": 40, "L_cold": 40},
            {"name": "多穀抹茶", "hot": 35, "cold": 35, "L_hot": 45, "L_cold": 45},
            {"name": "多穀奶茶", "hot": 35, "cold": 35, "L_hot": 45, "L_cold": 45},
            {"name": "多穀薏仁漿", "hot": 40, "cold": 40, "L_hot": 50, "L_cold": 50},
        ]
    },
    {
        "category": "鮮奶 / 茶", "emoji": "🍵",
        "items": [
            {"name": "黃方拿鐵", "hot": 50, "cold": 50},
            {"name": "阿里山拿鐵", "hot": 50, "cold": 50},
            {"name": "四季春拿鐵", "hot": 50, "cold": 50},
            {"name": "玄米拿鐵", "hot": 50, "cold": 50},
            {"name": "阿薩姆鮮奶茶", "hot": 25, "cold": 30},
            {"name": "美香奶奶", "hot": 25, "cold": 30},
            {"name": "高山青奶", "hot": 25, "cold": 30},
            {"name": "旺來奶茶", "hot": 30, "cold": 35},
            {"name": "茉香青奶", "hot": 35, "cold": 45},
            {"name": "抹茶綠奶", "hot": 35, "cold": 45},
        ]
    },
    {
        "category": "古早味豆漿", "emoji": "🫘",
        "items": [
            {"name": "研磨豆漿", "hot": 20, "cold": 25},
            {"name": "紅茶豆漿", "hot": 20, "cold": 25},
            {"name": "胚芽豆漿", "hot": 25, "cold": 30},
            {"name": "薏仁豆漿", "hot": 30, "cold": 35},
            {"name": "抹茶豆漿", "hot": 30, "cold": 35},
            {"name": "養生豆漿", "hot": 30, "cold": 35},
        ]
    },
    {
        "category": "純味茶", "emoji": "🫖",
        "items": [
            {"name": "阿薩姆紅茶", "price": 20, "L_price": 25},
            {"name": "茉香綠茶", "price": 20, "L_price": 25},
            {"name": "高山青茶", "price": 20, "L_price": 25},
            {"name": "東方美人", "price": 35},
            {"name": "黃金烏龍", "price": 35},
            {"name": "阿里山茶", "price": 35},
            {"name": "玄米玉露", "price": 35},
            {"name": "四季綠茶", "price": 35},
        ]
    },
    {
        "category": "義式咖啡", "emoji": "☕",
        "items": [
            {"name": "豆奶拿鐵", "hot": 40, "cold": 40},
            {"name": "特調咖啡", "hot": 40, "cold": 40},
            {"name": "美式咖啡", "hot": 40, "cold": 40},
            {"name": "拿鐵咖啡", "hot": 55, "cold": 55},
            {"name": "卡布奇諾", "hot": 55, "cold": 55},
        ]
    },
    {
        "category": "果汁 / 特調", "emoji": "🍹",
        "items": [
            {"name": "浪蕾金磚", "price": 35},
            {"name": "黑木耳豆漿", "hot": 30, "cold": 30, "L_hot": 40, "L_cold": 40},
            {"name": "紅茶拿鐵", "hot": 40, "cold": 50},
            {"name": "檸檬紅茶", "price": 40},
            {"name": "檸檬綠茶", "price": 40},
            {"name": "百香綠茶", "price": 40},
            {"name": "柳橙綠茶", "price": 45},
            {"name": "黑糖豆漿", "hot": 35, "cold": 45},
            {"name": "黑糖紅茶牛奶", "hot": 50, "cold": 60},
        ]
    },
    {
        "category": "鮮奶厚茶", "emoji": "🥤",
        "items": [
            {"name": "果汁厚茶", "price": 35},
            {"name": "鮮奶厚茶", "price": 40},
            {"name": "奶蓋可可", "price": 45},
            {"name": "奶蓋紅茶", "price": 45},
            {"name": "奶蓋青茶", "price": 45},
        ]
    },
]

# 展平成 MENU list，自動加 id 和 station
MENU = []
_counter = 0
for cat in MENU_DATA:
    station = "drink" if cat["category"] in DRINK_CATEGORIES else "kitchen"
    is_drink = station == "drink"
    for item in cat["items"]:
        _counter += 1
        mid = f"m{_counter:03d}"
        # 決定預設價格（取最低價或 fixed price）
        if "price" in item:
            default_price = item["price"]
        elif "hot" in item:
            default_price = min(item.get("hot", 999), item.get("cold", 999))
        else:
            default_price = 0
        MENU.append({
            "id": mid,
            "name": item["name"],
            "category": cat["category"],
            "emoji": cat["emoji"],
            "station": station,
            "price": default_price,
            "has_temp": "hot" in item or "cold" in item,
            "hot_price": item.get("hot"),
            "cold_price": item.get("cold"),
            "L_hot": item.get("L_hot"),
            "L_cold": item.get("L_cold"),
            "L_price": item.get("L_price"),
            "is_drink": is_drink,
            "note": item.get("note", ""),
        })

# ── 訂單資料 ────────────────────────────────────────────
orders: dict = {}
order_counter = 100

# ── WebSocket 連線池 ────────────────────────────────────
connections: list[WebSocket] = []

async def broadcast(msg: dict):
    data = json.dumps(msg, ensure_ascii=False)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)

def calc_order_status(order):
    items = order["items"]
    if not items:
        return "empty"
    statuses = [it["status"] for it in items]
    if all(s == "done" for s in statuses):
        return "ready"
    if any(s == "making" for s in statuses):
        return "making"
    if all(s == "pending" for s in statuses):
        return "pending"
    return "partial"

def get_full_state():
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
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        if websocket in connections:
            connections.remove(websocket)

async def handle_create_order(msg):
    global order_counter
    order_counter += 1
    oid = f"A{order_counter}"
    order = {
        "id": oid,
        "type": msg.get("order_type", "外帶"),
        "table": msg.get("table", ""),
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
            "temp": it.get("temp", ""),
            "size": it.get("size", ""),
            "note": it.get("note", ""),
            "price": it.get("price", menu_item["price"]),
            "status": "pending",
        })
    order["status"] = calc_order_status(order)
    order["total"] = sum(it["price"] * it["qty"] for it in order["items"])
    orders[oid] = order
    await broadcast({"type": "order_created", "order": order})

async def handle_update_item_status(msg):
    oid = msg.get("order_id")
    item_id = msg.get("item_id")
    new_status = msg.get("status")
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
