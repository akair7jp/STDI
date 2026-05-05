import os
import requests

def main():
    # GitHubのSettingsからトークンを読み込む
    token = os.environ.get("LINE_TOKEN")
    
    # 1. そもそもトークンがあるかチェック
    if not token:
        print("エラー: LINE_TOKENが空っぽです！GitHubのSecretsを確認してください。")
        return

    print(f"トークンを取得しました（先頭4文字）: {token[:4]}...")

    # 2. LINEに送る内容
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "messages": [{"type": "text", "text": "【テスト送信】接続テストに成功しました！これが届けば準備完了です。"}]
    }

    # 3. 実際に送信
    print("LINEに送信リクエストを送っています...")
    res = requests.post(url, headers=headers, json=payload)
    
    # 4. 結果を画面に出す
    print(f"LINEからの返事（ステータスコード）: {res.status_code}")
    print(f"LINEからの詳細メッセージ: {res.text}")

if __name__ == "__main__":
    main()
