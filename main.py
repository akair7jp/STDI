import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 設定：チェックしたい路線のキーワード
TARGET_LINES = ["東海道線", "御殿場線", "身延線", "東海道新幹線"]

def get_jr_central_status():
    url = "https://traininfo.jr-central.co.jp/zairaisen/index.html?lang=ja"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        status_dict = {}
        lines = soup.find_all('div', class_='line_name')
        for line in lines:
            line_name = line.get_text(strip=True)
            if any(target in line_name for target in TARGET_LINES):
                status_area = line.find_next_sibling('div', class_='status_text')
                status_text = status_area.get_text(strip=True) if status_area else "平常運転"
                status_dict[line_name] = status_text
        return status_dict
    except Exception as e:
        print(f"取得エラー: {e}")
        return None

def send_line(message):
    token = os.environ.get("LINE_TOKEN")
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {"messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    # 日本時間を取得
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now = datetime.now(tokyo_tz)
    time_str = now.strftime('%H:%M')

    # 1. 現在の状況を取得
    current_status = get_jr_central_status()
    if not current_status:
        return

    # 2. 前回の状況を読み込み
    status_file = "last_status.json"
    last_status = {}
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                last_status = json.load(f)
        except:
            last_status = {}

    # 3. 判定ロジック
    # A. 時報の判定 (6:50 または 17:50)
    # ※GitHub Actionsの実行間隔に合わせて「5分以内」の誤差を許容
    is_time_signal = time_str in ["06:50", "06:51", "06:52", "06:53", "06:54", 
                                "17:50", "17:51", "17:52", "17:53", "17:54"]

    # B. 変化の判定
    change_messages = []
    for line, status in current_status.items():
        if status != last_status.get(line):
            change_messages.append(f"【{line}】\n{status}")

    # 4. 送信処理
    if is_time_signal:
        # 時報として全路線の状況を送信
        summary = "\n".join([f"・{l}: {s}" for l, s in current_status.items()])
        msg = f"🔔 定時運行情報（{time_str}現在）\n\n{summary}\n\n本日も安全に。#防災の輪"
        send_line(msg)
        print(f"時報を送信しました: {time_str}")
        
    elif change_messages:
        # 変化があった場合のみ送信
        msg = "⚠️ 運行情報に変化があります\n\n" + "\n---\n".join(change_messages)
        send_line(msg)
        print("変化を検知して送信しました。")

    # 5. 状態を保存
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(current_status, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
