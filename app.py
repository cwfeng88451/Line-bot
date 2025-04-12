from flask import Flask, request, abort
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

app = Flask(__name__)

# LINE 官方金鑰
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

# 管理者ID
ADMIN_USER_ID = 'U984188d553a80bf4c6c8fce95e268f9c'

# 模擬使用者資料
user_data = {}

# 每日免費次數
DAILY_FREE_LIMIT = 3

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
    text = event.message.text

    if user_id == ADMIN_USER_ID and text == "管理":
        reply = "【管理者功能】\n1. 查看全部用戶資料（開發中）\n2. 調整次數（開發中）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if text == "資訊":
        reply = generate_status(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    user = user_data.get(user_id, {
        'used_count': 0,
        'recommend_count': 0,
        'customer_service_count': 0,
        'vip_expiry': '2025-05-01'
    })

    used_count = user['used_count']
    remaining = DAILY_FREE_LIMIT - used_count
    if remaining < 0:
        remaining = 0

    vip_expiry = user['vip_expiry']
    vip_days_left = (datetime.strptime(vip_expiry, '%Y-%m-%d') - datetime.now()).days
    if vip_days_left < 0:
        vip_days_left = 0

    title = "午後陽光的溫度"
    content = "靜靜地坐在窗邊，讓陽光灑滿心房，這就是生活的溫柔片刻。"

    reply_text = f"""【標題】{title}
【內文】{content}

---

【使用者可用指令】
（1）資訊 - 查看個人狀態
（2）VIP - 查看 VIP 方案
（3）分享 - 產生分享推薦鏈結（系統自動統計透過分享添加機器人的數量）

---

【目前狀態】
每日免費使用次數：3次（每日凌晨自動重置）
今日已使用次數：{used_count}次
今日剩餘免費次數：{remaining}次
推薦獎勵剩餘次數：{user['recommend_count']}次（透過分享推薦獲得）
客服獎勵剩餘次數：{user['customer_service_count']}次（加入客服獲得）

VIP 到期日：{vip_expiry}（剩{vip_days_left}天）

---

加入客服獲得額外10次使用次數（限1次）：
https://lin.ee/w4elbGV

---

【用戶ID】
{user_id}
"""

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    user['used_count'] += 1
    user_data[user_id] = user

def generate_status(user_id):
    user = user_data.get(user_id, {
        'used_count': 0,
        'recommend_count': 0,
        'customer_service_count': 0,
        'vip_expiry': '2025-05-01'
    })

    used_count = user['used_count']
    remaining = DAILY_FREE_LIMIT - used_count
    if remaining < 0:
        remaining = 0

    vip_expiry = user['vip_expiry']
    vip_days_left = (datetime.strptime(vip_expiry, '%Y-%m-%d') - datetime.now()).days
    if vip_days_left < 0:
        vip_days_left = 0

    return f"""【目前狀態】
每日免費使用次數：3次（每日凌晨自動重置）
今日已使用次數：{used_count}次
今日剩餘免費次數：{remaining}次
推薦獎勵剩餘次數：{user['recommend_count']}次（透過分享推薦獲得）
客服獎勵剩餘次數：{user['customer_service_count']}次（加入客服獲得）

VIP 到期日：{vip_expiry}（剩{vip_days_left}天）

---

加入客服獲得額外10次使用次數（限1次）：
https://lin.ee/w4elbGV

---

【用戶ID】
{user_id}
"""

if __name__ == "__main__":
    app.run()