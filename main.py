import os
import requests
from datetime import datetime
import pytz

def send_line_test():
    # GitHubのSecretsからトークンを取得
    token = os.environ.get("LINE_TOKEN")
    
    if not token:
        print("【エラー】LINE_TOKENが設定されていません。SettingsのSecretsを確認してください。")
        return

    # 日本時間を取得
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now = datetime.now(tokyo_tz).strftime('%Y/%m/%d %H:%M:%S')

    # LINE Messaging API の設定
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # 送信内容
    payload = {
        "messages": [
            {
                "type": "text",
                "text": f"✅ システム接続テスト成功！\n\n実行時刻: {now}\nGitHub Actionsからの自動配信に成功しました。これより運行情報の取得フェーズに移行可能です。"
            }
        ]
    }

    print(f"[{now}] LINEへの送信を開始します...")
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        print(f"ステータスコード: {res.status_code}")
        print(f"レスポンス内容: {res.text}")
        
        if res.status_code == 200:
            print(">>> LINEへの送信に成功しました！スマホを確認してください。")
        else:
            print(">>> 送信に失敗しました。トークンが正しいか確認してください。")
            
    except Exception as e:
        print(f"【エラー発生】: {e}")

if __name__ == "__main__":
    send_line_test()
