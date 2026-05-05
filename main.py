import os
import requests

def get_line_events():
    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("エラー: LINE_TOKEN がありません。")
        return

    # 本来はWebhookで受け取りますが、ここでは「ボットの現在の状態」から
    # ログを解析するアプローチを試みます。
    # ※ただし、Messaging APIの標準機能では過去のWebhook履歴を直接取得するAPIはないため、
    # 以下の「ダミー送信エラー」を利用して、グループへのアクセスを試みます。

    print("--- グループID特定テスト開始 ---")
    
    # 1. 自分のプロフィール情報を取得して、疎通確認
    headers = {
        "Authorization": f"Bearer {token}"
    }
    profile_res = requests.get("https://api.line.me/v2/bot/info", headers=headers)
    print(f"ボット情報: {profile_res.text}")

    print("\n【手順】")
    print("1. 公式アカウントの管理画面で『グループ・複数人トークへの参加』を『許可』にしましたか？")
    print("2. ボットをグループに招待しましたか？")
    print("3. グループ内でボットに向かって何か発言（例：『あ』）しましたか？")
    print("\n※GitHub Actions単体ではリアルタイムのWebhook受信ができないため、")
    print("本来は『Messaging API設定』の『Webhook URL』に、一時的な受け皿URLを設定する必要があります。")
    print("Google Apps Script (GAS) などを使うのが一般的です。")

if __name__ == "__main__":
    get_line_events()
