# Instagram Video Scraping Guide

## 🎯 Özellikler

Sistem artık **gerçek Instagram profillerinden video indirebiliyor**!

### Ne Yapıyor?

1. ✅ Instagram profillerini buluyor (instaloader ile)
2. ✅ En çok izlenen/beğenilen videoları seçiyor
3. ✅ Sadece video içeriği (reels, IGTV) indiriyor
4. ✅ Performansa göre sıralama yapıyor (views, engagement, likes)
5. ✅ Top N en iyi videoları alıyor

---

## 🚀 Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

Bu şunları yükler:
- `instaloader==4.11` - Instagram scraping için
- `yt-dlp==2024.3.10` - Video indirme için
- Diğer tüm bağımlılıklar

### 2. Veritabanını Hazırla

```bash
# PostgreSQL'in çalıştığından emin ol
# Veritabanını oluştur:
createdb realestate_intel

# Tabloları oluştur:
python scripts/init_db.py
```

### 3. Ayarları Yapılandır

`.env` dosyasını düzenle:

```bash
# Instagram gerçek scraping'i aktif et
USE_MOCK_SCRAPERS=false

# Video filtreleme ayarları
VIDEO_FINDER_DAYS_BACK=90        # Son 90 gündeki videolar
VIDEO_FINDER_MIN_VIEWS=1000      # Minimum 1000 izlenme
VIDEO_FINDER_TOP_N=50            # Profil başına en iyi 50 video
VIDEO_SORT_BY=views              # Sıralama: views, engagement, likes
```

---

## 📊 Sıralama Seçenekleri

### 1. **views** (Varsayılan)
En çok izlenen videolar

```bash
VIDEO_SORT_BY=views
```

### 2. **engagement**
En yüksek etkileşim oranı: `(likes + comments * 3) / views`

```bash
VIDEO_SORT_BY=engagement
```

### 3. **likes**
En çok beğenilen videolar

```bash
VIDEO_SORT_BY=likes
```

---

## 💻 Kullanım

### Tam Pipeline (Şirket Keşfi → Profil Bulma → Video İndirme)

```bash
python main.py --city "Miami" --country "USA" --limit 10
```

**Çıktı:**
```
============================================================
PIPELINE RESULTS
============================================================
Companies Discovered:  10
Social Profiles Found: 8   (sadece Instagram)
Video Posts Found:     400  (tüm profillerdeki videolar)
Videos Downloaded:     50   (profil başına top 50 = toplam 400)
============================================================
```

### Sadece Instagram'a Odaklan

Sistem şu anda **sadece Instagram** profillerini işliyor. TikTok ve YouTube mock data'da kalıyor.

---

## 📁 İndirilen Videolar

Videolar burada saklanıyor:

```
data/downloads/instagram/
├── C12345ABC.mp4
├── C23456DEF.mp4
├── C34567GHI.mp4
└── ...
```

Her video dosyası `external_post_id` ile adlandırılıyor (Instagram shortcode).

---

## 🔍 Örnek: Gerçek Instagram Profil Arama

```python
from scrapers.social.instagram import InstagramScraper

scraper = InstagramScraper(use_mock=False)

# Profil bul
profile = scraper.find_profile("Luxury Homes Miami")

# Output:
{
    "username": "luxuryhomesmiami",
    "profile_url": "https://instagram.com/luxuryhomesmiami",
    "followers_count": 45000,
    "posts_count": 312,
    "bio": "Luxury Real Estate in Miami...",
    "avg_likes": 850,
    "avg_comments": 23,
    "posts_per_week": 5.2,
    "video_ratio": 0.72
}

# Videoları çek
posts = scraper.get_recent_posts("https://instagram.com/luxuryhomesmiami", limit=100)

# En iyi 50 videoyu seç (VideoFinderAgent otomatik yapar)
```

---

## ⚙️ Performans Optimizasyonu

### 1. Az Profil, Çok Video

```bash
COMPANY_DISCOVERY_DEFAULT_LIMIT=5    # Sadece 5 şirket
VIDEO_FINDER_TOP_N=100               # Her birinden 100 video
VIDEO_FINDER_MIN_VIEWS=5000          # Daha kaliteli içerik
```

### 2. Çok Profil, Az Video

```bash
COMPANY_DISCOVERY_DEFAULT_LIMIT=50   # 50 şirket
VIDEO_FINDER_TOP_N=10                # Her birinden sadece 10 en iyisi
VIDEO_FINDER_MIN_VIEWS=10000         # Sadece viral olanlar
```

### 3. Sadece Yüksek Engagement

```bash
VIDEO_SORT_BY=engagement             # Engagement'a göre sırala
VIDEO_FINDER_MIN_VIEWS=2000
VIDEO_FINDER_TOP_N=30
```

---

## 🛡️ Rate Limiting ve Güvenlik

### Instagram Rate Limit

Instagram, instaloader kullanımında rate limiting uygular:

- **Oturum açmadan:** ~200-300 istek/saat
- **Oturum açarak:** Daha yüksek limitler

### Dikkat Edilmesi Gerekenler

1. ⚠️ **Çok hızlı scraping yapma** - Her istek arasında delay ekle
2. ⚠️ **Proxy kullan** - Büyük ölçekli scraping için
3. ⚠️ **Login gerekebilir** - Bazı profiller için oturum açmak gerekir

### Login Eklemek (Opsiyonel)

İleride `instagram.py` dosyasına login eklenebilir:

```python
L = instaloader.Instaloader()
L.login("kullaniciadi", "sifre")  # Login
```

Şu an için **login olmadan** çalışıyor (public profiller için).

---

## 📈 Veritabanında Saklanan Bilgiler

### Social Profiles

```sql
SELECT
    username,
    followers_count,
    engagement_score,
    content_type
FROM social_profiles
WHERE platform = 'instagram'
ORDER BY engagement_score DESC;
```

### Top Performing Videos

```sql
SELECT
    post_url,
    view_count,
    like_count,
    comment_count,
    caption_text
FROM social_posts
WHERE platform = 'instagram'
ORDER BY view_count DESC
LIMIT 50;
```

### Download Status

```sql
SELECT
    status,
    COUNT(*) as count
FROM video_download_jobs
WHERE platform = 'instagram'
GROUP BY status;
```

Expected:
```
status      | count
-----------+-------
done        |   400
error       |     5
pending     |     0
```

---

## 🐛 Troubleshooting

### Hata: "instaloader not installed"

```bash
pip install instaloader==4.11
```

### Hata: "Profile not found"

- Şirket adı Instagram username ile eşleşmiyor
- Manuel olarak username'i belirtmek gerekebilir
- Veya mock data kullan: `USE_MOCK_SCRAPERS=true`

### Hata: "Too many requests"

Rate limit'e takıldınız:
- Daha az profil dene (`--limit 5`)
- İstekler arasında delay ekle
- Proxy kullan

### Hata: "Login required"

Bazı private/restricted profiller için:
- `instagram.py` dosyasına login kodu ekle
- Veya sadece public profillerle çalış

---

## 🎓 Örnekler

### Örnek 1: Miami'deki En İyi 10 Şirket

```bash
python main.py --city "Miami" --country "USA" --limit 10
```

### Örnek 2: Sadece Viral Videolar (10K+ views)

`.env` dosyasında:
```bash
VIDEO_FINDER_MIN_VIEWS=10000
VIDEO_SORT_BY=views
VIDEO_FINDER_TOP_N=20
```

Sonra:
```bash
python main.py --city "Los Angeles" --country "USA" --limit 20
```

### Örnek 3: En Yüksek Engagement

`.env` dosyasında:
```bash
VIDEO_SORT_BY=engagement
VIDEO_FINDER_TOP_N=30
```

---

## 🔮 Gelecek İyileştirmeler

- [ ] Login desteği (daha fazla profil erişimi)
- [ ] Proxy rotation (rate limit aşımı için)
- [ ] Paralel scraping (daha hızlı)
- [ ] Story indirme
- [ ] Hashtag bazlı arama
- [ ] Competitor analysis

---

## 📞 Destek

Sorun mu var?

1. `.env` dosyasını kontrol et (`USE_MOCK_SCRAPERS=false`)
2. `pip install -r requirements.txt` çalıştır
3. PostgreSQL'in çalıştığından emin ol
4. Log'lara bak (konsol çıktısı)

---

**Artık gerçek Instagram videoları indirmeye hazırsın!** 🚀
