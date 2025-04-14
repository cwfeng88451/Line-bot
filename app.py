# AI看圖寫文案機器人 最終優化版 app.py
# 功能：
# 1. 接收LINE圖片 → 轉Base64 → 傳至GPT-4o Vision解析
# 2. 自動產生【文案一】~【文案三】
# 3. 每段包含【標題】+【內文】（30~35字內）
# 4. 排版整齊，社群貼文最佳格式

import os
import json
import requests
import base64
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化Flask
app = Flask(__name__)

# LINE API金鑰
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 載入config.json設定
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 載入使用者資料
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 儲存使用者資料
def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# GPT-4o Vision解析圖片取得主題
def gpt4o_image_analysis(image_base64):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    prompt = "請詳細描述這張圖片的主題內容，畫面細節，用於社群貼文靈感。"

    data = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# GPT-4o產生3段文案
def generate_captions(topic):
    prompt = f"""請針對主題「{topic}」產生三段社群貼文文案。
每段包含【標題】與【內文】，內文限制30~35字內。
輸出格式如下：
【文案一】
【標題】xxxxxx
【內文】xxxxxx

【文案二】
【標題】xxxxxx
【內文】xxxxxx

【文案三】
【標題】xxxxxx
【內文】xxxxxx
"""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# Flask路由處理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 接收LINE圖片並處理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    # 初次使用者新增
    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無"
        }

    # 更新次數
    users_data[user_id]["used_count"] += 1
    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]
    save_users_data(users_data)

    # 獲取圖片並轉Base64
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = b""
    for chunk in message_content.iter_content():
        image_data += chunk
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    # 圖片解析
    topic = gpt4o_image_analysis(image_base64)

    # 產生文案
    captions = generate_captions(topic)

    # 組合回覆內容
    reply_text = f"{config['welcome_text']}\n\n"
    reply_text += captions + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "【使用者可用指令】\n" + "\n".join(config['user_commands']) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "【目前狀態】\n" + config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "【公告區】\n" + config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "【備註區】\n" + config['note'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += f"【用戶ID】{user_id} / 暱稱：{user_name}"

    # 回覆LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 啟動Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))