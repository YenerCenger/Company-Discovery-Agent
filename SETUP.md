# 🔧 ViralFlow AI - Kurulum Rehberi

Bu belge, ViralFlow AI platformunun detaylı kurulum adımlarını içerir.

---

## 📋 Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---------|---------|----------|
| **İşletim Sistemi** | Windows 10 / Ubuntu 20.04 / macOS 12 | Windows 11 / Ubuntu 22.04 / macOS 14 |
| **Python** | 3.11 | 3.12 |
| **RAM** | 8 GB | 16+ GB |
| **GPU** | - | NVIDIA RTX 3060+ (CUDA 11.8+) |
| **Disk** | 20 GB | 50+ GB (video storage) |
| **PostgreSQL** | 14 | 15+ |
| **MongoDB** | 5.0 | 6.0+ |

---

## 🚀 Hızlı Kurulum (Windows)

### 1. Yazılımları İndirin ve Kurun

```powershell
# 1. Python 3.12 (Microsoft Store veya python.org)
winget install Python.Python.3.12

# 2. PostgreSQL
winget install PostgreSQL.PostgreSQL

# 3. MongoDB Community Server
winget install MongoDB.Server

# 4. Ollama
# https://ollama.ai/download adresinden indirin

# 5. FFmpeg
winget install FFmpeg
```

### 2. Projeyi Klonlayın

```powershell
git clone https://github.com/YenerCenger/ViralFlow-AI.git
cd ViralFlow-AI
```

### 3. Virtual Environment Oluşturun

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Bağımlılıkları Kurun

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Ollama Model İndirin

```powershell
ollama pull gemma:7b
```

### 6. Veritabanlarını Oluşturun

```powershell
# PostgreSQL (pgAdmin veya psql ile)
createdb viralflow_db

# MongoDB otomatik oluşturulur
```

### 7. .env Dosyasını Yapılandırın

Proje kök dizinine `.env` dosyası oluşturun:

```env
# PostgreSQL
DATABASE_URL=postgresql://postgres:sifreniz@localhost:5432/viralflow_db
DB_ECHO=false

# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=ViralFlowDB

# Instagram
INSTAGRAM_USERNAME=instagram_kullanici_adiniz
INSTAGRAM_PASSWORD=instagram_sifreniz

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:7b
OLLAMA_URL=http://localhost:11434/api/generate
LLM_MODEL=gemma:7b

# Video İşleme
WHISPER_MODEL_SIZE=medium
DOWNLOAD_BASE_PATH=./data/downloads

# Discovery
VIDEO_FINDER_DAYS_BACK=90
VIDEO_FINDER_MIN_VIEWS=100
VIDEO_FINDER_TOP_N=50
VIDEO_SORT_BY=views
VIDEO_DOWNLOAD_PER_COMPANY=5

# Uygulama
DEBUG=false
LOG_LEVEL=INFO
```

### 8. Veritabanı Tablolarını Oluşturun

```powershell
python scripts/init_db.py
```

### 9. Test Edin

```powershell
python run_pipeline.py --city Istanbul --country Turkey --limit 2
```

---

## 🐧 Linux/macOS Kurulumu

### Ubuntu/Debian

```bash
# Sistem güncellemesi
sudo apt update && sudo apt upgrade -y

# Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-dev

# PostgreSQL
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb viralflow_db

# MongoDB
# https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

# FFmpeg
sudo apt install ffmpeg

# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gemma:7b
```

### macOS

```bash
# Homebrew ile
brew install python@3.12 postgresql@15 mongodb-community ffmpeg

# Servisleri başlat
brew services start postgresql@15
brew services start mongodb-community

# Ollama
brew install ollama
ollama serve &
ollama pull gemma:7b
```

---

## 🎮 GPU Kurulumu (CUDA)

### NVIDIA GPU için PyTorch CUDA Kurulumu

```bash
# Önce CPU sürümünü kaldır
pip uninstall torch torchvision torchaudio

# CUDA 11.8 sürümünü kur
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1 için
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### GPU Doğrulama

```python
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"GPU Name: {torch.cuda.get_device_name(0)}")
```

---

## 🔍 Doğrulama Testleri

### 1. PostgreSQL Bağlantısı

```bash
python -c "from database.session import engine; print('PostgreSQL OK')"
```

### 2. MongoDB Bağlantısı

```bash
python -c "from pymongo import MongoClient; c=MongoClient('mongodb://localhost:27017'); print('MongoDB OK')"
```

### 3. Ollama Bağlantısı

```bash
curl http://localhost:11434/api/tags
```

### 4. Tam Pipeline Testi

```bash
python run_pipeline.py --city Istanbul --country Turkey --limit 1
```

---

## 🐛 Sık Karşılaşılan Sorunlar

### ❌ `psycopg2` kurulum hatası

```bash
# Windows
pip install psycopg2-binary

# Linux (derleme için)
sudo apt install libpq-dev python3-dev
pip install psycopg2
```

### ❌ `torch` CUDA hatası

```bash
# CUDA sürümünü kontrol edin
nvidia-smi

# Uygun PyTorch sürümünü kurun
# https://pytorch.org/get-started/locally/
```

### ❌ Instagram rate limit

```bash
# Session'ı temizleyin
python clear_instagram_session.py

# VPN kullanın
# 24-48 saat bekleyin
```

### ❌ Ollama bağlantı hatası

```bash
# Ollama servisini başlatın
ollama serve

# Model yüklü mü kontrol edin
ollama list

# Model indirin
ollama pull gemma:7b
```

### ❌ MongoDB bağlantı hatası

```bash
# Windows
net start MongoDB

# Linux
sudo systemctl start mongod

# macOS
brew services start mongodb-community
```

---

## 📁 Dosya Yapısı (Kurulum Sonrası)

```
ViralFlow-AI/
├── .env                    ← Oluşturulmalı
├── venv/                   ← Virtual environment
├── data/
│   ├── downloads/          ← İndirilen videolar
│   └── crawl_cache/        ← Web cache
├── reports/                ← Oluşturulan raporlar
│   └── YYYY-MM-DD/
├── requirements.txt
├── run_pipeline.py         ← Ana giriş noktası
└── ...
```

---

## ✅ Kurulum Kontrol Listesi

- [ ] Python 3.11+ kurulu
- [ ] PostgreSQL kurulu ve çalışıyor
- [ ] MongoDB kurulu ve çalışıyor
- [ ] Ollama kurulu ve model indirildi
- [ ] FFmpeg kurulu
- [ ] Virtual environment oluşturuldu
- [ ] Bağımlılıklar kuruldu
- [ ] `.env` dosyası yapılandırıldı
- [ ] Veritabanı tabloları oluşturuldu
- [ ] Test pipeline başarılı

---

## 📞 Destek

Sorun yaşarsanız:
1. Bu dokümandaki sorun giderme bölümünü kontrol edin
2. GitHub Issues açın
3. Log dosyalarını inceleyin

---

**Kurulum tamamlandı! 🎉**

```bash
python run_pipeline.py --city Istanbul --country Turkey --limit 5
```



