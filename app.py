import os
import json
import base64
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, ImageMessage, MessageEvent
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def gpt4o_image_to_captions(image_base64):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    prompt = """你是一位社群貼文文案創作者。
請根據我提供的圖片內容，產生三篇不同風格的貼文，適合發佈在 Facebook 或 Instagram。

每篇文案請包含：
【標題】約15字內
【內文】約40字內

請直接輸出：
文案一
文案二
文案三
不要加入其他說明。"""
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    users_data = load_users_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": "未設定暱稱",
            "vip": False,
            "vip_start": "",
            "vip_expire": "",
            "daily_used": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "extra_bonus": 0
        }

    user_name = users_data[user_id]["name"]
    users_data[user_id]["daily_used"] += 1
    save_users_data(users_data)

    remaining_count = 3 - users_data[user_id]["daily_used"]

    message_content = line_bot_api.get_message_content(message_id)
    image_binary = b''.join(chunk for chunk in message_content.iter_content())
    image_base64 = base64.b64encode(image_binary).decode('utf-8')

    reply_content = gpt4o_image_to_captions(image_base64)

    reply_text = config['welcome_text'] + "\n\n"
    reply_text += reply_content + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_commands'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=3,
        used_count=users_data[user_id]["daily_used"],
        remaining_count=remaining_count,
        service_bonus=users_data[user_id]["service_bonus"],
        extra_bonus=users_data[user_id]["extra_bonus"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['add_service_text'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['remark'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_id_display'].format(name=user_name, user_id=user_id)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))