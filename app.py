from flask import Flask, request
import os
import requests
import openai
import base64
from dotenv import load_dotenv

# 載入.env檔案
load_dotenv()

# 讀取環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 檢查環境變數是否存在
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET or not OPENAI_API_KEY:
    raise ValueError("環境變數未設定完全，請檢查 .env 或 Render 環境變數設定")

# 設定 OpenAI Key
openai.api_key = OPENAI_API_KEY

# Flask啟動
app = Flask(__name__)

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
                captions = generate_captions_with_openai(image_data)
                reply_message = "\n\n".join([f"文案 {i+1}：{txt}" for i, txt in enumerate(captions)])
                reply_to_line(reply_token, reply_message)

    return 'OK'


def get_image_from_line(message_id):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        return None


def generate_captions_with_openai(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    response = openai.chat.completions.create(
    model="gpt-4-turbo-vision"
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "請根據這張圖片產出三種風格不同的文案，每則約100字，風格分別是感性、故事、社群貼文。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=800
    )

    results = response.choices[0].message.content.strip()
    return results.split('\n\n')


def reply_to_line(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    requests.post(url, headers=headers, json=body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)