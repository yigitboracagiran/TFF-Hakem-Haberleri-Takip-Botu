# TFF Hakem Haberleri Takip Botu

Bu Python scripti, TFF'nin hakem haberleri sayfasını belirli aralıklarla kontrol eder ve sayfada ilk sırada görünen haber daha önce bildirilmemişse kullanıcıyı bilgilendirir.

Yeni bir haber tespit edildiğinde script:

- Haber başlığını ve bağlantısını konsola yazar
- Telegram yapılandırılmışsa Telegram mesajı gönderir
- Haberi varsayılan web tarayıcısında açmayı dener
- Bildirim başarılı kabul edilirse haber ID'sini yerel JSON geçmişine kaydeder
- Son bildirilen en fazla 5 haber ID'sini saklar

> [!IMPORTANT]
> Güncel sürümde ilk çalıştırma sessiz değildir. State dosyası yoksa bildirim geçmişi boş kabul edilir ve sayfadaki ilk haber hemen bildirim sürecine alınır.

> [!NOTE]
> Script en büyük `ftxtID` değerini güncel haber olarak kabul etmez. TFF sayfasında ilk sırada görünen geçerli haber bağlantısını kullanır; çünkü `ftxtID` değerleri her zaman yayın sırasını göstermeyebilir.

## İçindekiler

- [Özellikler](#özellikler)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Proje Yapısı](#proje-yapısı)
- [Yapılandırma](#yapılandırma)
- [Telegram Ayarları](#telegram-ayarları)
- [Çalıştırma](#çalıştırma)
- [Çalışma Mantığı](#çalışma-mantığı)
- [İlk Çalıştırma Davranışı](#ilk-çalıştırma-davranışı)
- [Bildirim Başarı Kriteri](#bildirim-başarı-kriteri)
- [State Dosyası](#state-dosyası)
- [Örnek Log Çıktıları](#örnek-log-çıktıları)
- [Hata Yönetimi](#hata-yönetimi)
- [Olası Sorunlar](#olası-sorunlar)
- [Güvenlik Notları](#güvenlik-notları)

## Özellikler

- TFF hakem haberleri sayfasını varsayılan olarak her 60 saniyede bir kontrol eder
- Her turda yalnızca bir HTTP isteğiyle güncel sayfayı alır
- URL'ye benzersiz `_hard_refresh` parametresi ekleyerek önbellekte kalmış HTML kullanma ihtimalini azaltır
- Her kontrolde yeni bir `requests.Session` ve yeni bağlantı kullanır
- `Cache-Control`, `Pragma`, `Expires` ve `Connection` başlıklarıyla zorla yenilemeye benzer bir istek gönderir
- Sayfadaki bağlantıları HTML sırasına göre inceler
- İlk geçerli `ftxtID` içeren haber bağlantısını güncel haber kabul eder
- Aynı habere ait yinelenen bağlantıları ID üzerinden eler
- Telegram bildirimi gönderebilir
- Haberi varsayılan tarayıcıda açabilir
- Son bildirilen 5 haber ID'sini JSON dosyasında saklar
- Eski state dosyası biçimini okuyabilir
- State dosyasını geçici dosya üzerinden güvenli şekilde günceller
- Ağ, JSON ve genel çalışma hatalarını loglayıp sonraki kontrole devam eder

## Gereksinimler

- Python 3
- İnternet bağlantısı
- İsteğe bağlı olarak Telegram bot token ve chat ID bilgileri
- Masaüstünde tarayıcı açma özelliği için grafik arayüzü ve varsayılan tarayıcı

### Standart kütüphane modülleri

Aşağıdaki modüller Python ile birlikte gelir ve ayrıca kurulmaz:

```text
json
os
time
webbrowser
datetime
pathlib
urllib.parse
```

### Harici paketler

```text
requests
urllib3
beautifulsoup4
```

## Kurulum

Projeyi indirdikten veya dosyaları aynı klasöre yerleştirdikten sonra bağımlılıkları kurun:

```bash
python3 -m pip install requests urllib3 beautifulsoup4
```

Windows üzerinde `python3` komutu tanımlı değilse:

```powershell
python -m pip install requests urllib3 beautifulsoup4
```

## Proje Yapısı

```text
tff-hakem-haberleri/
├── haber.py
├── README.md
└── tff_hakem_son_haber.json
```

`tff_hakem_son_haber.json` dosyasını elle oluşturmanız gerekmez. Dosya, bir haber bildirimi başarılı kabul edildiğinde script tarafından oluşturulur.

Yazma işlemi sırasında geçici olarak şu dosya da görülebilir:

```text
tff_hakem_son_haber.json.tmp
```

Başarılı yazma işleminden sonra geçici dosya asıl state dosyasının üzerine taşınır.

## Yapılandırma

Temel ayarlar `haber.py` dosyasının üst bölümündedir.

### `LIST_URL`

Kontrol edilecek TFF haber listesi:

```python
LIST_URL = "https://www.tff.org/default.aspx?pageID=248"
```

### `CHECK_EVERY_SECONDS`

İki kontrol turu arasında beklenecek süre:

```python
CHECK_EVERY_SECONDS = 60
```

Varsayılan ayarla sayfa her 60 saniyede bir kontrol edilir.

### `MAX_STORED_IDS`

State dosyasında tutulacak son bildirim ID'si sayısı:

```python
MAX_STORED_IDS = 5
```

Liste temizlenirken:

- Boş değerler atılır
- Yinelenen ID'ler kaldırılır
- Aynı ID yeniden eklenirse en sona taşınır
- Yalnızca son 5 ID saklanır

### `STATE_FILE`

Bildirim geçmişinin yazılacağı dosya:

```python
STATE_FILE = Path("tff_hakem_son_haber.json")
```

Göreli yol kullanıldığı için dosya, scriptin çalıştırıldığı mevcut terminal klasöründe oluşturulur. Scripti farklı bir klasörden çalıştırırsanız state dosyası da o klasörde aranır veya oluşturulur.

### `VERIFY_SSL`

TFF isteğinde SSL sertifika doğrulamasını kontrol eder:

```python
VERIFY_SSL = False
```

Mümkün olduğu durumlarda daha güvenli seçenek şudur:

```python
VERIFY_SSL = True
```

`False` kullanıldığında `InsecureRequestWarning` uyarıları kapatılır. Bu ayar yalnızca TFF sayfasına gönderilen isteği etkiler; Telegram isteği standart HTTPS doğrulamasıyla gönderilir.

### `HEADERS`

Script, tarayıcı isteğine benzeyen ayrıntılı HTTP başlıkları kullanır. Başlıca değerler:

```python
HEADERS = {
    "User-Agent": "...Chrome/126.0 Safari/537.36",
    "Accept": "text/html,...",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
}
```

İstek sırasında ayrıca `Referer` başlığı eklenir.

### Telegram ortam değişkenleri

Script Telegram bilgilerini kaynak koddan değil, şu ortam değişkenlerinden okur:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Kod içindeki karşılıkları:

```python
BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()
```

Her iki değer de doluysa Telegram yapılandırılmış kabul edilir.

## Telegram Ayarları

Telegram bildirimi isteğe bağlıdır. Kullanmak için bir bot token ve hedef sohbet ID'si gerekir.

### BotFather ile bot token alma

1. Telegram'da resmi `@BotFather` hesabını açın.
2. Aşağıdaki komutu gönderin:

```text
/newbot
```

3. Bot için görünen bir ad belirleyin.
4. `bot` ile biten benzersiz bir kullanıcı adı belirleyin.
5. BotFather tarafından verilen token değerini güvenli bir yerde saklayın.

Token biçimi genellikle şöyledir:

```text
123456789:ABCDefGhIJKlmNoPQRstuVWXyz
```

Token'ı kaynak koda yazmayın.

Token yenilemek gerektiğinde BotFather üzerinden şu komut kullanılabilir:

```text
/token
```

Yeni token oluşturulduğunda eski token geçersiz hale gelir.

### Kişisel sohbet için chat ID alma

1. Oluşturduğunuz botla Telegram'da sohbet başlatın.
2. Bota en az bir mesaj gönderin.
3. Tarayıcıda şu adresi açın:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. JSON yanıtında `message.chat.id` değerini bulun.

Örnek:

```json
{
  "message": {
    "chat": {
      "id": 123456789,
      "type": "private"
    }
  }
}
```

Bu örnekte kullanılacak değer:

```text
123456789
```

### Grup için chat ID alma

1. Botu gruba ekleyin.
2. Grupta yeni bir mesaj gönderin.
3. `getUpdates` yanıtında ilgili `message.chat.id` değerini bulun.

Grup veya süper grup ID'si çoğunlukla negatif olur:

```text
-1001234567890
```

Botun gruba mesaj gönderebilmesi için gerekli izinlere sahip olduğundan emin olun.

### Kanal için chat ID alma

1. Botu kanala yönetici olarak ekleyin.
2. Kanalda yeni bir test gönderisi paylaşın.
3. `getUpdates` yanıtında `channel_post.sender_chat.id` alanını kontrol edin.

Hedef kanalın negatif ID değerini eksiksiz kullanın.

### `getUpdates` boş gelirse

Şu tür bir yanıt görüyorsanız:

```json
{
  "ok": true,
  "result": []
}
```

şunları kontrol edin:

- Botla sohbet başlatıldı mı?
- Bota veya gruba yeni bir mesaj gönderildi mi?
- Kanalda bot eklendikten sonra yeni bir gönderi paylaşıldı mı?
- Doğru bot token kullanılıyor mu?
- Bot başka bir uygulama tarafından webhook ile kullanılıyor mu?

## Çalıştırma

### Linux / macOS

Telegram ile çalıştırmak için:

```bash
export TELEGRAM_BOT_TOKEN="bot_token_buraya"
export TELEGRAM_CHAT_ID="chat_id_buraya"

python3 haber.py
```

Telegram kullanmadan çalıştırmak için:

```bash
python3 haber.py
```

### Windows PowerShell

Telegram ile çalıştırmak için:

```powershell
$env:TELEGRAM_BOT_TOKEN="bot_token_buraya"
$env:TELEGRAM_CHAT_ID="chat_id_buraya"

python haber.py
```

Telegram kullanmadan çalıştırmak için:

```powershell
python haber.py
```

Programı durdurmak için:

```text
Ctrl + C
```

Program kapanırken şu mesajı yazar:

```text
Program kullanıcı tarafından durduruldu.
```

## Çalışma Mantığı

Her kontrol turunda aşağıdaki adımlar uygulanır:

1. `LIST_URL` sonuna benzersiz bir `_hard_refresh` değeri eklenir.
2. Yeni bir `requests.Session` oluşturulur.
3. Sayfa, önbelleği azaltmaya yönelik başlıklarla bir kez indirilir.
4. HTTP yanıtında mevcutsa `Date`, `Age`, `Cache-Control`, `ETag`, `X-Cache` gibi önbellek başlıkları loglanır.
5. Yanıt karakter kodlaması `windows-1254` olarak ayarlanır.
6. HTML, Beautiful Soup ile ayrıştırılır.
7. Tüm `<a>` bağlantıları sayfadaki sıralarıyla incelenir.
8. URL sorgusunda `ftxtID` bulunmayan bağlantılar atlanır.
9. Başlığı boş olan veya `-` ile başlayan bağlantılar atlanır.
10. `ftxtID` tam sayıya çevrilemeyen bağlantılar atlanır.
11. Aynı ID'ye ait tekrarlanan bağlantılar elenir.
12. Kalan ilk bağlantı güncel haber olarak seçilir.
13. Haber ID'si state geçmişinde varsa yeni bildirim gönderilmez.
14. ID geçmişte yoksa Telegram ve tarayıcı bildirimleri denenir.
15. Bildirim başarılı kabul edilirse ID state dosyasına eklenir.
16. Script bir sonraki kontrol için `CHECK_EVERY_SECONDS` kadar bekler.

### Neden en büyük `ftxtID` seçilmiyor?

`ftxtID` sayısının büyüklüğü her zaman yayın sırasını göstermeyebilir. Daha yeni bir haber daha küçük bir ID'ye sahip olabilir.

Bu nedenle güncel sürüm:

```text
En büyük ID
```

yerine:

```text
Sayfada ilk görünen geçerli haber
```

yaklaşımını kullanır.

### Önbelleği azaltma yaklaşımı

İstek URL'si her turda benzersiz hale getirilir:

```python
request_url = (
    f"{LIST_URL}&_hard_refresh={time.time_ns()}"
)
```

Ayrıca:

- Yeni session açılır
- `Connection: close` kullanılır
- Önbellek karşıtı HTTP başlıkları gönderilir
- `Referer` başlığı eklenir

Bu işlemler eski HTML dönme ihtimalini azaltır ancak sunucu veya ara ağ katmanlarının hiçbir zaman önbellek kullanmayacağını garanti etmez.

## İlk Çalıştırma Davranışı

State dosyası yoksa script boş bir bildirim geçmişiyle başlar:

```text
State dosyası bulunamadı. Boş bildirim geçmişi kullanılacak.
```

Sayfanın ilk haber ID'si boş listede bulunmayacağı için haber yeni kabul edilir ve bildirim süreci hemen başlatılır.

Bu nedenle ilk çalıştırmada:

- Telegram yapılandırılmışsa mesaj gönderilmeye çalışılır
- Haber tarayıcıda açılmaya çalışılır
- Başarı kriteri sağlanırsa ID state dosyasına kaydedilir

Mevcut haberi ilk çalıştırmada bildirmek istemiyorsanız scripti çalıştırmadan önce state dosyasını yeni biçimde elle hazırlayabilirsiniz:

```json
{
  "notified_ids": ["MEVCUT_HABER_ID"],
  "updated_at": "2026-07-30T16:30:00"
}
```

`MEVCUT_HABER_ID` yerine TFF bağlantısındaki gerçek `ftxtID` değerini yazın.

## Bildirim Başarı Kriteri

Yeni bir haber bulunduğunda işlemler şu sırada yapılır:

1. Telegram mesajı gönderilmeye çalışılır
2. Haber tarayıcıda açılmaya çalışılır
3. Sonuçlara göre ID'nin kaydedilip kaydedilmeyeceğine karar verilir

### Telegram yapılandırılmışsa

`TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` doluysa Telegram yapılandırılmış kabul edilir.

Bu durumda haber ID'sinin kaydedilebilmesi için Telegram gönderiminin başarılı olması gerekir.

Telegram gönderimi başarısız olursa:

- Haber tarayıcıda yine açılmaya çalışılmış olur
- ID state dosyasına kaydedilmez
- Aynı haber bir sonraki kontrolde yeniden denenir

### Telegram yapılandırılmamışsa

Telegram bilgileri eksikse mesaj atlanır:

```text
Telegram token veya chat_id tanımlı değil. Telegram bildirimi atlanacak.
```

Bu durumda haber ID'sinin kaydedilebilmesi için tarayıcının başarıyla açılmış olması gerekir.

Tarayıcı da açılamazsa:

- ID kaydedilmez
- Aynı haber sonraki kontrolde yeniden denenir

> [!WARNING]
> Telegram kullanmadan headless sunucu, VPS, Docker veya grafik arayüzü olmayan bir ortamda çalıştırırsanız tarayıcı açılamayabilir. Bu durumda haber ID'si kaydedilmez ve aynı haber her kontrolde yeniden işlenir.

## State Dosyası

### Güncel biçim

State dosyası artık tek bir haber nesnesi yerine son bildirilen ID listesini saklar:

```json
{
  "notified_ids": [
    "100",
    "101",
    "102"
  ],
  "updated_at": "2026-07-30T16:30:00"
}
```

Alanlar:

| Alan | Açıklama |
|---|---|
| `notified_ids` | Başarılı kabul edilen son bildirimlerin ID listesi |
| `updated_at` | State dosyasının son yazılma zamanı |
| Azami liste boyutu | `MAX_STORED_IDS`, varsayılan olarak 5 |

### Eski biçim desteği

Aşağıdaki eski state biçimi de okunabilir:

```json
{
  "id": "102",
  "title": "Haber başlığı",
  "url": "https://..."
}
```

Eski biçimdeki `id` değeri bildirim geçmişine alınır. Bir sonraki başarılı state yazımında dosya güncel `notified_ids` biçimiyle kaydedilir.

### Geçersiz veya bozuk state dosyası

Dosya:

- Geçerli JSON değilse
- Beklenen nesne biçiminde değilse
- `notified_ids` alanı liste değilse
- Okuma sırasında dosya sistemi hatası oluşursa

script hatayı loglar ve boş geçmiş kullanır.

Bu durumda sayfadaki ilk haber yeniden bildirim sürecine alınabilir.

### State dosyasını sıfırlama

Tüm bildirim geçmişini sıfırlamak için program kapalıyken dosyayı silebilirsiniz:

```bash
rm tff_hakem_son_haber.json
```

Windows PowerShell:

```powershell
Remove-Item .\tff_hakem_son_haber.json
```

Sonraki çalıştırmada mevcut ilk haber yeni kabul edilir.

## Örnek Log Çıktıları

Aşağıdaki örneklerde tarih ve haber bilgileri temsilidir.

### Program başlangıcı

```text
30.07.2026-16:30 TFF hakem haberleri takip ediliyor...
30.07.2026-16:30 Sayfa her 60 saniyede bir, her turda yalnızca bir kez kontrol edilecek.
30.07.2026-16:30 State dosyası bulunamadı. Boş bildirim geçmişi kullanılacak.
```

### Sayfanın alınması

Sunucu ilgili başlıkları döndürürse:

```text
30.07.2026-16:30 Yenileme yanıtı: Date=Thu, 30 Jul 2026 13:30:00 GMT; Cache-Control=private
30.07.2026-16:30 Yenilenen sayfanın ilk haberi: Haber başlığı - ID: 12345
```

### Yeni haber ve başarılı Telegram bildirimi

```text
30.07.2026-16:30 Sayfanın ilk haberindeki ID 12345, JSON bildirim geçmişinde bulunamadı. Bildirim gönderiliyor.
30.07.2026-16:30 Bildirim gönderilecek haber: Haber başlığı
30.07.2026-16:30 https://www.tff.org/...
30.07.2026-16:30 Telegram mesajı gönderildi.
30.07.2026-16:30 Haber tarayıcıda açıldı.
30.07.2026-16:30 Kaydedilen son bildirim ID'leri: 12345
30.07.2026-16:30 Sonraki kontrol için 60 saniye bekleniyor.
```

### Haber daha önce bildirilmişse

```text
30.07.2026-16:31 Bu haber JSON geçmişinde kayıtlı: Haber başlığı - ID: 12345
30.07.2026-16:31 Sonraki kontrol için 60 saniye bekleniyor.
```

### Telegram yapılandırılmamışsa

```text
30.07.2026-16:30 Telegram token veya chat_id tanımlı değil. Telegram bildirimi atlanacak.
30.07.2026-16:30 Haber tarayıcıda açıldı.
30.07.2026-16:30 Kaydedilen son bildirim ID'leri: 12345
```

### Telegram gönderimi başarısızsa

```text
30.07.2026-16:30 Telegram mesajı gönderilemedi: ...
30.07.2026-16:30 Haber tarayıcıda açıldı.
30.07.2026-16:30 Telegram bildirimi başarısız olduğu için haber ID'si kaydedilmedi.
```

## Telegram Mesaj Biçimi

Yeni haber mesajı şu biçimde oluşturulur:

```text
📰 Yeni TFF hakem haberi

Haber başlığı

https://haber-linki
```

Telegram bağlantı önizlemesi kapatılmaz:

```python
"disable_web_page_preview": False
```

## Hata Yönetimi

Ana döngü aşağıdaki hataları loglar ve bir sonraki kontrol turuna geçer:

- TFF sayfasına erişim hataları
- HTTP durum kodu hataları
- Bağlantı zaman aşımı
- Sayfada uygun haber bağlantısı bulunamaması
- Haber ID'sinin boş veya sayısal olmaması
- State dosyasının okunamaması
- Telegram API isteği hataları
- Telegram yanıtının JSON olarak okunamaması
- Tarayıcı açma hataları
- Beklenmeyen diğer hatalar

TFF istek hatası örneği:

```text
TFF sayfasına erişilirken hata oluştu: ...
```

Genel hata örneği:

```text
Hata: ...
```

Telegram API HTTP isteği başarılı olsa bile JSON içinde `ok` değeri doğru değilse gönderim başarısız kabul edilir.

## Olası Sorunlar

### İlk çalıştırmada hemen bildirim geldi

Bu güncel sürüm için normal davranıştır.

State dosyası bulunamazsa geçmiş boş kabul edilir ve sayfadaki ilk haber bildirim sürecine alınır.

İlk haberi bildirmeden başlangıç kaydı olarak kullanmak için state dosyasını önceden ilgili ID ile oluşturun.

### Aynı haber tekrar tekrar açılıyor

Bunun başlıca nedenleri:

- Telegram yapılandırılmış ancak mesaj gönderimi başarısız oluyor
- Telegram yapılandırılmamış ve `webbrowser.open_new_tab()` başarılı sonuç döndürmüyor
- State dosyası yazılamıyor
- Script her seferinde farklı çalışma klasöründen başlatılıyor
- State dosyası bozuk veya geçersiz biçimde

ID yalnızca bildirim başarılı kabul edildiğinde kaydedilir. Kaydedilmeyen ID bir sonraki kontrolde yeniden denenir.

### Telegram mesajı gelmiyor

Kontrol edin:

- `TELEGRAM_BOT_TOKEN` doğru mu?
- `TELEGRAM_CHAT_ID` doğru mu?
- Botla kişisel sohbet başlatıldı mı?
- Bot grup veya kanalda gerekli izinlere sahip mi?
- Ortam değişkenleri scriptin çalıştığı terminal oturumunda tanımlı mı?
- Bot token yenilendiyse eski değer kullanılmaya devam ediyor mu?
- Ağ, Telegram API alan adına erişebiliyor mu?

Linux / macOS:

```bash
printf '%s\n' "$TELEGRAM_CHAT_ID"
```

Windows PowerShell:

```powershell
$env:TELEGRAM_CHAT_ID
```

Token değerini ekran görüntülerinde veya loglarda paylaşmayın.

### `Telegram token veya chat_id tanımlı değil` mesajı

Script şu isimleri tam olarak bekler:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Yanlış:

```bash
export BOT_TOKEN="..."
export CHAT_ID="..."
```

Doğru:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
```

### Haber bulunamıyor

TFF sayfasının HTML veya bağlantı yapısı değişmiş olabilir.

Script şu koşulları sağlayan bağlantıları arar:

- `<a href="...">` etiketi olmalı
- URL sorgusunda `ftxtID` bulunmalı
- Bağlantı metni boş olmamalı
- Başlık `-` ile başlamamalı
- `ftxtID` tam sayıya çevrilebilmeli

Site farklı bir URL veya HTML yapısına geçerse `get_latest_news()` fonksiyonunun güncellenmesi gerekir.

### Güncel haber yerine eski haber seçiliyor

Script, sayfada ilk sırada bulunan uygun bağlantıyı seçer.

Kontrol edin:

- TFF sayfası gerçekten yeni haberi en üste koyuyor mu?
- Ara önbellek eski HTML döndürüyor mu?
- Loglarda `Age`, `ETag`, `X-Cache` veya benzeri önbellek başlıkları görünüyor mu?
- Kurumsal proxy, CDN veya güvenlik yazılımı isteği önbelleğe alıyor mu?

Script önbelleği azaltmaya yönelik önlemler uygular ancak uzak sistemlerin davranışını tamamen kontrol edemez.

### Türkçe karakterler bozuk

Kod yanıt karakter setini şu şekilde zorlar:

```python
response.encoding = "windows-1254"
```

TFF sayfasının karakter kodlaması değişirse bu satırın güncellenmesi gerekebilir.

### SSL hatası

TFF sunucusunun SSL yapılandırmasına göre şu ayar kullanılabilir:

```python
VERIFY_SSL = False
```

Güvenli bağlantı doğrulaması çalışıyorsa tercih edilen değer:

```python
VERIFY_SSL = True
```

SSL doğrulamasını kapatmanın güvenlik riskini dikkate alın.

### Tarayıcı açılmıyor

`webbrowser.open_new_tab()` masaüstü ortamlarında varsayılan tarayıcıyı açmayı dener.

Şu ortamlarda çalışmayabilir:

- VPS
- Docker
- SSH oturumu
- Grafik arayüzü olmayan Linux sunucusu
- Varsayılan tarayıcı yapılandırılmamış sistem

Telegram yapılandırılmış ve mesaj başarıyla gönderilmişse tarayıcının açılamaması ID'nin kaydedilmesini engellemez.

Telegram yapılandırılmamışsa tarayıcı başarıyla açılamadığında ID kaydedilmez.

### State dosyası beklediğim klasörde değil

`STATE_FILE` göreli bir yol kullandığı için dosya `haber.py` dosyasının bulunduğu klasöre değil, komutun çalıştırıldığı mevcut klasöre yazılır.

Örnek:

```bash
cd /proje
python3 haber.py
```

Bu durumda state dosyası `/proje` içinde oluşturulur.

Daha sabit bir konum istenirse kod şu şekilde değiştirilebilir:

```python
STATE_FILE = Path(__file__).resolve().with_name(
    "tff_hakem_son_haber.json"
)
```

Bu değişiklik mevcut kodun parçası değildir; isteğe bağlı bir uyarlamadır.

## Güvenlik Notları

- Telegram bot token'ını kaynak koda yazmayın
- Token'ı Git deposuna eklemeyin
- Token'ı ekran görüntüsü, log veya destek mesajında paylaşmayın
- Token açığa çıktıysa BotFather üzerinden yenileyin
- State dosyası token içermez; yalnızca haber ID'leri ve güncelleme zamanı içerir
- Mümkünse `VERIFY_SSL = True` kullanın
- Ortam değişkenlerini yalnızca scriptin çalıştığı kullanıcı hesabında erişilebilir tutun

Yanlış kullanım:

```python
BOT_TOKEN = "gercek_token"
CHAT_ID = "gercek_chat_id"
```

Doğru yaklaşım:

```python
BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()
```
