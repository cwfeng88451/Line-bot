import os
import base64
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    print("收到 webhook:", body)

    if 'events' not in body:
        return 'OK'

    for event in body['events']:
        if event['type'] == 'message' and event['message']['type'] == 'image':
            reply_token = event['replyToken']
            message_id = event['message']['id']

            image_data = get_image_from_line(message_id)
            if image_data:
                reply_message = generate_captions_with_deepseek(image_data)
                reply_to_line(reply_token, reply_message)

    return 'OK'


def get_image_from_line(message_id):
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.content if response.status_code == 200 else None


def generate_captions_with_deepseek(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    prompt = """
請針對這張圖片，產出三種不同風格的文案。
每種文案格式如下：
風格類型：
標題：（15-20字內）
內容：（40-50字內）
風格盡量不同，例如：文青風、幽默風、溫暖療癒風。
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "user", "content": {"image": base64_image}}
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
    result = response.json()
    return result['choices'][0]['message']['content']


def reply_to_line(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)