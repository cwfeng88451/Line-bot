import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
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

def gpt4o_image_to_text(image_url):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    prompt = f"請詳細描述這張圖片的內容，不需要回答與你是否能看到圖片相關的內容。圖片網址：{image_url}"
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

def generate_captions(topic):
    prompt = f"""請針對以下主題內容，撰寫三組適合社群平台（FB/IG/朋友圈）的貼文，每組包含【標題】與【內文】，字數不限，但需具有故事性、畫面感、情感連結，避免模板式寫法。

主題內容：{topic}

請依格式輸出：
文案一：
【標題】xxx
【內文】xxx

文案二：
【標題】xxx
【內文】xxx

文案三：
【標題】xxx
【內文】xxx
"""
    return gpt4o_image_to_text(prompt)

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
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f'tmp/{event.message.id}.jpg'

    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 上傳 Imgbb 取得 URL
    imgbb_url = os.getenv("IMGBB_URL")
    payload = {
        "image": open(image_path, 'rb').read()
    }
    response = requests.post(imgbb_url, files={"image": open(image_path, 'rb')})
    image_url = response.json()['data']['url']

    topic = gpt4o_image_to_text(image_url)
    captions = generate_captions(topic)

    users_data = load_users_data()
    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無",
            "vip_days_left": "0"
        }

    users_data[user_id]["used_count"] += 1
    users_data[user_id]["remaining_count"] = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]

    save_users_data(users_data)

    reply_text = f"{config['welcome_text']}\n\n{captions}\n{config['separator']}\n{config['user_commands']}\n{config['separator']}\n{config['user_status_format'].format(daily_limit=users_data[user_id]['daily_limit'], used_count=users_data[user_id]['used_count'], remaining_count=users_data[user_id]['remaining_count'], invite_bonus=users_data[user_id]['invite_bonus'], service_bonus=users_data[user_id]['service_bonus'], vip_expiry=users_data[user_id]['vip_expiry'], vip_days_left=users_data[user_id]['vip_days_left'])}\n{config['separator']}\n{config['add_service_text']}\n{config['separator']}\n{config['user_id_display'].format(user_id=user_id, user_name=user_name)}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))