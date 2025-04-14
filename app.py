# 匯入必要的套件
import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from dotenv import load_dotenv
import datetime

# 載入 .env 環境變數
load_dotenv()

# 初始化 Flask 應用程式
app = Flask(__name__)

# LINE API 驗證
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 讀取 config.json 設定檔
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 讀取使用者資料
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 存檔使用者資料
def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# GPT-4o 圖片內容解析 (Vision)
def gpt4o_image_analysis(image_url):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer " + os.getenv('OPENAI_API_KEY'),
        "Content-Type": "application/json"
    }
    prompt = f"請詳細描述這張圖片的主題與內容，作為社群貼文靈感使用，請描述畫面細節。圖片網址：{image_url}"
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# GPT-4o 依據主題生成3組高質感文案
def generate_captions(topic):
    prompt = f"""請根據「{topic}」這個主題，產生三組不同風格的社群貼文文案。
每組包含【標題】與【內文】，風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
每組文案之間請空兩行，請直接輸出："""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer " + os.getenv('OPENAI_API_KEY'),
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

# 接收圖片訊息處理邏輯
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    # 新使用者資料初始化
    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無",
            "vip_days_left": "0"
        }

    # 更新已使用次數
    users_data[user_id]["used_count"] += 1
    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]
    save_users_data(users_data)

    # 儲存圖片暫存
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f'tmp/{event.message.id}.jpg'
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 上傳圖片至 imgbb 取得網址
    imgbb_key = os.getenv("IMGBB_API_KEY")
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        params={"key": imgbb_key},
        files={"image": open(image_path, "rb")}
    )
    image_url = response.json()['data']['url']

    # GPT-4o 分析圖片內容並產文案
    topic = gpt4o_image_analysis(image_url)
    captions = generate_captions(topic)

    # 組合回覆內容
    reply_text = f"{config['welcome_text']}\n\n"
    reply_text += captions + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += "\n".join(config['user_commands']) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"]
    ) + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += config['note'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"
    reply_text += f"【用戶ID】{user_id} / 暱稱：{user_name}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    # 紀錄 Log
    now = datetime.datetime.now()
    print(f"[{now}] User: {user_id} ({user_name}) 已使用次數: {users_data[user_id]['used_count']}")

# 啟動 Flask 應用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))