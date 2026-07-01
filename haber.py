import time
import json
import webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from collections import Counter
import os
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime


LIST_URL = "https://www.tff.org/default.aspx?pageID=248"
CHECK_EVERY_SECONDS = 60
STATE_FILE = Path("tff_hakem_son_haber.json")

REFRESH_COUNT = 5
REFRESH_DELAY_SECONDS = 2

VERIFY_SSL = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TFF-Haber-Takip/1.0)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def now_text():
    return datetime.now().strftime("%d.%m.%Y-%H:%M")


def log(message):
    print(f"{now_text()} {message}")


def send_telegram_message(title, message, url=None):
    if not BOT_TOKEN or not CHAT_ID:
        log("Telegram token veya chat_id tanımlı değil.")
        return

    text = f"📰 {title}\n\n{message}"

    if url:
        text += f"\n\n{url}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=10
        )
        response.raise_for_status()

    except Exception as e:
        log(f"Telegram mesajı gönderilemedi: {e}")


def get_latest_news_once():
    response = requests.get(
        LIST_URL,
        headers=HEADERS,
        timeout=20,
        verify=VERIFY_SSL
    )
    response.raise_for_status()

    response.encoding = "windows-1254"

    soup = BeautifulSoup(response.text, "html.parser")

    candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(LIST_URL, href)

        parsed = urlparse(full_url)
        query = parse_qs(parsed.query)

        if "ftxtID" not in query:
            continue

        title = " ".join(a.get_text(" ", strip=True).split())

        if not title:
            continue

        if title.startswith("-"):
            continue

        try:
            news_id = int(query["ftxtID"][0])
        except ValueError:
            continue

        candidates.append({
            "id": str(news_id),
            "numeric_id": news_id,
            "title": title,
            "url": full_url
        })

    if not candidates:
        raise RuntimeError("Sayfada uygun haber linki bulunamadı.")

    latest = max(candidates, key=lambda x: x["numeric_id"])
    latest.pop("numeric_id", None)

    return latest


def get_latest_news():
    results = []

    for i in range(REFRESH_COUNT):
        try:
            news = get_latest_news_once()
            results.append(news)

            log(
                f"Kontrol {i + 1}/{REFRESH_COUNT}: "
                f"{news['title']} - {news['id']}"
            )

        except Exception as e:
            log(f"Kontrol {i + 1}/{REFRESH_COUNT} hatası: {e}")

        if i < REFRESH_COUNT - 1:
            time.sleep(REFRESH_DELAY_SECONDS)

    if not results:
        raise RuntimeError(f"{REFRESH_COUNT} kontrolün hiçbirinde haber alınamadı.")

    id_counts = Counter(news["id"] for news in results)
    most_common_count = id_counts.most_common(1)[0][1]

    majority_ids = [
        news_id
        for news_id, count in id_counts.items()
        if count == most_common_count
    ]

    candidates = [
        news
        for news in results
        if news["id"] in majority_ids
    ]

    selected = max(candidates, key=lambda x: int(x["id"]))

    log(
        f"Seçilen çoğunluk haber: {selected['title']} "
        f"({id_counts[selected['id']]}/{REFRESH_COUNT})"
    )

    return selected


def load_last_news():
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            return None

        return data

    except Exception:
        return None


def save_latest(news):
    STATE_FILE.write_text(
        json.dumps(news, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def notify_new_news(latest, reason):
    log(reason)
    log(f"Bildirim gönderilecek haber: {latest['title']}")
    log(latest["url"])

    webbrowser.open_new_tab(latest["url"])

    send_telegram_message(
        "Yeni TFF hakem haberi",
        latest["title"],
        latest["url"]
    )

    save_latest(latest)


def main():
    log("TFF hakem haberleri takip ediliyor...")

    while True:
        try:
            latest = get_latest_news()
            saved_news = load_last_news()

            saved_id = saved_news.get("id") if saved_news else None

            if saved_id == latest["id"]:
                log(f"Yeni haber yok. Son haber: {latest['title']}")

            else:
                if saved_id is None:
                    reason = "State dosyası yok veya okunamadı. Bildirim gönderiliyor."
                else:
                    reason = (
                        f"State dosyasındaki haber farklı. "
                        f"Eski ID: {saved_id}, Yeni ID: {latest['id']}. "
                        f"Bildirim gönderiliyor."
                    )

                notify_new_news(latest, reason)

        except KeyboardInterrupt:
            log("\nProgram durduruldu.")
            break

        except Exception as e:
            log(f"Hata: {e}")

        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()