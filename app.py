import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from openai import OpenAI
from datetime import datetime
import pytz

app = Flask(__name__)

# 這些密碼我們等等會放在 Render 主機上，不要直接寫在這裡
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# 設定台灣時區
tw = pytz.timezone('Asia/Taipei')

# --- 這裡設定你的自動作息表 ---
def get_status_by_time():
    now = datetime.now(tw)
    hour = now.hour
    
    # 這裡模擬竹山受訓的作息
    if 5 <= hour < 6:
        return "【自動狀態】我在整理內務跟準備早點名，還沒醒...好想睡。"
    elif 6 <= hour < 8:
        return "【自動狀態】晨跑和早餐時間！正在流汗中，等等回妳。"
    elif 8 <= hour < 12:
        return "【自動狀態】上午操課中（可能在穿消防衣、打繩結或上課），手機被收起來了，中午吃飯馬上回妳！"
    elif 12 <= hour < 14:
        return "【自動狀態】午休時間！如果我沒打給妳，可能是我累到睡著了，別擔心，下午繼續拚。"
    elif 14 <= hour < 18:
        return "【自動狀態】下午體能訓練地獄...快幫我加油，晚上聊。"
    elif 18 <= hour < 19:
        return "【自動狀態】快樂的洗澡吃飯時間～終於能喘口氣了。"
    elif 19 <= hour < 21:
        return "【自動狀態】晚間事務/晚自習，可能快拿到手機了！再等我一下！"
    elif 21 <= hour < 22:
        return "【自動狀態】準備就寢，晚安寶貝，夢裡見。"
    else: # 22:00 - 05:00
        return "【自動狀態】呼...呼...（我睡死囉，噓...明天見！）"

# --- 這裡設定 AI 的大腦 ---
def chat_with_gpt(user_text):
    # 這是給 AI 的指令，讓它扮演你
    system_prompt = f"""
    你現在扮演我的角色，名字叫「廖柏勳」，我是妳的男朋友。
    我現在正在「竹山消防訓練中心」受訓，手機被收起來了，沒辦法立刻回覆訊息。
    我的女朋友正在跟你對話。請遵守以下規則：
    
    1. 語氣要非常溫柔、安撫，帶一點點理工男的幽默。
    2. 絕對不要說「我是一個語言模型」，要說「我是柏勳留在雲端陪妳的分身」。
    3. 如果她說想我，你要回「我也很想妳，受訓很累但想到妳就有動力了」。
    4. 如果她問我在幹嘛，請參考現在的時間回答她（例如正在操課、睡覺）。
    5. 稱呼她「寶貝」或「親愛的」。
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "寶貝抱歉，我的雲端大腦有點秀逗，等我也許就能回覆了！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    reply_text = ""

    # --- 關鍵字觸發區 ---
    if "在哪" in msg or "在幹嘛" in msg or "狀態" in msg:
        reply_text = get_status_by_time()
    elif "愛你" in msg:
        reply_text = "我也愛妳！等我放假回去找妳！"
    else:
        # 其他對話交給 AI
        reply_text = chat_with_gpt(msg)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
