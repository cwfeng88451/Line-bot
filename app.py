# 載入必要套件
import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from dotenv import load_dotenv
import datetime

# 讀取環境變數
load_dotenv()

# 啟動 Flask 應用
app = Flask(__name__)

# 初始化 LINE API 與 Webhook 驗證
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 讀取 config.json 設定檔
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 讀取 users_data.json 使用者資料
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 儲存 users_data.json 使用者資料
def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 使用 GPT-4o Vision 解析圖片內容
def gpt4o_image_analysis(image_url):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    # 初步解析圖片內容
    prompt = f"請詳細描述這張圖片的主題與內容，給我可用於社群貼文的素材與重點。圖片網址：{image_url}"
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# 根據主題產生三組高質感文案
def generate_captions(topic):
    prompt = f"""請根據主題「{topic}」撰寫三組社群貼文文案。
每組包含【標題】與【內文】。
風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
標題15字內，內文80字內，避免模板式內容。
直接依格式輸出："""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# Flask 路由設定
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無",
            "vip_days_left": "0"
        }

    # 增加已使用次數
    users_data[user_id]["used_count"] += 1
    save_users_data(users_data)

    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]

    # 下載 LINE 上傳的圖片
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f'tmp/{event.message.id}.jpg'

    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 上傳至 imgbb 取得公開圖片網址
    imgbb_key = os.getenv("IMGBB_API_KEY")
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        params={"key": imgbb_key},
        files={"image": open(image_path, "rb")}
    )
    image_url = response.json()['data']['url']

    # 圖片解析與文案生成
    topic = gpt4o_image_analysis(image_url)
    captions = generate_captions(topic)

    # 回覆訊息格式
    reply_text = f"{config['welcome_text']}\n\n"
    reply_text += captions + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_commands'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"],
        vip_days_left=users_data[user_id]["vip_days_left"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['add_service_text'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['notes'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_id_display'].format(user_id=user_id, user_name=user_name)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    # Log 紀錄
    now = datetime.datetime.now()
    print(f"[{now}] User: {user_id} ({user_name}) 已使用次數: {users_data[user_id]['used_count']}")

# 啟動程式
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))