# TFF Hakem Haberleri Takip Botu

Bu Python scripti, TFF web sitesindeki hakem haberlerini belirli aralıklarla kontrol eder.

Program ilk kez çalıştırıldığında mevcut son haberi başlangıç kaydı olarak kabul eder ve bildirim göndermez.

Daha sonra yeni bir haber bulunduğunda:

* Haber başlığını konsola yazar
* Haber bağlantısını konsola yazar
* Haber bağlantısını tarayıcıda açar
* Telegram üzerinden bildirim gönderir
* Son görülen haber bilgisini yerel bir JSON dosyasına kaydeder

## Hedef Ortam

| Bileşen | Sürüm / Notlar |
|---|---|
| Dil | Python 3 |
| İşletim Sistemi | Linux / macOS / Windows |
| Paket Yöneticisi | `pip3` veya `pip` |
| Harici Paketler | `requests`, `urllib3`, `beautifulsoup4` |
| Bildirim Altyapısı | Telegram Bot API |
| Ortam Değişkenleri | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Durum Dosyası | `tff_hakem_son_haber.json` |
| Ana Script | `haber.py` |

> [!NOTE]
> Telegram token ve chat ID bilgilerini doğrudan kaynak koda yazmayın; ortam değişkeni olarak tanımlayın.

---

## İçindekiler

- [Özellikler](#ozellikler)
- [Gereksinimler](#gereksinimler)
- [Proje Yapısı](#proje-yapisi)
- [Değişken Açıklamaları](#degisken-aciklamalari)
- [Telegram Bot Token ve Chat ID Alma](#telegram-bot-token-ve-chat-id-alma)
- [BotFather ile Bot Token Alma](#botfather-ile-bot-token-alma)
- [Bot Token Yenileme](#bot-token-yenileme)
- [Chat ID Öğrenme](#chat-id-ogrenme)
- [getUpdates Boş Gelirse](#getupdates-bos-gelirse)
- [Telegram Ayarlarının Scriptte Kullanımı](#telegram-ayarlarinin-scriptte-kullanimi)
- [Güvenlik Notu](#guvenlik-notu)
- [Telegram Ortam Değişkenleri](#telegram-ortam-degiskenleri)
- [Çalıştırma](#calistirma)
- [Örnek Log Çıktısı](#ornek-log-ciktisi)
- [Çalışma Mantığı](#calisma-mantigi)
- [İlk Çalıştırma Davranışı](#ilk-calistirma-davranisi)
- [Telegram Bildirimi](#telegram-bildirimi)
- [Durum Dosyası](#durum-dosyasi)
- [Hata Yönetimi](#hata-yonetimi)
- [Olası Sorunlar](#olasi-sorunlar)

<a id="ozellikler"></a>

## Özellikler

* TFF haber listesinden en güncel hakem haberini tespit eder
* Haberleri URL içindeki `ftxtID` değerine göre karşılaştırır
* Aynı kontrolü birden fazla kez yaparak daha güvenilir sonuç seçer
* Telegram bildirimi gönderir
* Yeni haber bulunduğunda otomatik olarak tarayıcıda açar
* Son haber ID bilgisini dosyada sakladığı için program yeniden başlatıldığında kaldığı yerden devam eder
* Telegram bot token ve chat ID bilgilerini ortam değişkenlerinden okur
* İlk çalıştırmada mevcut haberi yeni haber gibi bildirmez

<a id="gereksinimler"></a>

## Gereksinimler

Script Python 3 ile çalışır.

Kodda kullanılan bazı modüller Python’un standart kütüphanesiyle birlikte gelir. Bunlar için ayrıca kurulum gerekmez:

```text
time
json
webbrowser
pathlib
urllib.parse
collections
os
datetime
```

Harici olarak kurulması gereken Python paketleri şunlardır:

```text
requests
urllib3
beautifulsoup4
```

Kurulum için:

```bash
pip3 install requests urllib3 beautifulsoup4
```

<a id="proje-yapisi"></a>

## Proje Yapısı

Örnek proje yapısı:

```text
tff-hakem-haberleri/
├── haber.py
├── tff_hakem_son_haber.json
└── README.md
```

`tff_hakem_son_haber.json` dosyası script tarafından otomatik oluşturulur. İlk başta elle oluşturmanız gerekmez.

<a id="degisken-aciklamalari"></a>

## Değişken Açıklamaları

### `LIST_URL`

Kontrol edilecek TFF haber liste sayfasının adresidir.

```python
LIST_URL = "https://www.tff.org/default.aspx?pageID=248"
```

### `CHECK_EVERY_SECONDS`

Ana döngüde iki kontrol arasında beklenecek süredir.

```python
CHECK_EVERY_SECONDS = 60
```

Bu ayara göre script her 60 saniyede bir TFF haber listesini kontrol eder.

### `STATE_FILE`

Son görülen haber bilgisinin kaydedileceği JSON dosyasıdır.

```python
STATE_FILE = Path("tff_hakem_son_haber.json")
```

Script yeniden başlatıldığında bu dosyayı okuyarak son görülen haber ID değerini öğrenir.

### `REFRESH_COUNT`

Her kontrol turunda kaç kez haber sorgusu yapılacağını belirler.

```python
REFRESH_COUNT = 5
```

Script tek bir kontrole güvenmek yerine aynı sayfayı 5 kez sorgular ve daha güvenilir bir sonuç seçmeye çalışır.

### `REFRESH_DELAY_SECONDS`

Aynı kontrol turundaki sorgular arasında beklenecek süredir.

```python
REFRESH_DELAY_SECONDS = 2
```

Bu ayara göre aynı kontrol turundaki sorgular arasında 2 saniye beklenir.

### `VERIFY_SSL`

SSL doğrulamasının aktif olup olmayacağını belirler.

```python
VERIFY_SSL = False
```

Güvenlik açısından mümkünse `True` kullanılması önerilir. Ancak bazı durumlarda site tarafındaki SSL yapılandırması nedeniyle hata alınırsa geçici olarak `False` kullanılabilir.

`VERIFY_SSL = False` kullanıldığında SSL uyarılarını gizlemek için scriptte şu satır yer alır:

```python
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### `HEADERS`

HTTP isteği gönderilirken kullanılacak başlıklardır.

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TFF-Haber-Takip/1.0)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
```

Bazı siteler varsayılan Python isteklerini engelleyebileceği için `User-Agent` tanımlamak faydalıdır.

### `BOT_TOKEN`

Telegram bot token bilgisidir.

Bu bilgi doğrudan Python dosyasına yazılmaz. Ortam değişkeninden okunur:

```python
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
```

### `CHAT_ID`

Bildirim gönderilecek Telegram kullanıcı, grup veya kanal ID bilgisidir.

Bu bilgi doğrudan Python dosyasına yazılmaz. Ortam değişkeninden okunur:

```python
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
```

<a id="telegram-bot-token-ve-chat-id-alma"></a>

## Telegram Bot Token ve Chat ID Alma

Telegram bildirimi gönderebilmek için iki bilgiye ihtiyaç vardır:

* `TELEGRAM_BOT_TOKEN`
* `TELEGRAM_CHAT_ID`

`TELEGRAM_BOT_TOKEN`, Telegram botunuza ait API anahtarıdır.

`TELEGRAM_CHAT_ID`, mesajın gönderileceği kullanıcı, grup veya kanal kimliğidir.

Bu bilgiler doğrudan Python dosyasına yazılmaz. Script çalıştırılmadan önce ortam değişkeni olarak tanımlanır.

<a id="botfather-ile-bot-token-alma"></a>

## BotFather ile Bot Token Alma

1. Telegram uygulamasını açın.
2. Arama kısmına `@BotFather` yazın.
3. Resmi BotFather hesabını açın.
4. Sohbeti başlatın.
5. Aşağıdaki komutu gönderin:

```text
/newbot
```

6. BotFather sizden bot için bir görünen ad isteyecektir.

Örnek:

```text
TFF Hakem Haber Botu
```

7. Daha sonra bot için benzersiz bir kullanıcı adı ister. Bu kullanıcı adı mutlaka `bot` ile bitmelidir.

Örnek:

```text
tff_hakem_haber_bot
```

8. İşlem başarılı olursa BotFather size bir token verir.

Token formatı genellikle şu şekildedir:

```text
123456789:ABCDefGhIJKlmNoPQRstuVWXyz
```

Bu değeri kaynak kod içine yazmak yerine ortam değişkeni olarak tanımlayın.

Linux / macOS:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
```

Bot token bilgisini kimseyle paylaşmayın. Bu token, botunuz adına mesaj göndermek için kullanılabilir.

<a id="bot-token-yenileme"></a>

## Bot Token Yenileme

Eğer bot token bilgisini kaybettiyseniz veya token başkasının eline geçtiyse BotFather üzerinden yeni token oluşturabilirsiniz.

1. Telegram’da `@BotFather` sohbetini açın.
2. Şu komutu gönderin:

```text
/token
```

3. BotFather size sahip olduğunuz botları listeler.
4. İlgili botu seçin.
5. BotFather yeni token üretir.

Yeni token üretildikten sonra eski token geçersiz olur. Bu nedenle `TELEGRAM_BOT_TOKEN` ortam değişkenini yeni token ile güncellemeniz gerekir.

Linux / macOS:

```bash
export TELEGRAM_BOT_TOKEN="yeni_token_buraya"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="yeni_token_buraya"
```

<a id="chat-id-ogrenme"></a>

## Chat ID Öğrenme

`TELEGRAM_CHAT_ID` değerini öğrenmek için önce botun mesaj göndereceği sohbetle etkileşim kurulmalıdır.

### Kişisel Mesaj İçin Chat ID Alma

1. Telegram’da oluşturduğunuz botu bulun.
2. Botla sohbeti başlatın.
3. Bota herhangi bir mesaj gönderin.

Örnek:

```text
Merhaba
```

4. Tarayıcıdan aşağıdaki adresi açın:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

Burada `<BOT_TOKEN>` yerine kendi bot token bilginizi yazın.

Örnek:

```text
https://api.telegram.org/bot123456789:ABCDefGhIJKlmNoPQRstuVWXyz/getUpdates
```

5. Açılan JSON çıktısında şu bölümü bulun:

```json
"chat": {
  "id": 123456789,
  "first_name": "Ad",
  "type": "private"
}
```

Buradaki `id` değeri sizin `TELEGRAM_CHAT_ID` değerinizdir.

Bu değeri ortam değişkeni olarak tanımlayın.

Linux / macOS:

```bash
export TELEGRAM_CHAT_ID="123456789"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_CHAT_ID="123456789"
```

### Grup İçin Chat ID Alma

Telegram bildiriminin bir gruba gönderilmesini istiyorsanız:

1. Botu ilgili Telegram grubuna ekleyin.
2. Grupta herhangi bir mesaj gönderin.
3. Tarayıcıdan şu adresi açın:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. JSON çıktısında grup sohbetine ait şu bölümü bulun:

```json
"message": {
  "chat": {
    "id": -1001234567890,
    "title": "Grup Adı",
    "type": "supergroup"
  }
}
```

Buradaki `chat.id` değeri grup için kullanılacak `TELEGRAM_CHAT_ID` değeridir.

Grup chat ID değerleri genellikle `-` işaretiyle başlar. Bu değeri eksiksiz kopyalamanız gerekir.

Linux / macOS:

```bash
export TELEGRAM_CHAT_ID="-1001234567890"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_CHAT_ID="-1001234567890"
```

### Kanal İçin Chat ID Alma

Telegram bildiriminin bir kanala gönderilmesini istiyorsanız:

1. Botu ilgili Telegram kanalına yönetici olarak ekleyin.
2. Kanalda herhangi bir test mesajı paylaşın.
3. Tarayıcıdan şu adresi açın:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. JSON çıktısında kanal gönderisine ait şu bölümü bulun:

```json
"channel_post": {
  "message_id": 2,
  "sender_chat": {
    "id": -1001234567890,
    "title": "Kanal Adı",
    "type": "channel"
  }
}
```

Buradaki `sender_chat.id` değeri kanal için kullanılacak `TELEGRAM_CHAT_ID` değeridir.

Kanal chat ID değerleri de genellikle `-100` ile başlar. Bu değeri eksiksiz kopyalamanız gerekir.

Linux / macOS:

```bash
export TELEGRAM_CHAT_ID="-1001234567890"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_CHAT_ID="-1001234567890"
```

<a id="getupdates-bos-gelirse"></a>

## getUpdates Boş Gelirse

Eğer tarayıcıda açtığınız `getUpdates` sonucu şu şekilde boş dönüyorsa:

```json
{
  "ok": true,
  "result": []
}
```

şunları kontrol edin:

* Botla bireysel sohbet başlatıldı mı?
* Bota en az bir mesaj gönderildi mi?
* Bot gruba eklendiyse grupta yeni bir mesaj yazıldı mı?
* Bot kanala eklendiyse kanalda yeni bir test mesajı paylaşıldı mı?
* Kanal için JSON içinde `channel_post.sender_chat.id` alanı kontrol edildi mi?
* Doğru bot token kullanılıyor mu?

Mesaj gönderdikten sonra `getUpdates` adresini tekrar yenileyin.

<a id="telegram-ayarlarinin-scriptte-kullanimi"></a>

## Telegram Ayarlarının Scriptte Kullanımı

Token ve chat ID bilgilerini aldıktan sonra bu değerleri Python dosyasına yazmayın.

Script zaten şu şekilde ortam değişkenlerini okur:

```python
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
```

Bu nedenle çalıştırmadan önce değişkenleri terminalde tanımlamanız yeterlidir.

Linux / macOS:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
export TELEGRAM_CHAT_ID="123456789"

python3 haber.py
```

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
$env:TELEGRAM_CHAT_ID="123456789"

python haber.py
```

Bu ayarlar doğru yapıldığında script yeni haber bulduğunda Telegram üzerinden bildirim gönderecektir.

<a id="guvenlik-notu"></a>

## Güvenlik Notu

Bot token bilgisini doğrudan Python dosyasına yazmak önerilmez.

Yanlış kullanım:

```python
BOT_TOKEN = "123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
CHAT_ID = "123456789"
```

Doğru kullanım:

```python
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
```

<a id="telegram-ortam-degiskenleri"></a>

## Telegram Ortam Değişkenleri

Script Telegram bilgilerini şu iki ortam değişkeninden okur:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Bu bilgileri kaynak kodun içine yazmak yerine terminalde tanımlamanız gerekir.

<a id="calistirma"></a>

## Çalıştırma

Script dosyasını örneğin `haber.py` olarak kaydedin.

Çalıştırmadan önce Telegram bilgilerini ortam değişkeni olarak tanımlayın.

### Linux / macOS

Kişisel Telegram sohbeti için:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
export TELEGRAM_CHAT_ID="123456789"

python3 haber.py
```

Grup veya kanal için:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
export TELEGRAM_CHAT_ID="-1001234567890"

python3 haber.py
```

### Windows PowerShell

Kişisel Telegram sohbeti için:

```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
$env:TELEGRAM_CHAT_ID="123456789"

python haber.py
```

Grup veya kanal için:

```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
$env:TELEGRAM_CHAT_ID="-1001234567890"

python haber.py
```

<a id="ornek-log-ciktisi"></a>

## Örnek Log Çıktısı

Program çalıştığında konsolda şu şekilde loglar üretir:

```text
30.06.2026-14:25 TFF hakem haberleri takip ediliyor...
30.06.2026-14:25 Kontrol 1/5: Haber başlığı - 12345
30.06.2026-14:25 Kontrol 2/5: Haber başlığı - 12345
30.06.2026-14:25 Kontrol 3/5: Haber başlığı - 12345
30.06.2026-14:25 Kontrol 4/5: Haber başlığı - 12345
30.06.2026-14:25 Kontrol 5/5: Haber başlığı - 12345
30.06.2026-14:25 Seçilen çoğunluk haber: Haber başlığı (5/5)
30.06.2026-14:25 Yeni haber yok. Son haber: Haber başlığı
```

İlk çalıştırmada daha önce kayıtlı haber yoksa şu şekilde bir çıktı görülür:

```text
30.06.2026-14:25 İlk kayıt yapıldı, bildirim gönderilmedi: Haber başlığı
30.06.2026-14:25 https://haber-linki
```

Yeni haber bulunduğunda ise şu şekilde çıktı üretilir:

```text
30.06.2026-14:30 Yeni haber bulundu: Yeni haber başlığı
30.06.2026-14:30 https://haber-linki
```

Programı durdurmak için:

```bash
Ctrl + C
```

<a id="calisma-mantigi"></a>

## Çalışma Mantığı

Script önce TFF haber liste sayfasını indirir.

HTML içindeki tüm bağlantıları inceler ve URL içinde `ftxtID` parametresi olan haberleri aday olarak toplar.

Her haber için:

* Haber ID değeri alınır
* Haber başlığı temizlenir
* Tam haber bağlantısı oluşturulur

Daha sonra ID değeri en büyük olan haber, en güncel haber olarak kabul edilir.

Script tek bir sorguya güvenmek yerine aynı kontrolü `REFRESH_COUNT` kadar tekrarlar. Gelen sonuçlar arasında en çok tekrar eden haber ID değeri seçilir. Eşitlik olması durumunda ID değeri en büyük olan haber tercih edilir.

Bu yöntem, sayfa geçici olarak eski veri döndürürse veya bağlantı listesi tutarsız gelirse daha güvenilir sonuç alınmasını sağlar.

<a id="ilk-calistirma-davranisi"></a>

## İlk Çalıştırma Davranışı

Program ilk kez çalıştırıldığında daha önce kaydedilmiş bir haber ID bilgisi yoksa mevcut son haberi ilk kayıt olarak kabul eder.

Bu durumda:

* Haber bilgisi `STATE_FILE` içine kaydedilir
* Haber başlığı konsola yazılır
* Haber bağlantısı konsola yazılır
* Telegram bildirimi gönderilmez
* Haber bağlantısı tarayıcıda açılmaz

Bu davranış sayesinde program ilk kez başlatıldığında mevcut son haber yanlışlıkla “yeni haber” gibi bildirilmez.

İlgili kod bloğu şu şekildedir:

```python
if last_id is None:
    last_id = latest["id"]
    save_latest(latest)

    log(f"İlk kayıt yapıldı, bildirim gönderilmedi: {latest['title']}")
    log(latest["url"])
```

Sonraki kontrollerde farklı bir haber ID değeri bulunursa bu haber yeni haber kabul edilir.

Yeni haber bulunduğunda:

* Haber başlığı konsola yazılır
* Haber bağlantısı konsola yazılır
* Haber bağlantısı tarayıcıda açılır
* Telegram bildirimi gönderilir
* Son haber bilgisi `STATE_FILE` içine kaydedilir

İlgili kod bloğu şu şekildedir:

```python
elif latest["id"] != last_id:
    log(f"Yeni haber bulundu: {latest['title']}")
    log(latest["url"])

    webbrowser.open_new_tab(latest["url"])

    send_telegram_message(
        "Yeni TFF hakem haberi",
        latest["title"],
        latest["url"]
    )

    last_id = latest["id"]
    save_latest(latest)
```

<a id="telegram-bildirimi"></a>

## Telegram Bildirimi

Yeni haber bulunduğunda Telegram mesajı şu formatta gönderilir:

```text
📰 Yeni TFF hakem haberi

Haber başlığı

https://haber-linki
```

Telegram bildirimi göndermek için aşağıdaki iki ortam değişkeninin tanımlanmış olması gerekir:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Script bu değerleri şu şekilde okur:

```python
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
```

Eğer bu değerlerden biri eksikse program hata vermez, sadece konsola şu mesajı yazar:

```text
Telegram token veya chat_id tanımlı değil.
```

<a id="durum-dosyasi"></a>

## Durum Dosyası

Son görülen haber bilgisi JSON formatında saklanır.

Dosya adı:

```text
tff_hakem_son_haber.json
```

Örnek dosya içeriği:

```json
{
  "id": "12345",
  "title": "Haber başlığı",
  "url": "https://..."
}
```

Bu dosya sayesinde script yeniden başlatıldığında aynı haberi tekrar yeni haber olarak algılamaz.

Dosya silinirse script bir sonraki çalıştırmada mevcut son haberi yeniden ilk kayıt olarak kabul eder ve bildirim göndermez.

<a id="hata-yonetimi"></a>

## Hata Yönetimi

Script aşağıdaki durumlarda hata mesajını konsola yazar ve çalışmaya devam eder:

* Sayfa indirilemezse
* Bağlantı zaman aşımına uğrarsa
* HTML içinde uygun haber bağlantısı bulunamazsa
* Telegram bildirimi gönderilemezse
* Durum dosyası okunamazsa

Ana döngüde oluşan hatalar programı durdurmaz. Sadece loglanır ve bir sonraki kontrol zamanı beklenir.

Klavye ile durdurma yapılırsa program şu mesajı yazar ve kapanır:

```text
Program durduruldu.
```

<a id="olasi-sorunlar"></a>

## Olası Sorunlar

### Telegram mesajı gelmiyor

Kontrol edilmesi gerekenler:

* `TELEGRAM_BOT_TOKEN` doğru tanımlandı mı?
* `TELEGRAM_CHAT_ID` doğru tanımlandı mı?
* Bot ilgili kullanıcıya, gruba veya kanala mesaj gönderebiliyor mu?
* Bot gruba eklendiyse gerekli izinleri var mı?
* Ortam değişkenleri script çalıştırılan terminal oturumunda gerçekten mevcut mu?

Linux / macOS üzerinde kontrol etmek için:

```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

Windows PowerShell üzerinde kontrol etmek için:

```powershell
echo $env:TELEGRAM_BOT_TOKEN
echo $env:TELEGRAM_CHAT_ID
```

### Telegram token veya chat_id tanımlı değil mesajı alıyorum

Bu mesaj, scriptin ortam değişkenlerini okuyamadığı anlamına gelir.

Script şu değişkenleri bekler:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Yanlış örnek:

```bash
export BOT_TOKEN="..."
export CHAT_ID="..."
```

Doğru örnek:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
```

Windows PowerShell için doğru örnek:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="..."
```

### İlk çalıştırmada Telegram mesajı gelmedi

Bu normaldir.

Scriptin güncel davranışına göre ilk çalıştırmada mevcut son haber sadece kaydedilir. Telegram bildirimi gönderilmez.

Bildirim yalnızca daha sonra farklı bir haber ID değeri tespit edilirse gönderilir.

### Haber bulunamıyor

TFF sayfasının HTML yapısı değişmiş olabilir.

Script özellikle URL içinde `ftxtID` parametresi bulunan bağlantıları arar. Eğer site farklı bir URL yapısına geçerse `get_latest_news_once()` fonksiyonunun güncellenmesi gerekir.

### Türkçe karakterler bozuk görünüyor

Script sayfa encoding değerini şu şekilde ayarlar:

```python
response.encoding = "windows-1254"
```

Kaynak sayfanın karakter seti değişirse bu değer güncellenmelidir.

### SSL hatası alıyorum

Geçici olarak aşağıdaki ayar denenebilir:

```python
VERIFY_SSL = False
```

Ancak güvenlik açısından mümkünse SSL doğrulamasını açık bırakmak daha uygundur:

```python
VERIFY_SSL = True
```

### Tarayıcı açılmıyor

Script yeni haber bulunduğunda şu satır ile haber bağlantısını tarayıcıda açar:

```python
webbrowser.open_new_tab(latest["url"])
```

Bu özellik masaüstü bilgisayarda çalıştırıldığında uygundur.

Ancak script bir sunucuda, VPS üzerinde, Docker içinde veya grafik arayüzü olmayan bir ortamda çalıştırılıyorsa tarayıcı açılamayabilir.

Bu durumda ilgili satırı kaldırabilir veya yorum satırı yapabilirsiniz:

```python
# webbrowser.open_new_tab(latest["url"])
```
