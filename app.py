from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import requests
import datetime
import base64

load_dotenv()

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_USER_ID = "U984188d553a80bf4c6c8fce95e268f9c"  # 管理者ID

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
}

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

config = load_json("config.json")
users_data = load_json("users_data.json")

def save_users_data():
    save_json("users_data.json", users_data)

def reply_message(reply_token, text):
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

def push_message(user_id, text):
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

def get_image_from_line(message_id):
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    return None

def generate_caption(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "請為這張圖片生成一個15字內的標題和一段40-50字的內文，格式為：標題換行後加內文。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            }
        )
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        lines = content.split('\n', 1)
        title = lines[0] if len(lines) > 0 else "【標題】這是一張值得分享的照片"
        text = lines[1] if len(lines) > 1 else "【內文】用照片記錄生活點滴，分享你的故事，讓更多人看見。"
    except:
        title = "【標題】這是一張值得分享的照片"
        text = "【內文】用照片記錄生活點滴，分享你的故事，讓更多人看見。"
    return title, text

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    print(body)

    if "events" not in body:
        return "OK"

    for event in body["events"]:
        user_id = event["source"]["userId"]
        reply_token = event["replyToken"]

        if user_id not in users_data:
            users_data[user_id] = {
                "vip_start": None,
                "vip_expire": None,
                "vip_type": None,
                "recommend_count": 0,
                "reward_count": 0,
                "add_customer_count": 0,
                "total_used": 0
            }
            save_users_data()

        if event["type"] == "message":
            message_type = event["message"]["type"]

            if message_type == "text":
                text = event["message"]["text"]

                if text == "資訊" or text == "剩餘次數":
                    status = f"""VIP到期日：{users_data[user_id].get('vip_expire', '無')}
推薦次數：{users_data[user_id].get('recommend_count', 0)}
獎勵次數：{users_data[user_id].get('reward_count', 0)}
加入客服獎勵次數：{users_data[user_id].get('add_customer_count', 0)}
累積使用次數：{users_data[user_id].get('total_used', 0)}"""
                    reply_message(reply_token, f"{config['tips']}\n\n{status}\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

                elif text == "VIP":
                    reply_message(reply_token, f"{config['vip_info']}\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

                elif text == "分享":
                    share_url = f"https://line.me/R/ti/p/@你的LINE官方帳號ID?ref={user_id}"
                    share_text = f"{config['share_text']}\n{share_url}\n\n加入客服獲得額外10次使用次數（限1次）：https://lin.ee/w4elbGV"
                    reply_message(reply_token, share_text)

                elif text == "管理":
                    if user_id == ADMIN_USER_ID:
                        reply_message(reply_token, "【管理者模式】\n請輸入管理指令，例如：增加次數 查詢用戶 查看統計")
                    else:
                        reply_message(reply_token, "非管理者，無法使用管理功能。")

                else:
                    reply_message(reply_token, f"{config['tips']}\n\n請輸入正確的指令或上傳圖片進行文案生成！\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

            elif message_type == "image":
                reply_message(reply_token, "收到圖片了，正在產生文案，請稍後...")
                message_id = event["message"]["id"]
                image_data = get_image_from_line(message_id)
                if image_data:
                    title, text = generate_caption(image_data)
                    push_message(user_id, f"{title}\n{text}\n\n{config['functions']}\n\n加入客服獲得額外10次使用次數（限1次）：https://lin.ee/w4elbGV\n\n【你的 User ID】{user_id}")

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)