# TFF Hakem Haberleri Takip Botu

Bu Python scripti, TFF web sitesindeki hakem haberlerini belirli aralıklarla kontrol eder. Yeni bir haber bulunduğunda:

* Haber başlığını konsola yazar
* Haber bağlantısını tarayıcıda açar
* Telegram üzerinden bildirim gönderir
* Son görülen haber bilgisini yerel bir JSON dosyasına kaydeder

## Özellikler

* TFF haber listesinden en güncel hakem haberini tespit eder
* Haberleri `ftxtID` değerine göre karşılaştırır
* Aynı kontrolü birden fazla kez yaparak daha güvenilir sonuç seçer
* Telegram bildirimi gönderir
* Yeni haber bulunduğunda otomatik olarak tarayıcıda açar
* Son haber ID bilgisini dosyada sakladığı için program yeniden başlatıldığında kaldığı yerden devam eder

## Gereksinimler

Gerekli Python paketleri:

```bash
pip install requests beautifulsoup4
```

### Değişken Açıklamaları

`LIST_URL`
Kontrol edilecek TFF haber liste sayfasının adresidir.

`HEADERS`
HTTP isteği gönderilirken kullanılacak başlıklardır. Bazı siteler varsayılan Python isteklerini engelleyebileceği için `User-Agent` tanımlamak faydalıdır.

`VERIFY_SSL`
SSL doğrulamasının aktif olup olmayacağını belirler. Genellikle `True` bırakılması önerilir.

`BOT_TOKEN`
Telegram bot token bilgisidir. BotFather üzerinden alınır.

`CHAT_ID`
Bildirim gönderilecek Telegram kullanıcı, grup veya kanal ID bilgisidir.

`STATE_FILE`
Son görülen haber bilgisinin kaydedileceği JSON dosyasıdır.

`CHECK_EVERY_SECONDS`
Ana döngüde iki kontrol arasında beklenecek süredir.

`REFRESH_COUNT`
Her kontrol turunda kaç kez haber sorgusu yapılacağını belirler.

`REFRESH_DELAY_SECONDS`
Aynı kontrol turundaki sorgular arasında beklenecek süredir.

## Çalıştırma

Script dosyasını örneğin `haber.py` olarak kaydedin.

Ardından terminalden çalıştırın:

```bash
python3 haber.py
```

Program çalıştığında konsolda şu şekilde loglar üretir:

```text
30.06.2026-14:25 TFF hakem haberleri takip ediliyor...
30.06.2026-14:25 Kontrol 1/3: Haber başlığı - 12345
30.06.2026-14:25 Seçilen çoğunluk haber: Haber başlığı (3/3)
30.06.2026-14:25 Yeni haber yok. Son haber: Haber başlığı
```

Programı durdurmak için:

```bash
Ctrl + C
```

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

## İlk Çalıştırma Davranışı

Program ilk kez çalıştırıldığında daha önce kaydedilmiş bir haber ID bilgisi yoksa mevcut son haberi ilk kayıt olarak kabul eder.

Bu durumda:

* Haber bilgisi `STATE_FILE` içine kaydedilir
* Haber bağlantısı tarayıcıda açılır
* Telegram bildirimi gönderilir

Eğer ilk çalıştırmada bildirim gönderilmesini istemiyorsanız, `main()` fonksiyonundaki ilk kayıt bloğunda yer alan şu bölümleri kaldırabilir veya yorum satırı yapabilirsiniz:

```python
webbrowser.open_new_tab(latest["url"])

send_telegram_message(
    "Yeni TFF hakem haberi",
    latest["title"],
    latest["url"]
)
```

## Telegram Bildirimi

Yeni haber bulunduğunda Telegram mesajı şu formatta gönderilir:

```text
📰 Yeni TFF hakem haberi

Haber başlığı

https://haber-linki
```

Telegram bildirimi göndermek için `BOT_TOKEN` ve `CHAT_ID` değerlerinin doğru tanımlanmış olması gerekir.

Eğer bu değerlerden biri eksikse program hata vermez, sadece konsola şu mesajı yazar:

```text
Telegram token veya chat_id tanımlı değil.
```

## Durum Dosyası

Son görülen haber bilgisi JSON formatında saklanır.

Örnek `last_news.json` içeriği:

```json
{
  "id": "12345",
  "title": "Haber başlığı",
  "url": "https://..."
}
```

Bu dosya sayesinde script yeniden başlatıldığında aynı haberi tekrar yeni haber olarak algılamaz.

## Hata Yönetimi

Script aşağıdaki durumlarda hata mesajını konsola yazar ve çalışmaya devam eder:

* Sayfa indirilemezse
* Bağlantı zaman aşımına uğrarsa
* HTML içinde uygun haber bağlantısı bulunamazsa
* Telegram bildirimi gönderilemezse
* Durum dosyası okunamazsa

Ana döngüde oluşan hatalar programı durdurmaz. Sadece loglanır ve bir sonraki kontrol zamanı beklenir.

## Olası Sorunlar

### Telegram mesajı gelmiyor

Kontrol edilmesi gerekenler:

* `BOT_TOKEN` doğru mu?
* `CHAT_ID` doğru mu?
* Bot ilgili kullanıcıya, gruba veya kanala mesaj gönderebiliyor mu?
* Bot gruba eklendiyse gerekli izinleri var mı?

### Haber bulunamıyor

TFF sayfasının HTML yapısı değişmiş olabilir. Script özellikle URL içinde `ftxtID` parametresi bulunan bağlantıları arar. Eğer site farklı bir URL yapısına geçerse `get_latest_news_once()` fonksiyonunun güncellenmesi gerekir.

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

Ancak güvenlik açısından mümkünse SSL doğrulamasını açık bırakmak daha uygundur.

## Örnek Proje Yapısı

```text
tff-hakem-haberleri/
├── tff_hakem_takip.py
├── last_news.json
└── README.md
```

## Telegram Bot Token ve Chat ID Alma

Telegram bildirimi gönderebilmek için iki bilgiye ihtiyaç vardır:

* `BOT_TOKEN`
* `CHAT_ID`

`BOT_TOKEN`, Telegram botunuza ait API anahtarıdır.
`CHAT_ID`, mesajın gönderileceği kullanıcı, grup veya kanal kimliğidir.

### BotFather ile Bot Token Alma

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

Bu değeri script içinde `BOT_TOKEN` değişkenine yazabilirsiniz:

```python
BOT_TOKEN = "123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
```

> Bot token bilgisini kimseyle paylaşmayın. Bu token, botunuz adına mesaj göndermek için kullanılabilir.

### Bot Token Yenileme

Eğer bot token bilgisini kaybettiyseniz veya token başkasının eline geçtiyse BotFather üzerinden yeni token oluşturabilirsiniz.

1. Telegram’da `@BotFather` sohbetini açın.
2. Şu komutu gönderin:

```text
/token
```

3. BotFather size sahip olduğunuz botları listeler.
4. İlgili botu seçin.
5. BotFather yeni token üretir.

Yeni token üretildikten sonra eski token geçersiz olur. Bu nedenle script içindeki `BOT_TOKEN` değerini yeni token ile güncellemeniz gerekir.

### Chat ID Öğrenme

`CHAT_ID` değerini öğrenmek için önce botun mesaj göndereceği sohbetle etkileşim kurulmalıdır.

#### Kişisel Mesaj İçin Chat ID Alma

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

Buradaki `id` değeri sizin `CHAT_ID` değerinizdir.

Scriptte şu şekilde kullanılabilir:

```python
CHAT_ID = "123456789"
```

#### Grup İçin Chat ID Alma

Telegram bildiriminin bir gruba gönderilmesini istiyorsanız:

1. Botu ilgili Telegram grubuna ekleyin.
2. Grupta herhangi bir mesaj gönderin.
3. Tarayıcıdan şu adresi açın:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. JSON çıktısında grup sohbetine ait şu bölümü bulun:

```json
"chat": {
  "id": -1001234567890,
  "title": "Grup Adı",
  "type": "supergroup"
}
```

Buradaki `id` değeri grup için kullanılacak `CHAT_ID` değeridir.

Grup chat ID değerleri genellikle `-` işaretiyle başlar. Bu değeri eksiksiz kopyalamanız gerekir.

Örnek:

```python
CHAT_ID = "-1001234567890"
```

### getUpdates Boş Gelirse

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
* Doğru bot token kullanılıyor mu?

Mesaj gönderdikten sonra `getUpdates` adresini tekrar yenileyin.

### Telegram Ayarlarının Scriptte Kullanımı

Token ve chat ID bilgilerini aldıktan sonra scriptte ilgili değişkenleri şu şekilde tanımlayın:

```python
BOT_TOKEN = "123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
CHAT_ID = "123456789"
```

Grup için örnek:

```python
BOT_TOKEN = "123456789:ABCDefGhIJKlmNoPQRstuVWXyz"
CHAT_ID = "-1001234567890"
```

Bu ayarlar doğru yapıldığında script yeni haber bulduğunda Telegram üzerinden bildirim gönderecektir.
