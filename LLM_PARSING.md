# LLM-Based Company Discovery

## 🎯 Genel Bakış

Sistem artık **Ollama + Gemma 2:2b** kullanarak HTML içeriğinden akıllı şirket çıkarımı yapıyor. Bu sayede:

✅ **Site-agnostic**: Realtor.com'a bağımlı değil, herhangi bir web sitesinden veri çıkarabilir
✅ **Uluslararası destek**: Avrupa, Türkiye, vs. lokal gayrimenkul sitelerinden çalışır
✅ **Dil-agnostic**: İngilizce, Türkçe, Almanca, Fransızca vb. destekler
✅ **Akıllı parsing**: Regex pattern'lara bağımlı değil, LLM anlam çıkarımı yapar

## 🏗️ Mimari

```
User Query (e.g., "Istanbul Turkey real estate")
    ↓
CompanyScraper
    ↓
Crawl4AI → HTML çeker (Google Search / Local Sites)
    ↓
LLMParser → Ollama + Gemma 2:2b
    ↓
Structured JSON (company data)
    ↓
Database'e kaydedilir
```

### 3 Katmanlı Strateji

1. **Primary**: Google Search + LLM (global, her dilde çalışır)
2. **Fallback**: Realtor.com + LLM (sadece USA için)
3. **Last Resort**: Generic regex parser

## 📦 Kurulum

### 1. Ollama'yı Kur ve Başlat

```powershell
# Ollama'yı indir ve kur
# https://ollama.ai/download

# Ollama'yı başlat
ollama serve

# Gemma 2:2b modelini indir (yeni terminalde)
ollama pull gemma2:2b
```

### 2. Environment Ayarları

`.env` dosyası zaten yapılandırılmış:

```env
# Ollama LLM Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b
OLLAMA_TIMEOUT=120
OLLAMA_TEMPERATURE=0.1
OLLAMA_MAX_TOKENS=4000
```

### 3. Veritabanını Başlat

```powershell
python scripts\init_db.py
```

### 4. API'yi Başlat

```powershell
python main.py --mode api
```

## 🚀 Kullanım

### API ile Discovery

```powershell
# Miami (USA) - Google + LLM
Invoke-RestMethod -Uri "http://localhost:8000/api/discover" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"city":"Miami","country":"USA","companies":10}'

# Istanbul (Turkey) - Lokal siteler + LLM
Invoke-RestMethod -Uri "http://localhost:8000/api/discover" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"city":"Istanbul","country":"Turkey","companies":20}'

# Berlin (Germany) - Almanca siteler + LLM
Invoke-RestMethod -Uri "http://localhost:8000/api/discover" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"city":"Berlin","country":"Germany","companies":15}'
```

### CLI ile Discovery

```powershell
# Türkiye örneği
python main.py --city Istanbul --country Turkey --limit 20

# Almanya örneği
python main.py --city Berlin --country Germany --limit 15

# İspanya örneği
python main.py --city Barcelona --country Spain --limit 10
```

## 🔍 LLM Nasıl Çalışıyor?

### 1. HTML'den Text Extraction

```python
# BeautifulSoup ile clean text
soup = BeautifulSoup(html, 'lxml')
text = soup.get_text(separator='\n', strip=True)
```

### 2. LLM Prompt

```
System: You are a data extraction assistant...

User: Extract real estate companies from this page.
Context: Istanbul Turkey real estate

Page content:
---
[cleaned HTML text]
---

Return JSON format.
```

### 3. Structured Output

```json
{
  "companies": [
    {
      "name": "Remax Türkiye",
      "website_url": "https://remax.com.tr",
      "source": "google_search"
    },
    {
      "name": "Century 21 İstanbul",
      "website_url": "https://century21.com.tr",
      "source": "google_search"
    }
  ]
}
```

### 4. Validation & Normalization

- Minimum name length check
- Generic term filtering ("click here", "learn more", etc.)
- URL normalization (http/https)
- Duplicate removal

## 🧪 Test Senaryoları

### Test 1: USA (Realtor.com fallback)

```powershell
python main.py --city "Los Angeles" --country USA --limit 10
```

**Beklenen**: Realtor.com'dan LLM ile extract edilmiş şirketler

### Test 2: Türkiye (Google + LLM)

```powershell
python main.py --city Istanbul --country Turkey --limit 20
```

**Beklenen**: Google'dan Türkçe gayrimenkul siteleri, LLM ile extract

### Test 3: Almanya (Google + LLM)

```powershell
python main.py --city Munich --country Germany --limit 15
```

**Beklenen**: Almanca emlak siteleri, LLM ile extract

## 📊 Monitoring & Debugging

### Ollama Logları

```powershell
# Ollama servisinin çalıştığını kontrol et
curl http://localhost:11434/api/tags

# Response:
# {"models":[{"name":"gemma2:2b",...}]}
```

### Application Logları

Loglar detaylı bilgi verir:

```
INFO: Strategy 1: Google Search + LLM: https://google.com/search?q=...
INFO: LLM parser returned 15 companies from Google
INFO: Successfully scraped 15 companies
```

### Hata Senaryoları

**Ollama çalışmıyor:**
```
WARNING: Ollama not available
HINT: Make sure Ollama is running: 'ollama serve'
```

**Model yüklü değil:**
```
WARNING: Model gemma2:2b not found
HINT: Run: ollama pull gemma2:2b
```

**LLM parse hatası:**
```
WARNING: LLM did not return valid JSON
INFO: Falling back to regex parser
```

## ⚙️ Optimization

### Model Seçimi

Şu anda `gemma2:2b` kullanıyoruz (hafif ve hızlı).

Alternatifler:
- `gemma2:2b` - ✅ Hızlı, orta kalite (şu anki)
- `gemma3:4b` - Daha yavaş, daha iyi kalite
- `llama3:8b` - En iyi kalite, en yavaş

`.env` dosyasından değiştirebilirsiniz:

```env
OLLAMA_MODEL=gemma3:4b
```

### Cache Stratejisi

Crawl4AI cache aktif (24 saat):

```env
CRAWL4AI_CACHE_ENABLED=true
CRAWL4AI_CACHE_EXPIRY_HOURS=24
```

Cache lokasyonu: `data/crawl_cache/`

### Rate Limiting

Crawl4AI delay: 1 saniye (ayarlanabilir)

```env
CRAWL4AI_DELAY_MS=1000
```

## 🌍 Uluslararası Kullanım

### Avrupa Örnekleri

```powershell
# Fransa
python main.py --city Paris --country France --limit 20

# İspanya
python main.py --city Madrid --country Spain --limit 15

# İtalya
python main.py --city Rome --country Italy --limit 10

# Portekiz
python main.py --city Lisbon --country Portugal --limit 12
```

### Lokal Site Discovery

LLM sayesinde lokal sitelerden de extraction yapılabilir:

- **Türkiye**: sahibinden.com, hepsiemlak.com, emlakjet.com
- **Almanya**: immobilienscout24.de, immonet.de
- **Fransa**: seloger.com, leboncoin.fr
- **İspanya**: idealista.com, fotocasa.es

## 🔐 Avantajlar

### Regex/CSS Selector'a Göre

❌ **Regex**: Brittle, site değişince bozulur
❌ **CSS Selector**: Site-specific, her site için yeni kod

✅ **LLM**: Anlam çıkarımı, site-agnostic, dil-agnostic

### Örnek

**Regex yaklaşımı:**
```python
# Her site için farklı pattern
if "realtor.com" in url:
    pattern = r'<div class="agent-name">(.*?)</div>'
elif "zillow.com" in url:
    pattern = r'<span class="agent-title">(.*?)</span>'
# 100+ site için 100+ pattern!
```

**LLM yaklaşımı:**
```python
# Tek kod, tüm siteler için
companies = llm_parser.extract_companies(html, query_context)
```

## 📝 Notlar

- LLM çağrıları ~5-10 saniye sürebilir (model boyutuna göre)
- Cache kullanımı önemli (aynı URL'yi tekrar çekme)
- Google rate limiting olabilir (1 saniye delay yeterli)
- Ollama local çalışır, API key gerekmez
- Gemma 2:2b küçük model (~2GB RAM)

## 🎯 Sonraki Adımlar

1. ✅ LLM-based parsing implementasyonu
2. ✅ Multi-language support
3. ✅ Site-agnostic extraction
4. 🔄 Performans testing (farklı ülkeler)
5. 🔄 Cache optimization
6. 🔄 Model fine-tuning (isteğe bağlı)
