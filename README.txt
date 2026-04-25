🚀 AI Company OS v2 - 超簡單版

1. TERMINAL 1:
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

2. TERMINAL 2:
cd frontend
python -m http.server 3000

3. 瀏覽器: http://localhost:3000

看到 "WebSocket 連線成功" + 能傳訊息 = 成功！

這證明前後端 + WebSocket 正常，接下來版本 3 就加完整 UI。
