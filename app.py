# AI看圖寫文案機器人 app.py 最終正式版
# 功能：接收LINE圖片 → 轉Base64 → 傳送至GPT-4o Vision解析 → 生成三組高質感文案 → 回傳至LINE聊天室

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

# 初始化Flask應用
app = Flask(__name__)

# 設定LINE API
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 載入config設定
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

# 圖片傳送至GPT-4o Vision解析
def gpt4o_image_analysis(image_base64):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    prompt = "請詳細描述這張圖片的主題與內容，描述畫面細節，作為社群貼文靈感。"
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

# GPT-4o 根據主題生成3組文案
def generate_captions(topic):
    prompt = f"""請根據「{topic}」這個主題，產生三組不同風格的社群貼文文案。
每組包含【標題】與【內文】，風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
每組文案之間請空兩行，請直接輸出："""

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

# Flask主路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 接收LINE圖片事件
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    # 初始化新使用者資料
    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無"
        }

    users_data[user_id]["used_count"] += 1
    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]
    save_users_data(users_data)

    # 獲取LINE圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = b""
    for chunk in message_content.iter_content():
        image_data += chunk

    # 圖片轉Base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    # 圖片解析取得主題
    topic = gpt4o_image_analysis(image_base64)

    # GPT-4o產生文案
    captions = generate_captions(topic)

    # 回覆文字整合
    reply_text = f"{config['welcome_text']}\n\n"
    reply_text += captions + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "\n".join(config['user_commands']) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['note'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += f"【用戶ID】{user_id} / 暱稱：{user_name}"

    # 回覆至LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 執行Flask應用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))