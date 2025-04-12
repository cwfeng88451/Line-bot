from flask import Flask, request, abort
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, ImageMessage, TextSendMessage
)

app = Flask(__name__)

# 請替換為您的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

# 模擬使用者資料庫
user_data = {
    'U984188d553a80bf4c6c8fce95e268f9c': {
        'used_count': 2,
        'recommend_count': 3,
        'customer_service_count': 5,
        'vip_expiry': '2025-05-01'
    }
}

# 每日免費使用次數
DAILY_FREE_LIMIT = 3

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭值
    signature = request.headers['X-Line-Signature']

    # 取得請求主體內容
    body = request.get_data(as_text=True)

    # 處理 webhook 主體
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id

    # 取得使用者資料，若無則初始化
    data = user_data.get(user_id, {
        'used_count': 0,
        'recommend_count': 0,
        'customer_service_count': 0,
        'vip_expiry': '2025-05-01'
    })

    # 計算剩餘免費次數
    remaining_free = DAILY_FREE_LIMIT - data['used_count']
    if remaining_free < 0:
        remaining_free = 0

    # 計算 VIP 剩餘天數
    vip_expiry_date = datetime.strptime(data['vip_expiry'], '%Y-%m-%d')
    days_left = (vip_expiry_date - datetime.now()).days
    if days_left < 0:
        days_left = 0

    # 產生標題與內文（此處為範例，實際應根據圖片內容生成）
    title = "午後陽光的溫度"
    content = "靜靜地坐在窗邊，讓陽光灑滿心房，這就是生活的溫柔片刻。"

    # 組合回覆訊息
    reply_text = f"""【標題】{title}
【內文】{content}

---

【使用者可用指令】
（1）資訊 - 查看個人狀態
（2）VIP - 查看 VIP 方案
（3）分享 - 產生分享推薦鏈結（系統自動統計透過分享添加機器人的數量）

---

【目前狀態】
每日免費使用次數：{DAILY_FREE_LIMIT}次（每日凌晨自動重置）
今日已使用次數：{data['used_count']}次
今日剩餘免費次數：{remaining_free}次
推薦獎勵剩餘次數：{data['recommend_count']}次（透過分享推薦獲得）
客服獎勵剩餘次數：{data['customer_service_count']}次（加入客服獲得）

VIP 到期日：{data['vip_expiry']}（剩{days_left}天）

---

加入客服獲得額外10次使用次數（限1次）：
https://lin.ee/w4elbGV

---

【用戶ID】
{user_id}
"""

    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    # 更新使用者已使用次數
    data['used_count'] += 1
    user_data[user_id] = data

if __name__ == "__main__":
    app.run()