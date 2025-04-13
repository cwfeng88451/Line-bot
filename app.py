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

def gpt4o_image_to_text(image_path):
    # 模擬 GPT-4o 圖片解析（此處自行擴充為真實圖片處理邏輯）
    return "黃昏、公路、夕陽、車燈、旅程"

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
    message_id = event.message.id
    users_data = load_users_data()
    user_name = users_data.get(user_id, {}).get("name", "未設定暱稱")

    # 下載圖片並暫存
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    image_path = f'tmp/{message_id}.jpg'
    message_content = line_bot_api.get_message_content(message_id)
    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # GPT-4o 圖片解析（模擬）
    topic = gpt4o_image_to_text(image_path)

    reply_text = config['welcome_text'] + "\n\n"
    reply_text += generate_caption(topic) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_commands'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=3,
        used_count=users_data.get(user_id, {}).get("daily_used", 0),
        remaining_count=3 - users_data.get(user_id, {}).get("daily_used", 0),
        service_bonus=users_data.get(user_id, {}).get("service_bonus", 0),
        extra_bonus=users_data.get(user_id, {}).get("extra_bonus", 0)
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