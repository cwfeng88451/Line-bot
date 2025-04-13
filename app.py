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

# 讀取 config.json 設定檔
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 會員資料處理
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# GPT-3.5 自動產文
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

# GPT-4o 圖片解析模擬
def gpt4o_image_to_text(image_url):
    return "黃昏、公路、夕陽、車燈、旅程"

# 自動產生三組不同風格文案
def generate_caption(topic):
    prompt = f"""請針對主題「{topic}」產生三組不同風格的文案，每組包含【標題】與【內文】。
每個標題15字內，內文40字內。
風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
直接依格式輸出："""
    return chatgpt_generate(prompt)

# Line Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 圖片訊息處理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    topic = gpt4o_image_to_text("圖片網址")

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

# Render 部署執行
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))