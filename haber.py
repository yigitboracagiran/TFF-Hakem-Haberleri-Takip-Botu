import json
import os
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup


LIST_URL = "https://www.tff.org/default.aspx?pageID=248"

# Sayfanın kaç saniyede bir kontrol edileceği
CHECK_EVERY_SECONDS = 60

# Bildirim gönderilen son kaç haber ID'sinin saklanacağı
MAX_STORED_IDS = 5

# Bildirim geçmişinin kaydedileceği dosya
STATE_FILE = Path("tff_hakem_son_haber.json")

# TFF sitesinde SSL sertifika sorunu yaşanıyorsa False kalabilir.
VERIFY_SSL = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    # Tarayıcıdaki zorla yenilemeye benzer biçimde, aradaki
    # önbelleklerden eski HTML kullanılmamasını ister.
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    # Her yenilemede yeni bağlantı kurulmasını sağlar.
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
}

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()


if not VERIFY_SSL:
    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )


def now_text():
    """Log mesajları için mevcut tarihi ve saati döndürür."""
    return datetime.now().strftime("%d.%m.%Y-%H:%M")


def log(message):
    """Tarih ve saat ekleyerek konsola mesaj yazar."""
    print(
        f"{now_text()} {message}",
        flush=True,
    )


def telegram_is_configured():
    """Telegram bilgilerinin tanımlı olup olmadığını kontrol eder."""
    return bool(BOT_TOKEN and CHAT_ID)


def send_telegram_message(title, message, url=None):
    """
    Telegram mesajı gönderir.

    Dönüş değerleri:
        True: Mesaj başarıyla gönderildi.
        False: Mesaj gönderilemedi.
        None: Telegram bilgileri tanımlı değil.
    """
    if not telegram_is_configured():
        log(
            "Telegram token veya chat_id tanımlı değil. "
            "Telegram bildirimi atlanacak."
        )
        return None

    text = f"📰 {title}\n\n{message}"

    if url:
        text += f"\n\n{url}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False,
            },
            timeout=15,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            log(
                "Telegram API başarılı yanıt vermedi: "
                f"{result}"
            )
            return False

        log("Telegram mesajı gönderildi.")
        return True

    except requests.RequestException as error:
        log(
            "Telegram mesajı gönderilemedi: "
            f"{error}"
        )
        return False

    except ValueError as error:
        log(
            "Telegram yanıtı JSON olarak okunamadı: "
            f"{error}"
        )
        return False


def get_latest_news():
    """
    TFF hakem haberleri sayfasını bir kez zorla yeniler ve
    sayfada ilk sırada görünen haberi döndürür.

    ftxtID değerleri yayın sırasını göstermediği için en büyük
    ID seçilmez. Örneğin daha yeni bir haber, daha küçük bir
    ftxtID değerine sahip olabilir.
    """
    # Her isteğin URL'sini benzersiz yap. Bu, sorgu dizisini
    # önbellek anahtarına dahil eden ara katmanlarda eski HTML
    # kullanılma ihtimalini azaltır.
    request_url = (
        f"{LIST_URL}&_hard_refresh={time.time_ns()}"
    )

    # requests kendi başına tarayıcı önbelleği tutmaz. Buna ek
    # olarak her yenilemede yeni bir Session ve yeni bağlantı
    # kullanarak tarayıcıdaki zorla yenilemeye yaklaşılır.
    with requests.Session() as session:
        response = session.get(
            request_url,
            headers={
                **HEADERS,
                "Referer": LIST_URL,
            },
            timeout=20,
            verify=VERIFY_SSL,
            allow_redirects=True,
        )

    response.raise_for_status()

    # TFF sayfası Türkçe karakterlerde Windows-1254
    # kodlamasını kullanabiliyor.
    response.encoding = "windows-1254"

    # Sunucunun/ara önbelleğin davranışını incelemeyi kolaylaştırır.
    cache_parts = []

    for header_name in (
        "Date",
        "Age",
        "Cache-Control",
        "Expires",
        "ETag",
        "Last-Modified",
        "X-Cache",
        "CF-Cache-Status",
    ):
        header_value = response.headers.get(header_name)

        if header_value:
            cache_parts.append(
                f"{header_name}={header_value}"
            )

    if cache_parts:
        log(
            "Yenileme yanıtı: "
            + "; ".join(cache_parts)
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    candidates = []
    seen_ids = set()

    # Bağlantılar HTML'deki sırayla okunur. TFF liste sayfasında
    # üstte görünen haber, ilk uygun haber bağlantısıdır.
    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(
            LIST_URL,
            href,
        )

        parsed_url = urlparse(full_url)
        query = parse_qs(parsed_url.query)

        if "ftxtID" not in query:
            continue

        title = " ".join(
            link.get_text(
                " ",
                strip=True,
            ).split()
        )

        if not title or title.startswith("-"):
            continue

        try:
            news_id = str(
                int(query["ftxtID"][0])
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ):
            continue

        # Aynı haberin resim ve başlık bağlantıları varsa yalnızca
        # başlığı bulunan ilk bağlantıyı sakla.
        if news_id in seen_ids:
            continue

        seen_ids.add(news_id)

        candidates.append(
            {
                "id": news_id,
                "title": title,
                "url": full_url,
            }
        )

    if not candidates:
        raise RuntimeError(
            "Sayfada uygun haber bağlantısı bulunamadı."
        )

    latest = candidates[0]

    log(
        f"Yenilenen sayfanın ilk haberi: "
        f"{latest['title']} - ID: {latest['id']}"
    )

    return latest



def normalize_notified_ids(ids):
    """
    ID listesini temizler, tekrarları kaldırır ve yalnızca
    son MAX_STORED_IDS adet ID'yi döndürür.
    """
    normalized_ids = []

    for news_id in ids:
        news_id = str(news_id).strip()

        if not news_id:
            continue

        # Aynı ID daha önce eklenmişse eski konumundan çıkar.
        if news_id in normalized_ids:
            normalized_ids.remove(news_id)

        normalized_ids.append(news_id)

    return normalized_ids[-MAX_STORED_IDS:]


def load_notified_ids():
    """
    Daha önce bildirim gönderilen haber ID'lerini yükler.

    Yeni state biçimi:
    {
        "notified_ids": ["100", "101", "102"],
        "updated_at": "2026-07-21T12:00:00"
    }

    Eski state biçimi de desteklenir:
    {
        "id": "102",
        "title": "...",
        "url": "..."
    }
    """
    if not STATE_FILE.exists():
        log(
            "State dosyası bulunamadı. "
            "Boş bildirim geçmişi kullanılacak."
        )
        return []

    try:
        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        # Yeni state biçimi
        if (
            isinstance(data, dict)
            and isinstance(
                data.get("notified_ids"),
                list,
            )
        ):
            notified_ids = normalize_notified_ids(
                data["notified_ids"]
            )

            log(
                "Kayıtlı bildirim ID'leri: "
                + (
                    ", ".join(notified_ids)
                    if notified_ids
                    else "Yok"
                )
            )

            return notified_ids

        # Eski state biçiminden otomatik geçiş
        if (
            isinstance(data, dict)
            and data.get("id") is not None
        ):
            notified_ids = normalize_notified_ids(
                [data["id"]]
            )

            log(
                "Eski state biçimi okundu. "
                "Yeni biçime otomatik geçilecek."
            )

            return notified_ids

        log(
            "State dosyasının biçimi geçersiz. "
            "Boş bildirim geçmişi kullanılacak."
        )
        return []

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        log(
            f"State dosyası okunamadı: {error}"
        )
        return []


def save_notified_ids(notified_ids):
    """
    Bildirim gönderilen son MAX_STORED_IDS adet ID'yi
    state dosyasına güvenli biçimde kaydeder.
    """
    normalized_ids = normalize_notified_ids(
        notified_ids
    )

    state = {
        "notified_ids": normalized_ids,
        "updated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    temporary_file = STATE_FILE.with_suffix(
        STATE_FILE.suffix + ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Geçici dosyayı asıl state dosyasının üzerine taşır.
    temporary_file.replace(
        STATE_FILE
    )


def open_news_in_browser(url):
    """
    Haberi varsayılan tarayıcıda açar.

    Başarılıysa True, başarısızsa False döndürür.
    """
    try:
        opened = webbrowser.open_new_tab(
            url
        )

        if opened:
            log(
                "Haber tarayıcıda açıldı."
            )
            return True

        log(
            "Tarayıcı açma komutu gönderildi ancak "
            "başarılı olduğu doğrulanamadı."
        )
        return False

    except Exception as error:
        log(
            f"Tarayıcı açılamadı: {error}"
        )
        return False


def notify_new_news(
    latest,
    reason,
    notified_ids,
):
    """
    Yeni haber için tarayıcı ve Telegram bildirimi gönderir.

    Bildirim başarılı kabul edilirse ID kaydedilir ve
    güncellenmiş ID listesi döndürülür.
    """
    log(reason)

    log(
        "Bildirim gönderilecek haber: "
        f"{latest['title']}"
    )

    log(
        latest["url"]
    )

    telegram_result = send_telegram_message(
        "Yeni TFF hakem haberi",
        latest["title"],
        latest["url"],
    )

    browser_opened = open_news_in_browser(
        latest["url"]
    )

    # Telegram yapılandırılmışsa gönderimin başarılı olması
    # gerekir. Başarısız gönderimde ID kaydedilmez ve haber
    # sonraki kontrolde yeniden denenir.
    if telegram_is_configured() and telegram_result is not True:
        log(
            "Telegram bildirimi başarısız olduğu için "
            "haber ID'si kaydedilmedi."
        )
        return notified_ids

    # Telegram kullanılmıyorsa en azından tarayıcının
    # açılmış olması gerekir.
    if not telegram_is_configured() and not browser_opened:
        log(
            "Telegram yapılandırılmamış ve tarayıcı da "
            "açılamamış olduğu için haber ID'si kaydedilmedi."
        )
        return notified_ids

    latest_id = str(
        latest["id"]
    ).strip()

    updated_ids = normalize_notified_ids(
        [
            *notified_ids,
            latest_id,
        ]
    )

    save_notified_ids(
        updated_ids
    )

    log(
        "Kaydedilen son bildirim ID'leri: "
        + ", ".join(updated_ids)
    )

    return updated_ids


def main():
    log(
        "TFF hakem haberleri takip ediliyor..."
    )
    log(
        f"Sayfa her {CHECK_EVERY_SECONDS} saniyede bir, "
        "her turda yalnızca bir kez kontrol edilecek."
    )

    notified_ids = load_notified_ids()

    while True:
        try:
            latest = get_latest_news()

            latest_id = str(
                latest.get("id", "")
            ).strip()

            if not latest_id:
                raise RuntimeError(
                    "Sayfadan alınan haber ID'si boş."
                )

            int(latest_id)

            if latest_id in notified_ids:
                log(
                    "Bu haber JSON geçmişinde kayıtlı: "
                    f"{latest['title']} - ID: {latest_id}"
                )

            else:
                reason = (
                    f"Sayfanın ilk haberindeki ID {latest_id}, "
                    "JSON bildirim geçmişinde bulunamadı. "
                    "Bildirim gönderiliyor."
                )

                notified_ids = notify_new_news(
                    latest,
                    reason,
                    notified_ids,
                )

        except KeyboardInterrupt:
            log(
                "Program kullanıcı tarafından durduruldu."
            )
            break

        except requests.RequestException as error:
            log(
                "TFF sayfasına erişilirken hata oluştu: "
                f"{error}"
            )

        except Exception as error:
            log(
                f"Hata: {error}"
            )

        try:
            log(
                f"Sonraki kontrol için {CHECK_EVERY_SECONDS} "
                "saniye bekleniyor."
            )
            time.sleep(
                CHECK_EVERY_SECONDS
            )

        except KeyboardInterrupt:
            log(
                "Program kullanıcı tarafından durduruldu."
            )
            break


if __name__ == "__main__":
    main()