import os
import base64
import requests
import datetime
from flask import Flask, request
from dotenv import load_dotenv
import openai

load_dotenv()

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COST_PER_POST = float(os.getenv("COST_PER_POST", 0.05))
BALANCE_TWD = float(os.getenv("BALANCE_TWD", 1000))

openai.api_key = OPENAI_API_KEY

users_data = {}
admin_id = "0977419988"  # 管理者 User ID


@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json(force=True, silent=True)
    print("收到 Webhook:", body)

    if 'events' not in body:
        return 'OK'

    for event in body['events']:
        if event['type'] == 'message':
            user_id = event['source']['userId']
            message_type = event['message']['type']
            reply_token = event['replyToken']

            if user_id not in users_data:
                users_data[user_id] = {
                    "vip_expire": None,
                    "recommend_count": 0,
                    "reward_count": 0,
                    "daily_count": 0,
                    "total_used": 0
                }

            text = event['message'].get('text', '')

            if message_type == 'image':
                message_id = event['message']['id']
                reply_image_message(user_id, reply_token, message_id)
            elif text.startswith("管理 "):
                if user_id == admin_id:
                    reply_admin_command(text[3:], reply_token)
                else:
                    reply_message(reply_token, "沒有權限執行此指令")
            elif text in ["功能", "剩餘次數"]:
                reply_user_status(user_id, reply_token)
            elif text == "VIP":
                reply_message(reply_token, "VIP方案: 月費100元，無限次數使用。加入客服了解更多。")
            elif text == "分享":
                share_link = f"https://你的LIFF網址?ref={user_id}"
                share_text = f"免費文案產生工具！每天3次免費，馬上體驗：{share_link}"
                reply_message(reply_token, share_text)

    return 'OK'


def reply_image_message(user_id, reply_token, message_id):
    user = users_data[user_id]
    today = datetime.datetime.now().date()
    if user.get("last_date") != today:
        user["daily_count"] = 0
        user["last_date"] = today

    if is_vip(user):
        pass
    elif user["daily_count"] < 3:
        user["daily_count"] += 1
    elif user["recommend_count"] > 0:
        user["recommend_count"] -= 1
    elif user["reward_count"] > 0:
        user["reward_count"] -= 1
    else:
        reply_message(reply_token, "今日免費次數已用完，升級VIP或分享邀請好友增加次數。")
        return

    user["total_used"] += 1

    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        reply_message(reply_token, "圖片取得失敗，請重試")
        return

    image_bytes = response.content
    content = generate_caption(image_bytes)

    reply_text = f"{content}\n\n每日免費次數:3 已使用:{user['daily_count']} 剩餘:{3-user['daily_count']}\n推薦次數:{user['recommend_count']}\n獎勵次數:{user['reward_count']}\n查看VIP方案請輸入:VIP\n查看分享方式請輸入:分享"

    if user_id == admin_id:
        reply_text += "\n\n" + get_system_statistics() + "\n\n管理者可使用指令：\n管理 增加獎勵 user_id 次數\n管理 設定VIP user_id 天數\n管理 統計"

    reply_message(reply_token, reply_text)

def generate_caption(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "請針對這張圖片產生一個15字內的標題，與一段約40~50字的內文，格式為：標題換行後接內文。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=400
    )

    result = response.choices[0].message.content.strip()
    return result


def reply_admin_command(command, reply_token):
    parts = command.split()
    if parts[0] == "增加獎勵" and len(parts) == 3:
        uid = parts[1]
        count = int(parts[2])
        if uid in users_data:
            users_data[uid]["reward_count"] += count
            reply_message(reply_token, f"已為用戶{uid}增加{count}次獎勵次數")
    elif parts[0] == "設定VIP" and len(parts) == 3:
        uid = parts[1]
        days = int(parts[2])
        if uid in users_data:
            expire = datetime.datetime.now().date() + datetime.timedelta(days=days)
            users_data[uid]["vip_expire"] = expire
            reply_message(reply_token, f"已為用戶{uid}設定VIP至{expire}")
    elif parts[0] == "統計":
        reply_message(reply_token, get_system_statistics())


def get_system_statistics():
    total_users = len(users_data)
    total_posts = sum(u["total_used"] for u in users_data.values())
    usd_spent = total_posts * COST_PER_POST
    usd_balance = get_openai_balance()
    twd_balance = usd_balance * 33
    estimate_posts = int(usd_balance / COST_PER_POST)
    return f"【系統統計資訊】\n目前用戶數:{total_users} 人\n累積文案產生次數:{total_posts} 次\n累積花費約: NT${usd_spent*33:.0f}\nOpenAI餘額:${usd_balance:.2f} 美金 約NT${twd_balance:.0f}\n預估還可產生:{estimate_posts} 篇文案"


def is_vip(user):
    if user["vip_expire"] and user["vip_expire"] >= datetime.datetime.now().date():
        return True
    return False


def get_openai_balance():
    url = "https://api.openai.com/v1/dashboard/billing/credit_grants"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("total_available", 0)
    return 0


def reply_user_status(user_id, reply_token):
    user = users_data[user_id]
    status = "VIP會員" if is_vip(user) else "免費用戶"
    expire = user["vip_expire"] or "無"
    reply_message(reply_token, f"【會員狀態】{status}\nVIP到期日:{expire}\n每日免費次數:3 今日已使用:{user['daily_count']} 剩餘:{3-user['daily_count']}\n推薦次數:{user['recommend_count']}\n獎勵次數:{user['reward_count']}")


def reply_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)