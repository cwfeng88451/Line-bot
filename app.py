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

def reply_image_and_text(reply_token, image_url, text):
    payload = {
        "replyToken": reply_token,
        "messages": [
            {"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url},
            {"type": "text", "text": text}
        ]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

def get_user_status(user_id):
    user = users_data.get(user_id, {})
    vip_expire = user.get("vip_expire", "無")
    recommend = user.get("recommend_count", 0)
    reward = user.get("reward_count", 0)
    add_customer = user.get("add_customer_count", 0)
    total_used = user.get("total_used", 0)

    status = f"""VIP到期日：{vip_expire}
推薦次數：{recommend}
獎勵次數：{reward}
加入客服獎勵次數：{add_customer}
累積使用次數：{total_used}"""
    return status
    
def update_user_count(user_id, count_type, add_count, source):
    user = users_data.setdefault(user_id, {
        "vip_start": None,
        "vip_expire": None,
        "vip_type": None,
        "recommend_count": 0,
        "reward_count": 0,
        "add_customer_count": 0,
        "total_used": 0
    })

    before_count = user.get(count_type, 0)
    user[count_type] = before_count + add_count
    save_users_data()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    log_content = f"""=== 操作紀錄 ===
操作時間：{now}
管理者：U0977419988
目標會員：{user_id}
來源分類：{source}
原有次數：{before_count}
變更後次數：{user[count_type]}
備註：{source}增加{add_count}次使用次數"""
    save_log(log_content)

    return f"操作成功！\n{log_content}"
    
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
                    status = get_user_status(user_id)
                    reply_message(reply_token, f"{config['tips']}\n\n{status}\n\n{config['functions']}\n\n【你的 User ID】{user_id}")
                    
                elif text == "VIP":
                    reply_message(reply_token, f"{config['vip_info']}\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

                elif text == "分享":
                    share_url = f"https://line.me/R/ti/p/@你的LINE官方帳號ID?ref={user_id}"
                    share_text = f"{config['share_text']}\n{share_url}\n\n加入客服獲得額外10次使用次數（限1次）：https://lin.ee/w4elbGV"
                    reply_image_and_text(reply_token, config['share_image'], share_text)

                elif text.startswith("管理 增加客服"):
                    _, _, target_id, count = text.split()
                    reply_message(reply_token, update_user_count(target_id, "add_customer_count", int(count), "加入客服"))

                elif text.startswith("管理 增加推薦"):
                    _, _, target_id, count = text.split()
                    reply_message(reply_token, update_user_count(target_id, "recommend_count", int(count), "推薦好友"))

                elif text.startswith("管理 增加獎勵"):
                    _, _, target_id, count = text.split()
                    reply_message(reply_token, update_user_count(target_id, "reward_count", int(count), "客服額外獎勵"))

                elif text.startswith("管理 查詢"):
                    _, _, target_id = text.split()
                    status = get_user_status(target_id)
                    reply_message(reply_token, status)

                else:
                    reply_message(reply_token, f"{config['tips']}\n\n請輸入正確的指令或上傳圖片進行文案生成！\n\n{config['functions']}\n\n【你的 User ID】{user_id}")

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)