# app.py 第一段

import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 讀取 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 讀取 users_data.json
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 儲存 users_data.json
def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 取得 GPT 產文
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
    
# app.py 第二段

# 處理圖片內容 GPT-4o
def gpt4o_image_to_text(image_url):
    prompt = "請描述這張圖片的場景與主題，提供關鍵詞，不用太長。"
    # 這裡請串接你 GPT-4o 圖片解析 API
    return "黃昏、高速公路、夕陽、車輛、遠方、寧靜"

# 自動產生三種風格文案
def generate_caption(topic):
    prompt = f"""請針對主題「{topic}」產生三組不同風格的文案，每組包含【標題】與【內文】。
每個標題約15字內，內文約40字內。
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
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    image_path = f'tmp/{message_id}.jpg'
    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    image_url = "你的圖片存放網址"  # 可用 imgur、s3、自架空間
    topic = gpt4o_image_to_text(image_url)
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
    app.run()