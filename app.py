import os
import json
import requests
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging.models import TextSendMessage, ImageMessage, MessageEvent

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

line_bot_api = MessagingApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# GPT-3.5 產生文案
def chatgpt_generate(prompt, model="gpt-3.5-turbo"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# GPT-4o 圖片解析（模擬）
def gpt4o_image_to_text(image_url):
    prompt = "請描述這張圖片的主題與關鍵詞，簡短即可。"
    return "黃昏、公路、夕陽、車燈、旅程"

# 自動產生三組風格文案
def generate_caption(topic):
    prompt = f"""請針對主題「{topic}」產生三組不同風格的文案，每組包含【標題】與【內文】。
每個標題15字內，內文40字內。
風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
直接依格式輸出："""
    return chatgpt_generate(prompt)

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
    topic = gpt4o_image_to_text("圖片網址")  # 圖片處理待擴充

    reply_text = config['welcome_text'] + "\n\n"
    reply_text += generate_caption(topic)
    reply_text += f"\n{config['separator']}\n"
    reply_text += config['user_commands']
    reply_text += f"\n{config['separator']}\n"
    reply_text += config['user_status_format'].format(
        daily_limit=3,
        used_count=1,
        remaining_count=2,
        invite_bonus=3,
        service_bonus=5,
        vip_expiry="無",
        vip_days_left="0"
    )
    reply_text += f"\n{config['separator']}\n"
    reply_text += config['add_service_text']
    reply_text += f"\n{config['separator']}\n"
    reply_text += config['user_id_display'].format(user_id=user_id)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))