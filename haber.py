import time
import json
import webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from collections import Counter

import requests
from bs4 import BeautifulSoup


LIST_URL = "https://www.tff.org/default.aspx?pageID=248"
CHECK_EVERY_SECONDS = 60
STATE_FILE = Path("tff_hakem_son_haber.json")

REFRESH_COUNT = 5
REFRESH_DELAY_SECONDS = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TFF-Haber-Takip/1.0)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def get_latest_news_once():
    response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
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

        if "Müsabaka Görevlileri Açıklandı" not in title:
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

            print(
                f"Kontrol {i + 1}/{REFRESH_COUNT}: "
                f"{news['title']} - {news['id']}"
            )

        except Exception as e:
            print(f"Kontrol {i + 1}/{REFRESH_COUNT} hatası: {e}")

        if i < REFRESH_COUNT - 1:
            time.sleep(REFRESH_DELAY_SECONDS)

    if not results:
        raise RuntimeError("5 kontrolün hiçbirinde haber alınamadı.")

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

    # Eşitlik varsa ftxtID büyük olanı seç
    selected = max(candidates, key=lambda x: int(x["id"]))

    print(
        f"Seçilen çoğunluk haber: {selected['title']} "
        f"({id_counts[selected['id']]}/{REFRESH_COUNT})"
    )

    return selected


def load_last_id():
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("id")
    except Exception:
        return None


def save_latest(news):
    STATE_FILE.write_text(
        json.dumps(news, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    print("TFF hakem haberleri takip ediliyor...")

    last_id = load_last_id()

    while True:
        try:
            latest = get_latest_news()

            if last_id is None:
                last_id = latest["id"]
                save_latest(latest)
                print(f"İlk kayıt: {latest['title']}")
                print(latest["url"])

            elif latest["id"] != last_id:
                print(f"Yeni haber bulundu: {latest['title']}")
                print(latest["url"])

                webbrowser.open_new_tab(latest["url"])

                last_id = latest["id"]
                save_latest(latest)

            else:
                print(f"Yeni haber yok. Son haber: {latest['title']}")

        except Exception as e:
            print(f"Hata: {e}")

        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()