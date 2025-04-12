from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import requests
import datetime

load_dotenv()

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

COST_PER_POST = float(os.getenv("COST_PER_POST", 0.05))
TWD_EXCHANGE_RATE = int(os.getenv("TWD_EXCHANGE_RATE", 33))

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

def save_log(content):
    if not os.path.exists("logs"):
        os.makedirs("logs")
    today = datetime.datetime.now().strftime("%Y%m%d")
    with open(f"logs/record_{today}.txt", "a", encoding="utf-8") as f:
        f.write(content + "\n\n")
        
def reply_message(reply_token, text):
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

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

                else:
                    reply_message(reply_token, f"{config['tips']}\n\n請輸入正確的指令或上傳圖片進行文案生成！\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

            elif message_type == "image":
                reply_message(reply_token, "收到圖片了，正在產生文案，請稍後...")

                result_title = "【標題】AI生成標題"
                result_content = "【內文】AI根據圖片產生的內容，約30-50字。"

                reply_message(reply_token, f"{result_title}\n{result_content}\n\n{config['functions']}\n\n加入客服獲得額外10次使用次數（限1次）：https://lin.ee/w4elbGV\n\n【你的 User ID】{user_id}")

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    