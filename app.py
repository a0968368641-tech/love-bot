import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from openai import OpenAI
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# 讀取環境變數 (GIRL_ID 等你查到後，再去 Render 補填)
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
target_user_id = os.environ.get('GIRL_ID') 

tw = pytz.timezone('Asia/Taipei')

# === 1. 早安情話庫 (隨機抽選，讓她每天有新鮮感) ===
morning_msgs = [
    "寶貝早安～今天要開心得過喔！受訓的時候我也會想妳的。",
    "早安！新的一天開始了，記得吃早餐，不要餓肚子囉！",
    "起床了嗎小懶豬？早安～今天也要充滿元氣，加油！",
    "寶貝早安，昨晚睡得好嗎？雖然我不在，但心一直陪著妳喔。",
    "早安！今天天氣多變化，出門記得確認一下有沒有帶傘喔～",
    "早安安～受訓雖然累，但想到還有妳在等我，我就充滿電力了！",
    "寶貝早安（捏臉），今天也要開開心心的，不可以皺眉頭喔。",
    "早安！傳送滿滿的能量給妳，如果遇到討厭的事，心裡默念我的名字三次 XD",
    "哈囉寶貝早安～記得多喝水，照顧好自己，我會擔心的。",
    "早安！再過幾天就能見面了，為了這個目標，我們今天一起加油！"
]

# === 2. 定時任務：發送早安 ===
def send_morning_greeting():
    if not target_user_id:
        print("尚未設定 GIRL_ID，跳過早安")
        return
    
    msg = random.choice(morning_msgs)
    full_msg = f"【自動排程：早安服務】\n{msg}\n(來自工科男友的雲端早安)"
    
    try:
        line_bot_api.push_message(target_user_id, TextSendMessage(text=full_msg))
        print("早安發送成功")
    except Exception as e:
        print(f"早安發送失敗: {e}")

# === 3. 定時任務：發送晚安 (寒流提醒) ===
def send_evening_greeting():
    if not target_user_id:
        return
    
    msg = "寶貝晚安 🌙\n最近可能有寒流或溫差大，睡覺要注意保暖，蓋好被子喔！\n(機器人準備進入休眠模式...夢裡見！)"
    
    try:
        line_bot_api.push_message(target_user_id, TextSendMessage(text=msg))
        print("晚安發送成功")
    except Exception as e:
        print(f"晚安發送失敗: {e}")

# === 4. 啟動定時器 (每天 08:00 和 23:00) ===
scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(send_morning_greeting, 'cron', hour=8, minute=0)
scheduler.add_job(send_evening_greeting, 'cron', hour=23, minute=0)
scheduler.start()

# === 5. 作息狀態查詢 ===
def get_status_by_time():
    now = datetime.now(tw)
    hour = now.hour
    if 5 <= hour < 6: return "【自動狀態】我在整理內務跟準備早點名，還沒醒...好想睡。"
    elif 6 <= hour < 8: return "【自動狀態】晨跑和早餐時間！正在流汗中，等等回妳。"
    elif 8 <= hour < 12: return "【自動狀態】上午操課中（手機被收起來了），中午吃飯馬上回妳！"
    elif 12 <= hour < 14: return "【自動狀態】午休時間！可能累到睡著了，下午繼續拚。"
    elif 14 <= hour < 18: return "【自動狀態】下午體能訓練地獄...快幫我加油。"
    elif 18 <= hour < 19: return "【自動狀態】快樂的洗澡吃飯時間～"
    elif 19 <= hour < 21: return "【自動狀態】晚間事務/晚自習，可能快拿到手機了！"
    elif 21 <= hour < 22: return "【自動狀態】準備就寢，晚安寶貝。"
    else: return "【自動狀態】呼...呼...（我睡死囉，噓...）"

# === 6. AI 對話邏輯 ===
def chat_with_gpt(user_text):
    system_prompt = f"""
    你現在扮演我的角色「廖柏勳」，我是妳的工科男朋友。
    我正在「竹山消防訓練中心」受訓。
    請用溫柔、安撫、帶點理工男幽默的語氣回覆。
    如果是關於天氣的問題，請提醒她去查氣象局，並說你會擔心她冷到。
    絕不要說你是AI，要說是「雲端分身」。
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}]
        )
        return response.choices[0].message.content
    except:
        return "機器人大腦暫時短路中...等我一下！"

# === 7. LINE Webhook 接口 ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# === 8. 處理訊息 (含查ID密技) ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    user_id = event.source.user_id
    
    # --- 密技：輸入「查ID」來獲取她的 User ID ---
    if msg == "查ID":
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text=f"您的 User ID 是：\n{user_id}\n\n(請把這串 ID 複製起來，拿去 Render 設定 GIRL_ID)")
        )
        return
    # ------------------------------------------

    if "在哪" in msg or "在幹嘛" in msg or "狀態" in msg:
        reply = get_status_by_time()
    else:
        reply = chat_with_gpt(msg)

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# === 9. 為了防止機器人睡著的網址 ===
@app.route("/")
def home():
    return "Bot is alive!", 200

if __name__ == "__main__":
    app.run()
