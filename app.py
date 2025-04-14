import os
import json
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

def gpt4o_image_to_text(image_url):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "請描述這張圖片的主要內容，並提取可作為貼文主題的重點。"},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    }]
    data = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

def generate_caption(topic):
    prompt = f"""請針對主題「{topic}」產生三組不同風格的貼文文案，每組包含【標題】與【內文】。
每組標題15字內，內文80字內。
風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
直接依格式輸出："""
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
    image_path = f'/tmp/{event.message.id}.jpg'

    with open(image_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    image_url = upload_image_to_imgbb(image_path)
    topic = gpt4o_image_to_text(image_url)
    captions = generate_caption(topic)

    reply_text = config['welcome_text'] + "\n\n"
    reply_text += captions + "\n"
    reply_text += config['separator'] + "\n"
    reply_text += config['user_commands'] + "\n"
    reply_text += config['separator'] + "\n"
    reply_text += config['user_status_format'].format(
        daily_limit=3,
        used_count=1,
        remaining_count=2,
        invite_bonus=0,
        service_bonus=0,
        vip_expiry="無",
        vip_days_left="0"
    ) + "\n"
    reply_text += config['separator'] + "\n"
    reply_text += config['add_service_text'] + "\n"
    reply_text += config['separator'] + "\n"
    reply_text += config['user_id_display'].format(user_id=user_id, user_name=user_name)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

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