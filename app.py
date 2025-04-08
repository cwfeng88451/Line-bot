from flask import Flask, request, abort
import os
import requests
import openai

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    print("Received webhook body:", body)  # 印出收到的內容

    if 'events' not in body:
        print("No events found in body")
        return 'OK'

    for event in body['events']:
        print("Event received:", event)  # 看每一個 event 是什麼
        if event['type'] == 'message' and event['message']['type'] == 'image':
            print("Image message detected")  # 看有沒有走到這裡
            reply_token = event['replyToken']
            message_id = event['message']['id']

            image_data = get_image_from_line(message_id)
            if image_data:
                print("Image data fetched, sending to GPT")
                captions = generate_captions_with_openai(image_data)
                print("Captions returned:", captions)
                reply_message = "\n\n".join([f"文案 {i+1}：{txt}" for i, txt in enumerate(captions)])
                reply_to_line(reply_token, reply_message)

    return 'OK'

def get_image_from_line(message_id):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.content
    else:
        return None 
        
import base64

def generate_captions_with_openai(image_bytes):
    print("===> 開始處理圖片，準備轉 base64")
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    print("===> 呼叫 OpenAI API...")
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "請根據這張圖片產出三種風格不同的文案，每則約 100 字。風格可以是感性、故事敘述、社群貼文風格。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=800
    )

    print("===> 收到 OpenAI 回傳")
    results = response.choices[0].message.content.strip()
    return results.split('\n\n')
    
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)