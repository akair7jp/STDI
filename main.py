import os
import re
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_FILE = "last_status.json"
TIMEZONE = ZoneInfo("Asia/Tokyo")
LINE_TOKEN = os.environ.get("LINE_TOKEN")

TARGET_LINES = {
    "東海道本線": {
        "section": "熱海〜豊橋",
        "source": "JR東海",
        "aliases": ["東海道線", "東海道本線"],
    },
    "身延線": {
        "section": "富士〜西富士宮",
        "source": "JR東海",
        "aliases": ["身延線"],
    },
    "御殿場線": {
        "section": "沼津〜国府津",
        "source": "JR東海",
        "aliases": ["御殿場線"],
    },
    "静岡鉄道 静岡清水線": {
        "section": "新清水〜新静岡",
        "source": "静岡鉄道",
        "aliases": ["静岡鉄道", "静岡清水線", "静鉄電車", "静鉄"],
    },
    "伊豆箱根鉄道 駿豆線": {
        "section": "三島〜修善寺",
        "source": "伊豆箱根鉄道",
        "aliases": ["駿豆線", "伊豆箱根鉄道"],
    },
    "伊東線": {
        "section": "熱海〜伊東",
        "source": "JR東日本",
        "aliases": ["伊東線"],
    },
}

URLS = {
    "jr_central": "https://traininfo.jr-central.co.jp/zairaisen/index.html?lang=ja",
    "jr_east": "https://traininfo.jreast.co.jp/train_info/kanto.aspx",
    "shizutetsu": "https://train.shizutetsu.co.jp/news/newslist/important",
    "izuhakone": "https://www.izuhakone.co.jp/izu-group/izu-operation/p001055.html",
}


def fetch_html(url):
    headers = {"User-Agent": "Mozilla/5.0 train-status-line-bot/1.0"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    return res.text


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_status(text):
    text = clean_text(text)

    if not text:
        return "不明"

    if any(word in text for word in ["運転見合わせ", "運転を見合わせ", "見合わせ"]):
        return "運転見合わせ"

    if any(word in text for word in ["運転再開", "再開しました", "運転を再開"]):
        return "運転再開"

    if any(word in text for word in ["遅延", "遅れ"]):
        return "遅延"

    if "運休" in text:
        return "運休"

    if any(word in text for word in ["平常", "通常どおり", "通常通り", "平常通り", "情報はありません"]):
        return "平常運転"

    return "その他"


def extract_reason(text):
    text = clean_text(text)

    patterns = [
        r"(.+?の影響)",
        r"(.+?のため)",
        r"(.+?により)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1)

    if normalize_status(text) == "平常運転":
        return "なし"

    return "公式情報をご確認ください"


def extract_resume_time(text):
    text = clean_text(text)

    patterns = [
        r"(\d{1,2}時\d{2}分頃)",
        r"(\d{1,2}時頃)",
        r"再開見込[み]*[:： ]*([^。 ]+)",
        r"運転再開見込[み]*[:： ]*([^。 ]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1)

    return "未定または記載なし"


def make_record(line_name, raw_text):
    info = TARGET_LINES[line_name]
    status = normalize_status(raw_text)

    return {
        "line": line_name,
        "section": info["section"],
        "source": info["source"],
        "status": status,
        "reason": extract_reason(raw_text),
        "resume_time": extract_resume_time(raw_text) if status == "運転見合わせ" else "",
        "raw_text": clean_text(raw_text),
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "initialized": False,
            "lines": {},
            "sent_hashes": [],
            "sent_time_signals": [],
        }

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        state.setdefault("initialized", False)
        state.setdefault("lines", {})
        state.setdefault("sent_hashes", [])
        state.setdefault("sent_time_signals", [])
        return state

    except Exception:
        return {
            "initialized": False,
            "lines": {},
            "sent_hashes": [],
            "sent_time_signals": [],
        }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def message_hash(message):
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def already_sent(state, message):
    return message_hash(message) in state.get("sent_hashes", [])


def remember_sent(state, message):
    hashes = state.get("sent_hashes", [])
    hashes.append(message_hash(message))
    state["sent_hashes"] = hashes[-50:]


def send_line(message):
    if not LINE_TOKEN:
        raise RuntimeError("LINE_TOKEN が設定されていません。")

    url = "https://api.line.me/v2/bot/message/broadcast"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }

    payload = {
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()


def get_jr_central_status():
    html = fetch_html(URLS["jr_central"])
    soup = BeautifulSoup(html, "html.parser")
    results = {}
    text_all = clean_text(soup.get_text(" "))

    for line_name, info in TARGET_LINES.items():
        if info["source"] != "JR東海":
            continue

        found_text = ""
        blocks = soup.find_all(["div", "li", "tr", "section", "article"])

        for block in blocks:
            block_text = clean_text(block.get_text(" "))
            if any(alias in block_text for alias in info["aliases"]):
                found_text = block_text
                break

        if not found_text:
            for alias in info["aliases"]:
                if alias in text_all:
                    idx = text_all.find(alias)
                    found_text = text_all[idx:idx + 300]
                    break

        if not found_text:
            found_text = "平常運転"

        results[line_name] = make_record(line_name, found_text)

    return results


def get_jr_east_status():
    html = fetch_html(URLS["jr_east"])
    soup = BeautifulSoup(html, "html.parser")
    results = {}
    text_all = clean_text(soup.get_text(" "))

    for line_name, info in TARGET_LINES.items():
        if info["source"] != "JR東日本":
            continue

        found_text = ""
        blocks = soup.find_all(["div", "li", "tr", "section", "article"])

        for block in blocks:
            block_text = clean_text(block.get_text(" "))
            if any(alias in block_text for alias in info["aliases"]):
                found_text = block_text
                break

        if not found_text:
            for alias in info["aliases"]:
                if alias in text_all:
                    idx = text_all.find(alias)
                    found_text = text_all[idx:idx + 300]
                    break

        if not found_text:
            found_text = "平常運転"

        results[line_name] = make_record(line_name, found_text)

    return results


def get_shizutetsu_status():
    html = fetch_html(URLS["shizutetsu"])
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))

    line_name = "静岡鉄道 静岡清水線"

    if "通常どおり運行" in text or "通常通り運行" in text:
        raw = "静鉄電車は通常どおり運行しております。"
    else:
        raw = text[:500]

    return {line_name: make_record(line_name, raw)}


def get_izuhakone_status():
    html = fetch_html(URLS["izuhakone"])
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))

    line_name = "伊豆箱根鉄道 駿豆線"

    if "駿豆線" in text:
        idx = text.find("駿豆線")
        raw = text[idx:idx + 500]
    else:
        raw = text[:500]

    return {line_name: make_record(line_name, raw)}


def get_all_status():
    all_status = {}
    errors = []

    fetchers = [
        get_jr_central_status,
        get_jr_east_status,
        get_shizutetsu_status,
        get_izuhakone_status,
    ]

    for fetcher in fetchers:
        try:
            all_status.update(fetcher())
        except Exception as e:
            errors.append(f"{fetcher.__name__}: {e}")

    for line_name in TARGET_LINES:
        if line_name not in all_status:
            all_status[line_name] = {
                "line": line_name,
                "section": TARGET_LINES[line_name]["section"],
                "source": TARGET_LINES[line_name]["source"],
                "status": "取得失敗",
                "reason": "公式サイトから取得できませんでした",
                "resume_time": "",
                "raw_text": "",
            }

    if errors:
        print("取得エラー:")
        for e in errors:
            print(e)

    return all_status


def get_time_signal_slot(now):
    """
    6:48〜6:58、17:48〜17:58の間に1回だけ時報を送る。
    """
    if now.hour == 6 and 48 <= now.minute <= 58:
        return now.strftime("%Y-%m-%d") + "_morning"

    if now.hour == 17 and 48 <= now.minute <= 58:
        return now.strftime("%Y-%m-%d") + "_evening"

    return None


def format_time_signal(current_status, now):
    lines = []

    for line_name, data in current_status.items():
        lines.append(
            f"・{line_name}（{data['section']}）\n"
            f"　状態：{data['status']}\n"
            f"　理由：{data['reason']}"
        )

    body = "\n\n".join(lines)

    return (
        f"🔔 定時運行情報（{now.strftime('%H:%M')}現在）\n\n"
        f"{body}\n\n"
        f"※公式情報をもとに自動配信しています。\n"
        f"#防災の輪"
    )


def format_event_message(current, previous):
    line = current["line"]
    section = current["section"]
    status = current["status"]
    reason = current["reason"]
    resume_time = current.get("resume_time", "")
    source = current["source"]

    prev_status = previous.get("status", "不明") if previous else "不明"

    if prev_status == "平常運転" and status == "遅延":
        return (
            f"⚠️ 遅延発生\n\n"
            f"【路線】{line}\n"
            f"【区間】{section}\n"
            f"【理由】{reason}\n"
            f"【情報元】{source}"
        )

    if status == "運転見合わせ" and prev_status != "運転見合わせ":
        return (
            f"⛔ 運転見合わせ\n\n"
            f"【路線】{line}\n"
            f"【見合わせ区間】{section}\n"
            f"【理由】{reason}\n"
            f"【再開見込み】{resume_time}\n"
            f"【情報元】{source}"
        )

    if prev_status == "運転見合わせ" and status in ["平常運転", "遅延", "運転再開"]:
        return (
            f"✅ 運転再開\n\n"
            f"【路線】{line}\n"
            f"【区間】{section}\n"
            f"【理由】{reason}\n\n"
            f"運転再開しました。\n"
            f"【情報元】{source}"
        )

    if prev_status in ["遅延", "運転見合わせ", "運休"] and status == "平常運転":
        return (
            f"✅ 遅延・運行障害 解消\n\n"
            f"【路線】{line}\n"
            f"【区間】{section}\n"
            f"【理由】{reason}\n\n"
            f"現在は平常運転です。\n"
            f"【情報元】{source}"
        )

    if status not in ["平常運転", prev_status]:
        return (
            f"⚠️ 運行情報に変化があります\n\n"
            f"【路線】{line}\n"
            f"【区間】{section}\n"
            f"【状態】{status}\n"
            f"【理由】{reason}\n"
            f"【情報元】{source}"
        )

    return None


def main():
    now = datetime.now(TIMEZONE)

    state = load_state()
    last_lines = state.get("lines", {})
    current_status = get_all_status()

    messages = []

    time_signal_slot = get_time_signal_slot(now)
    sent_time_signals = state.get("sent_time_signals", [])

    if time_signal_slot and time_signal_slot not in sent_time_signals:
        messages.append(format_time_signal(current_status, now))
        sent_time_signals.append(time_signal_slot)
        state["sent_time_signals"] = sent_time_signals[-30:]

    if not state.get("initialized", False):
        state["initialized"] = True
        state["lines"] = current_status

        for msg in messages:
            try:
                send_line(msg)
                remember_sent(state, msg)
                print("初回起動ですが、時報枠内のため時報を送信しました。")
            except Exception as e:
                print(f"LINE送信エラー: {e}")

        save_state(state)

        if not messages:
            print("初回起動のため、通知せず状態だけ保存しました。")

        return

    if not messages:
        for line_name, current in current_status.items():
            previous = last_lines.get(line_name)
            msg = format_event_message(current, previous)
            if msg:
                messages.append(msg)

    for msg in messages:
        if already_sent(state, msg):
            print("重複通知をスキップしました。")
            continue

        try:
            send_line(msg)
            remember_sent(state, msg)
            print("LINEへ送信しました。")
        except Exception as e:
            print(f"LINE送信エラー: {e}")

    state["lines"] = current_status
    save_state(state)


if __name__ == "__main__":
    main()
