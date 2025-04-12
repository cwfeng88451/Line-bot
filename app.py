import os
import json
import base64
from datetime import datetime, timedelta
from flask import Flask, request, abort
from dotenv import load_dotenv
import openai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

app = Flask(__name__)

# 載入環境變數
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# 管理者 User ID
ADMIN_USER_ID = 'U984188d553a80bf4c6c8fce95e268f9c'

# 每日免費使用次數
DAILY_FREE_LIMIT = 3

# 客服網址
CUSTOMER_SERVICE_URL = "https://lin.ee/w4elbGV"

# 使用者資料檔案
USER_DATA_FILE = 'users_data.json'

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

user_data = load_user_data()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if user_id == ADMIN_USER_ID and text == "管理":
        reply = "【管理者功能】\n1. 查看全部用戶資料（開發中）\n2. 調整次數（開發中）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if text == "資訊":
        reply = generate_status(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    reply = "無法識別的指令，請使用以下指令：\n（1）資訊 - 查看個人狀態\n（2）VIP - 查看 VIP 方案\n（3）分享 - 產生分享推薦鏈結"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    user = user_data.get(user_id, {
        'used_count': 0,
        'recommend_count': 0,
        'customer_service_count': 0,
        'vip_expiry': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    })

    if user['used_count'] >= DAILY_FREE_LIMIT:
        reply = "今日免費使用次數已達上限，請明日再試或升級為 VIP。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = message_content.content
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    prompt = f"請根據以下的圖片內容，生成一個適合社交媒體的標題和內文：\n\n圖片：{image_base64}"
    response = openai.Completion.create(
        model="gpt-4o",
        prompt=prompt,
        temperature=0.7,
        max_tokens=150
    )
    result = response.choices[0].text.strip().split('\n', 1)
    title = result[0] if len(result) > 0 else "無法生成標題"
    content = result[1] if len(result) > 1 else "無法生成內文"
    
        # 更新使用次數
    user['used_count'] += 1
    user_data[user_id] = user
    save_user_data(user_data)

    # 計算剩餘次數與 VIP 到期日
    remaining = DAILY_FREE_LIMIT - user['used_count']
    vip_expiry = datetime.strptime(user['vip_expiry'], '%Y-%m-%d')
    vip_days_left = (vip_expiry - datetime.now()).days

    # 回覆格式
    reply_text = f"""歡迎使用 AI看圖寫文案智能體，只要上傳圖片，即可快速產生文案，協助你發文不再煩惱。

【標題】{title}
【內文】{content}

---

【使用者可用指令】
（1）資訊 - 查看個人狀態
（2）VIP - 查看 VIP 方案
（3）分享 - 產生分享推薦鏈結（系統自動統計透過分享添加機器人的數量）

---

【目前狀態】
每日免費使用次數：3次（每日凌晨自動重置）
今日已使用次數：{user['used_count']}次
今日剩餘免費次數：{remaining}次
推薦獎勵剩餘次數：{user['recommend_count']}次（透過分享推薦獲得）
客服獎勵剩餘次數：{user['customer_service_count']}次（加入客服獲得）

VIP 到期日：{user['vip_expiry']}（剩{vip_days_left}天）

---

加入客服獲得額外10次使用次數（限1次）：
{CUSTOMER_SERVICE_URL}

---

【用戶ID】
{user_id}
"""

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

# 狀態查詢功能
def generate_status(user_id):
    user = user_data.get(user_id, {
        'used_count': 0,
        'recommend_count': 0,
        'customer_service_count': 0,
        'vip_expiry': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    })

    remaining = DAILY_FREE_LIMIT - user['used_count']
    vip_expiry = datetime.strptime(user['vip_expiry'], '%Y-%m-%d')
    vip_days_left = (vip_expiry - datetime.now()).days

    status_text = f"""【目前狀態】
每日免費使用次數：3次（每日凌晨自動重置）
今日已使用次數：{user['used_count']}次
今日剩餘免費次數：{remaining}次
推薦獎勵剩餘次數：{user['recommend_count']}次（透過分享推薦獲得）
客服獎勵剩餘次數：{user['customer_service_count']}次（加入客服獲得）

VIP 到期日：{user['vip_expiry']}（剩{vip_days_left}天）

---

加入客服獲得額外10次使用次數（限1次）：
{CUSTOMER_SERVICE_URL}

---

【用戶ID】
{user_id}
"""
    return status_text

if __name__ == "__main__":
    app.run()