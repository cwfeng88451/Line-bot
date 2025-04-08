from flask import Flask, request, abort
import os
import requests
import openai

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

@app.route("/")
def index():
    return "Line GPT Bot is running!"

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    if 'events' not in body:
        return 'OK'

    for event in body['events']:
        if event['type'] == 'message' and event['message']['type'] == 'image':
            reply_token = event['replyToken']
            message_id = event['message']['id']

            image_data = get_image_from_line(message_id)
            if image_data:
                captions = generate_captions_with_openai(image_data)
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
   