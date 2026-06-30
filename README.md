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
