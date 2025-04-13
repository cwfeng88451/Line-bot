from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage, ImageSendMessage
import os
import json
import datetime
import requests
import openai
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# 資料檔案位置
DATA_FILE = 'users_data.json'
LIST_FILE = 'users_list.txt'
CONFIG_FILE = 'config.json'
LOG_FOLDER = 'logs/'

lock = threading.Lock()

# 讀取設定檔
def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 儲存使用者資料
def save_user_data(data):
    with lock:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# 讀取使用者資料
def load_user_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 紀錄 log
def write_log(user_id, action, content):
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(LOG_FOLDER, f"{today}.txt")
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[{time}] 管理者 {action}\n會員：{user_id}\n{content}\n\n")

# 取得今日日期
def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

# 計算 VIP 剩餘天數
def calculate_vip_days(vip_expire):
    today = datetime.datetime.now().date()
    expire_date = datetime.datetime.strptime(vip_expire, "%Y-%m-%d").date()
    return (expire_date - today).days
    
# 取得 LINE 使用者名稱
def get_user_profile(user_id):
    profile = line_bot_api.get_profile(user_id)
    return profile.display_name

# 回覆訊息
def reply_text(reply_token, text):
    line_bot_api.reply_message(reply_token, TextSendMessage(text=text))

# 回覆圖片
def reply_image(reply_token, image_url, text):
    line_bot_api.reply_message(reply_token, [
        ImageSendMessage(original_content_url=image_url, preview_image_url=image_url),
        TextSendMessage(text=text)
    ])

# 處理使用者圖片訊息
def handle_image(event, user_id, user_data, config, vip_mode):
    daily_limit = config["daily_limit"]
    max_texts = config["vip_texts"] if vip_mode else config["user_texts"]

    today = get_today()
    if user_data[user_id]["date"] != today:
        user_data[user_id]["date"] = today
        user_data[user_id]["used"] = 0

    used = user_data[user_id]["used"]
    extra = user_data[user_id]["recommend"] + user_data[user_id]["customer"] + user_data[user_id]["reward"]
    vip_expire = user_data[user_id].get("vip_expire", "")

    if not vip_mode and used >= daily_limit and extra <= 0:
        reply_text(event.reply_token, "今日免費使用次數已用完，升級 VIP 或推薦好友可獲得更多次數。")
        return

    # 模擬取得圖片（此範例略過圖片處理細節）
    img_url = "https://example.com/image.jpg"

    # 模擬生成文案
    reply_msg = f"{config['welcome_text']}\n（每日免費使用次數：{daily_limit}）\n"
    for i in range(1, max_texts + 1):
        reply_msg += f"\n【標題】AI範例標題{i}\n【內文】AI自動產生的文案內容{i}。\n"

    reply_msg += f"\n{config['separator']}\n{config['user_commands']}\n"
    reply_msg += f"\n{config['separator']}\n{config['user_status_format'].format(daily_limit=daily_limit, used_count=used+1, remaining_count=daily_limit-used-1, invite_bonus=user_data[user_id]['recommend'], service_bonus=user_data[user_id]['customer'], reward_bonus=user_data[user_id]['reward'], vip_expiry=vip_expire, vip_days_left=calculate_vip_days(vip_expire) if vip_expire else 0)}\n"
    reply_msg += f"\n加入客服，申請額外10次免費使用次數（限1次）\n加入網址：https://lin.ee/w4elbGV\n"
    reply_msg += f"\n【用戶資料】{user_data[user_id]['name']} ({user_id})\n"
    reply_msg += f"\n{config['separator']}\n【公告】{config['announcement']}\n【備註】{config['extra_notes']}\n"

    reply_image(event.reply_token, img_url, reply_msg)

    # 更新使用次數
    if not vip_mode:
        if used < daily_limit:
            user_data[user_id]["used"] += 1
        else:
            if user_data[user_id]["recommend"] > 0:
                user_data[user_id]["recommend"] -= 1
            elif user_data[user_id]["customer"] > 0:
                user_data[user_id]["customer"] -= 1
            elif user_data[user_id]["reward"] > 0:
                user_data[user_id]["reward"] -= 1

    save_user_data(user_data)

# Webhook 接收處理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()