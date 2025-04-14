import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, ImageMessage, MessageEvent
from dotenv import load_dotenv
import datetime

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

def gpt4o_vision_generate(image_url):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    # 第一步：解析圖片內容
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "請描述這張圖片的主要內容與場景。"},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    }]
    data = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    image_description = response.json()['choices'][0]['message']['content'].strip()

    # 第二步：根據解析內容產生三組文案
    prompt = f"""請根據這張圖片的內容「{image_description}」，產生三組不同風格的文案，每組包含【標題】與【內文】。
標題15字內，內文80字內。
風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
直接依格式輸出：
文案一：
【標題】
【內文】

文案二：
【標題】
【內文】

文案三：
【標題】
【內文】"""

    data2 = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response2 = requests.post(url, headers=headers, json=data2)
    result = response2.json()
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
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "user_name": user_name,
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無",
            "vip_days_left": "0"
        }

    users_data[user_id]["user_name"] = user_name
    users_data[user_id]["used_count"] += 1
    save_users_data(users_data)

    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]

    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f'/tmp/{event.message.id}.jpg'

    with open(image_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    image_url = upload_image_to_imgbb(image_path)
    reply_content = gpt4o_vision_generate(image_url)

    reply_text = config['welcome_text'] + "\n\n"
    reply_text += reply_content + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_commands'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"],
        vip_days_left=users_data[user_id]["vip_days_left"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['add_service_text'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['notes'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_id_display'].format(user_id=user_id, user_name=user_name)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    now = datetime.datetime.now()
    print(f"[{now}] User: {user_id} ({user_name}) 已使用 {users_data[user_id]['used_count']} 次")

def upload_image_to_imgbb(image_path):
    api_key = os.getenv("IMGBB_API_KEY")
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": api_key},
            files={"image": f}
        )
    return response.json()['data']['url']

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))