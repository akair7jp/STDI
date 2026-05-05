import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import pytz

# タイムゾーン設定（日本時間）
JST = pytz.timezone('Asia/Tokyo')
now = datetime.datetime.now(JST)

# LINE設定
LINE_TOKEN = os.environ["LINE_TOKEN"]
STATUS_FILE = "last_status.json"

def get_train_status():
    """各社のサイトから運行情報を取得する（簡易版ロジック）"""
    # ここでは例として主要路線の辞書を作成
    # 実際にはここで各社のURLをBeautifulSoupで解析します
    lines = {
        "東海道本線(熱海〜豊橋)": {"status": "平常", "section": "全線", "reason": "", "resume": ""},
        "身延線(富士〜西富士宮)": {"status": "平常", "section": "全線", "reason": "", "resume": ""},
        "御殿場線(沼津〜国府津)": {"status": "平常", "section": "全線", "reason": "", "resume": ""},
        "静岡鉄道": {"status": "平常", "section": "全線", "reason": "", "resume": ""},
        "駿豆線": {"status": "平常", "section": "全線", "reason": "", "resume": ""},
        "伊東線": {"status": "平常", "section": "全線", "reason": "", "resume": ""}
    }
    
    # --- スクレイピング例（JR東海） ---
    try:
        res = requests.get("https://traininfo.jr-central.co.jp/zairaisen/index.html?area=4")
        # JR東海の詳細解析は複雑なため、ここでは「平常」か否かの判定ロジックをシミュレート
        # 実際にはサイトのHTML構造に合わせて更新が必要
    except:
        pass
        
    return lines

def send_line(text):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"messages": [{"type": "text", "text": text}]}
    requests.post(url, headers=headers, json=payload)

def main():
    current_info = get_train_status()
    
    # 前回の状態を読み込み
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            last_info = json.load(f)
    else:
        last_info = {}

    # 1. 時報配信 (7時、18時)
    if now.minute < 10 and (now.hour == 7 or now.hour == 18):
        report = f"【定期運行情報】({now.strftime('%H:%M')})\n"
        for line, info in current_info.items():
            report += f"・{line}: {info['status']}\n"
        send_line(report)

    # 2. 変化の検知
    for line, info in current_info.items():
        prev = last_info.get(line, {"status": "平常", "section": "全線", "reason": ""})
        
        # 平常 → 遅延/見合わせ
        if prev["status"] == "平常" and info["status"] != "平常":
            if "見合わせ" in info["status"]:
                msg = f"【運転見合わせ】\n路線名：{line}\n区間：{info['section']}\n理由：{info['reason']}\n再開見込み：{info['resume']}"
            else:
                msg = f"【遅延発生】\n路線名：{line}\n区間：{info['section']}\n理由：{info['reason']}"
            send_line(msg)
            
        # 解消判定
        elif prev["status"] != "平常" and info["status"] == "平常":
            msg = f"【事象解消】\n路線名：{line}\n区間：{prev['section']}\n理由：{prev['reason']}\n運転再開（遅延解消）しました。"
            send_line(msg)

    # 状態保存
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(current_info, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
