import os
import base64
import requests
from flask import Flask, request
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET or not DEEPSEEK_API_KEY:
    raise ValueError("環境變數未設定完全，請檢查 .env 或 Render 環境變數")

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
                    reply_message = generate_captions_with_deepseek(image_data)
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

    if response.status_code == 200:
        result = response.json()
        print("DeepSeek 回傳成功")
        return result['choices'][0]['message']['content']
    else:
        print("DeepSeek 回傳失敗:", response.text)
        return "文案生成失敗，請稍後再試"


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