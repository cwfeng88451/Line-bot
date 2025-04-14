# AI看圖寫文案機器人 app.py 最終穩定版
# 功能說明：
# 1. 接收LINE使用者傳來的圖片
# 2. 圖片上傳至OpenAI GPT-4o Vision進行圖片解析
# 3. 自動依據圖片內容生成三組高質感文案
# 4. 回傳文案、使用者狀態、公告、備註至LINE聊天室
# 5. 使用Flask架構，支援完整Log紀錄

# 匯入必要套件
import os
import json
import requests
import base64
import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化Flask應用程式
app = Flask(__name__)

# 設定LINE Messaging API
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 讀取config.json 設定檔
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 讀取users_data.json 使用者資料
def load_users_data():
    with open('users_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 儲存users_data.json 使用者資料
def save_users_data(data):
    with open('users_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# GPT-4o Vision 圖片解析
def gpt4o_image_analysis(image_base64):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    # 給GPT的提示詞（請GPT根據圖片描述內容）
    prompt = "請詳細描述這張圖片的主題與內容，描述畫面細節，作為社群貼文靈感。"

    data = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

# GPT-4o 生成三組文案
def generate_captions(topic):
    prompt = f"""請根據「{topic}」這個主題，產生三組不同風格的社群貼文文案。
每組包含【標題】與【內文】，風格如下：
1. 感性抒情
2. 生活紀錄
3. 激勵勵志
每組文案之間請空兩行，請直接輸出。"""

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

# 處理圖片訊息的主程式
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    users_data = load_users_data()

    # 判斷新使用者，自動初始化狀態
    if user_id not in users_data:
        users_data[user_id] = {
            "daily_limit": 3,
            "used_count": 0,
            "invite_bonus": 0,
            "service_bonus": 0,
            "vip_expiry": "無"
        }

    # 已使用次數+1
    users_data[user_id]["used_count"] += 1
    remaining_count = users_data[user_id]["daily_limit"] - users_data[user_id]["used_count"]

    # 存檔
    save_users_data(users_data)

    # 圖片處理
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f'tmp/{event.message.id}.jpg'
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 圖片轉為Base64
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    # GPT-4o 圖片解析
    topic = gpt4o_image_analysis(image_base64)

    # GPT-4o 生成文案
    captions = generate_captions(topic)
    
    # 組合回覆內容
    reply_text = f"{config['welcome_text']}\n\n"
    reply_text += captions + "\n\n"
    reply_text += f"{config['separator']}\n\n"

    # 使用者可用指令
    reply_text += "\n".join(config['user_commands']) + "\n\n"
    reply_text += f"{config['separator']}\n\n"

    # 使用者狀態格式顯示
    reply_text += config['user_status_format'].format(
        daily_limit=users_data[user_id]["daily_limit"],
        used_count=users_data[user_id]["used_count"],
        remaining_count=remaining_count,
        invite_bonus=users_data[user_id]["invite_bonus"],
        service_bonus=users_data[user_id]["service_bonus"],
        vip_expiry=users_data[user_id]["vip_expiry"]
    ) + "\n\n"

    reply_text += f"{config['separator']}\n\n"

    # 公告區
    reply_text += config['announcement'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"

    # 備註區
    reply_text += config['note'] + "\n\n"
    reply_text += f"{config['separator']}\n\n"

    # 顯示用戶ID與暱稱
    reply_text += f"【用戶ID】{user_id} / 暱稱：{user_name}"

    # 回傳訊息至LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    # Log紀錄
    now = datetime.datetime.now()
    print(f"[{now}] User: {user_id} ({user_name}) 已使用次數: {users_data[user_id]['used_count']}")

# Flask啟動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))