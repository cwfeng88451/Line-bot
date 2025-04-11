import os
import base64
import requests
from flask import Flask, request
from dotenv import load_dotenv
import openai

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET or not OPENAI_API_KEY:
    raise ValueError("環境變數未設定完全，請檢查 .env 或 Render 環境變數")

openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def webhook():
    try:
        body = request.get_json(force=True, silent=True)
        print("收到 webhook:", body)

        if not body or 'events' not in body:
            print("body 無資料或格式錯誤")
            return 'OK'

        for event in body['events']:
            if event['type'] == 'message' and event['message']['type'] == 'image':
                reply_token = event['replyToken']
                message_id = event['message']['id']

                image_data = get_image_from_line(message_id)
                if image_data:
                    reply_message = generate_simple_caption_with_openai(image_data)
                    reply_to_line(reply_token, reply_message)
                else:
                    reply_to_line(reply_token, "圖片處理失敗，請稍後再試")
        return 'OK'

    except Exception as e:
        print("Webhook Error:", e)
        return 'Error', 500


def get_image_from_line(message_id):
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("取得 LINE 圖片成功")
        return response.content
    print("取得 LINE 圖片失敗")
    return None


def generate_simple_caption_with_openai(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    prompt = """
請針對這張圖片，產出一段文案。
格式如下：
標題：（10字以內）
內文：（30字以內）
請注意簡潔有力，適合社群貼文。
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=300
    )

    result = response.choices[0].message.content.strip()
    print("OpenAI 產生文案成功")
    return result


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
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        print("LINE 回覆成功")
    else:
        print("LINE 回覆失敗:", response.text)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)