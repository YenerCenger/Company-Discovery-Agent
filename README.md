# 🎯 ViralFlow AI - Real Estate Marketing Intelligence Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-47A248.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**End-to-end AI-powered video marketing intelligence system for real estate companies.**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-reference)

</div>

---

## 📋 Overview

ViralFlow AI is a comprehensive marketing intelligence platform that automates the discovery, analysis, and strategy generation for real estate video marketing. The system crawls social media, analyzes video content using AI, and generates actionable marketing recommendations.

### What It Does

```
🔍 DISCOVER → 📱 COLLECT → 🎬 ANALYZE → 📊 REPORT → 💡 RECOMMEND
```

1. **Discovers** real estate companies in any target city/country
2. **Finds** their social media profiles (Instagram, TikTok, YouTube)
3. **Downloads** video content with smart filtering
4. **Analyzes** videos using AI (transcription, object detection, OCR)
5. **Generates** marketing reports with LLM-powered recommendations

---

## ✨ Features

### 🔍 Company Discovery
- LLM-powered company extraction from real estate websites
- Multi-country support (USA, Turkey, UK, Germany, UAE, etc.)
- Intelligent deduplication and scoring

### 📱 Social Media Integration
- **Instagram**: Real scraping via Instaloader + DuckDuckGo search
- **TikTok/YouTube**: Ready for implementation
- Engagement scoring and content classification

### 🎬 Video Processing
- **Audio Transcription**: Faster-Whisper (GPU optimized)
- **Object Detection**: YOLOv8 for visual analysis
- **OCR**: EasyOCR for text extraction
- Segment-based analysis with timestamps

### 📊 Report Generation
- **LLM Interpretation**: Pattern recognition from successful videos
- **Strategy Recommendations**: Platform-specific content strategies
- **Viral Formulas**: Hook templates, CTA variants, script templates
- Export to JSON + Markdown

### 🛠️ Technical Features
- ✅ Dual database architecture (PostgreSQL + MongoDB)
- ✅ REST API with FastAPI
- ✅ CLI interface for automation
- ✅ Rate limiting protection
- ✅ Configurable via environment variables
- ✅ Structured logging with Structlog

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ViralFlow AI Platform                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Company    │───▶│   Profile    │───▶│    Video     │              │
│  │  Discovery   │    │   Finder     │    │   Finder     │              │
│  │    Agent     │    │    Agent     │    │    Agent     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌─────────────────────────────────────────────────────┐               │
│  │                   PostgreSQL                         │               │
│  │   companies │ social_profiles │ social_posts │ jobs │               │
│  └─────────────────────────────────────────────────────┘               │
│                              │                                          │
│                              ▼                                          │
│                    ┌──────────────┐                                     │
│                    │    Video     │                                     │
│                    │  Downloader  │                                     │
│                    │    Agent     │                                     │
│                    └──────────────┘                                     │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────┐               │
│  │              Video Processor Agent                   │               │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │               │
│  │  │ Whisper │  │ YOLOv8  │  │ EasyOCR │             │               │
│  │  │ (Audio) │  │ (Visual)│  │  (Text) │             │               │
│  │  └─────────┘  └─────────┘  └─────────┘             │               │
│  └─────────────────────────────────────────────────────┘               │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────┐               │
│  │                    MongoDB                           │               │
│  │              analysis_results collection             │               │
│  └─────────────────────────────────────────────────────┘               │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────┐               │
│  │             Report Analysis Agent                    │               │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │               │
│  │  │ Preprocess  │─▶│   Stats     │─▶│    LLM      │ │               │
│  │  │   Agent     │  │   Agent     │  │ Interpreter │ │               │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │               │
│  │                                            │        │               │
│  │                                            ▼        │               │
│  │                                    ┌─────────────┐ │               │
│  │                                    │    LLM      │ │               │
│  │                                    │ Recommender │ │               │
│  │                                    └─────────────┘ │               │
│  └─────────────────────────────────────────────────────┘               │
│                              │                                          │
│                              ▼                                          │
│                    ┌──────────────┐                                     │
│                    │   Reports    │                                     │
│                    │  (JSON/MD)   │                                     │
│                    └──────────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ |
| **API Framework** | FastAPI |
| **Databases** | PostgreSQL (metadata) + MongoDB (analysis) |
| **ORM** | SQLModel |
| **Web Scraping** | Crawl4AI, BeautifulSoup, Instaloader |
| **Video Download** | yt-dlp |
| **Audio AI** | Faster-Whisper |
| **Vision AI** | YOLOv8 (Ultralytics) |
| **OCR** | EasyOCR |
| **LLM** | Ollama (Gemma, DeepSeek, Qwen) |
| **Logging** | Structlog |

### Project Structure

```
ViralFlow-AI/
├── agents/                      # Core discovery agents
│   ├── company_discovery.py     # LLM-based company extraction
│   ├── profile_finder.py        # Social media profile discovery
│   ├── video_finder.py          # Video post extraction
│   └── video_downloader.py      # Video download orchestration
│
├── modules/
│   ├── video_processor_agent/   # Video analysis module
│   │   ├── services/
│   │   │   ├── audio_service.py     # Whisper transcription
│   │   │   ├── vision_service.py    # YOLO + OCR
│   │   │   └── pipeline_service.py  # Analysis orchestration
│   │   └── core/
│   │       ├── config.py            # Module settings
│   │       └── database.py          # MongoDB connection
│   │
│   └── report_analysis_agent/   # Report generation module
│       ├── agents/
│       │   ├── preprocessing_agent.py   # Data preparation
│       │   ├── stats_agent.py           # Statistical analysis
│       │   ├── interpretation_agent.py  # LLM pattern analysis
│       │   └── recommendation_agent.py  # LLM recommendations
│       └── services/
│           ├── mongodb_service.py       # MongoDB data fetching
│           └── report_builder.py        # JSON/MD generation
│
├── database/                    # PostgreSQL models & repos
│   ├── models.py                # SQLModel definitions
│   ├── repositories.py          # CRUD operations
│   └── session.py               # DB session management
│
├── scrapers/                    # Web scraping modules
│   ├── company_scraper.py       # Real estate site scraper
│   ├── crawl4ai_handler.py      # Crawl4AI wrapper
│   └── social/
│       └── instagram.py         # Instagram scraper
│
├── services/                    # Business logic
│   ├── llm_service.py           # Ollama integration
│   ├── video_download.py        # yt-dlp wrapper
│   └── scoring.py               # Engagement scoring
│
├── reports/                     # Generated reports (gitignored)
│   └── YYYY-MM-DD/
│       ├── {uuid}.json
│       └── {uuid}.md
│
├── data/
│   └── downloads/               # Downloaded videos (gitignored)
│
├── run_pipeline.py              # Main CLI entry point
├── main.py                      # Legacy CLI + API server
├── requirements.txt             # Python dependencies
└── .env                         # Environment configuration
```

---

## 📦 Installation

### Prerequisites

| Requirement | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| PostgreSQL | 15+ | Metadata storage |
| MongoDB | 6.0+ | Analysis results |
| Ollama | Latest | Local LLM inference |
| FFmpeg | Latest | Video processing |

### Step 1: Clone Repository

```bash
git clone https://github.com/YenerCenger/ViralFlow-AI.git
cd ViralFlow-AI
```

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

# If ExecutionPolicy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**For GPU Support (CUDA):**
```bash
# Uninstall CPU PyTorch first
pip uninstall torch torchvision torchaudio

# Install CUDA version (adjust cu118 to your CUDA version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 4: Install Ollama & Models

**Windows:**
1. Download from https://ollama.ai/download
2. Install and start Ollama

**Linux/macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Pull Required Models:**
```bash
# Primary model for report generation
ollama pull gemma:7b

# Alternative models
ollama pull deepseek-r1:8b
ollama pull qwen2.5:7b
```

### Step 5: Setup Databases

**PostgreSQL:**
```bash
# Create database
createdb viralflow_db

# Or via psql
psql -U postgres -c "CREATE DATABASE viralflow_db;"
```

**MongoDB:**
```bash
# MongoDB should be running on localhost:27017
# Database and collection will be created automatically
```

### Step 6: Configure Environment

Create `.env` file in project root:

```env
# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# PostgreSQL
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/viralflow_db
DB_ECHO=false

# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=ViralFlowDB

# =============================================================================
# INSTAGRAM AUTHENTICATION
# =============================================================================
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
# Ollama (Discovery Agent)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:7b
OLLAMA_TIMEOUT=300

# Ollama (Video Processor & Report Analysis)
OLLAMA_URL=http://localhost:11434/api/generate
LLM_MODEL=gemma:7b

# =============================================================================
# VIDEO PROCESSING
# =============================================================================
WHISPER_MODEL_SIZE=medium
DOWNLOAD_BASE_PATH=./data/downloads

# =============================================================================
# DISCOVERY SETTINGS
# =============================================================================
VIDEO_FINDER_DAYS_BACK=90
VIDEO_FINDER_MIN_VIEWS=100
VIDEO_FINDER_TOP_N=50
VIDEO_SORT_BY=views
VIDEO_DOWNLOAD_PER_COMPANY=5
COMPANY_DISCOVERY_DEFAULT_LIMIT=50

# =============================================================================
# APPLICATION
# =============================================================================
DEBUG=false
LOG_LEVEL=INFO
```

### Step 7: Initialize Database

```bash
python scripts/init_db.py
```

---

## 🚀 Usage

### Full Pipeline (Recommended)

Run the complete pipeline from discovery to report generation:

```bash
python run_pipeline.py --city "Istanbul" --country "Turkey" --limit 5
```

**Output:**
```
======================================================================
                    VIRALFLOW AI PIPELINE
======================================================================

[1/7] COMPANY DISCOVERY
----------------------------------------------------------------------
  → Searching for real estate companies in Istanbul, Turkey...
  ✓ 5 companies discovered

[2/7] PROFILE FINDER
----------------------------------------------------------------------
  → Finding social media profiles...
  ✓ 5 Instagram profiles found

[3/7] VIDEO FINDER
----------------------------------------------------------------------
  → Extracting video posts...
  ✓ 47 videos found

[4/7] VIDEO DOWNLOADER
----------------------------------------------------------------------
  → Downloading top videos...
  ✓ 25/25 videos downloaded

[5/7] VIDEO ANALYSIS
----------------------------------------------------------------------
  → Processing videos with AI...
  ✓ 25 videos analyzed (MongoDB)

[6/7] REPORT ANALYSIS
----------------------------------------------------------------------
  → Generating marketing report...
  ✓ Report created: reports/2025-12-07/abc123.md

======================================================================
                         PIPELINE RESULTS
======================================================================
  Companies Discovered:     5
  Social Profiles Found:    5
  Videos Found:             47
  Videos Downloaded:        25
  Videos Analyzed:          25
  Report ID:                abc123-def456-...
  Report File:              reports/2025-12-07/abc123.md
======================================================================
```

### CLI Options

```bash
python run_pipeline.py --help

Options:
  --city TEXT           Target city (required with --country)
  --country TEXT        Target country (required with --city)
  --limit INTEGER       Max companies to discover (default: 5)
  --url TEXT            Direct video URL to process
  --company TEXT        Company name for direct URL
  --report              Generate report from existing MongoDB data
  --status              Show MongoDB analysis results
  --analyze-pending     Analyze pending videos
```

### Usage Examples

```bash
# Full pipeline
python run_pipeline.py --city "Miami" --country "USA" --limit 10

# Process a single video URL
python run_pipeline.py --url "https://www.instagram.com/reel/ABC123/" --company "Test Company"

# Generate report from existing data
python run_pipeline.py --report
python run_pipeline.py --report --company "Specific Company"

# Check analysis status
python run_pipeline.py --status

# Analyze pending videos
python run_pipeline.py --analyze-pending
```

### API Server Mode

```bash
python main.py --mode api
```

Server runs on `http://localhost:8000`

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📖 API Reference

### Discovery Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/discover` | Start discovery pipeline |
| `GET` | `/api/companies` | List discovered companies |
| `GET` | `/api/profiles` | List social profiles |
| `GET` | `/api/videos` | List video posts |
| `GET` | `/api/status` | System status |

### Video Processor Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/process-job/{job_id}` | Process a download job |
| `GET` | `/api/v1/analysis/{job_id}` | Get analysis result |
| `GET` | `/api/v1/pending-jobs` | List pending jobs |

### Report Analysis Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/mongodb/videos` | Get analyzed videos from MongoDB |
| `POST` | `/analyze/mongodb` | Generate report from MongoDB |
| `GET` | `/mongodb/stats` | MongoDB statistics |

---

## 📊 Database Schema

### PostgreSQL Tables

```sql
-- companies: Discovered real estate companies
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    website_url VARCHAR,
    city VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    source VARCHAR,
    importance_score FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- social_profiles: Social media profiles
CREATE TABLE social_profiles (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    platform VARCHAR NOT NULL,
    profile_url VARCHAR NOT NULL,
    username VARCHAR NOT NULL,
    followers_count INTEGER,
    engagement_score FLOAT,
    content_type VARCHAR,
    created_at TIMESTAMP
);

-- social_posts: Video posts
CREATE TABLE social_posts (
    id UUID PRIMARY KEY,
    social_profile_id UUID REFERENCES social_profiles(id),
    platform VARCHAR NOT NULL,
    post_type VARCHAR,
    post_url VARCHAR NOT NULL,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    created_at TIMESTAMP
);

-- video_download_jobs: Download tracking
CREATE TABLE video_download_jobs (
    id UUID PRIMARY KEY,
    social_post_id UUID REFERENCES social_posts(id),
    status VARCHAR DEFAULT 'pending',
    file_path VARCHAR,
    error_message TEXT,
    created_at TIMESTAMP
);
```

### MongoDB Collections

```javascript
// analysis_results: Video analysis data
{
    _id: ObjectId,
    postgresql_job_id: String,
    postgresql_company_id: String,
    company_name: String,
    video_filename: String,
    video_url: String,
    status: String,  // "completed" | "failed"
    processed_at: DateTime,
    metadata: {
        platform: String,
        view_count: Number,
        like_count: Number,
        comment_count: Number
    },
    segments: [{
        start_time: Number,
        end_time: Number,
        transcript: String,
        visual_objects: [String],
        ocr_text: [String],
        sentiment: String,
        key_entities: [String]
    }],
    summary: String,
    all_objects: [String],
    all_ocr_text: [String],
    dominant_emotion: String
}
```

---

## 📄 Report Output

Reports are saved to `reports/YYYY-MM-DD/` directory in both JSON and Markdown formats.

### Sample Report Structure

```markdown
# Video Analysis Report

**Company:** Avcılar İnşaat
**Generated:** 2025-12-07 11:44:24

## Executive Summary
- Total Videos Analyzed: 5
- Average Viral Score: 0.25
- Top Viral Score: 0.62

## Marketing Recommendations

### 🎭 Tone Recommendations
**Recommended Tone:** Sophisticated Aspiration
**Examples:** "Invest in Excellence", "Experience the Extraordinary"

### 📹 Camera Angle Recommendations
- Wide shots showcasing property scale
- Close-ups highlighting luxury features

### 🎵 Audio & Music
**Style:** Uplifting orchestral or ambient electronic
**Tempo:** Medium - creates calm sophistication

## Viral Script Templates

### The Vista Reveal
**Structure:** Quick property reveal + benefit statement
**Duration:** 25-30 seconds
**Example:** "Introducing 'The Sapphire Residences'..."

## Platform Strategy

### TikTok
- Format: Vertical
- Length: 20-30 seconds
- Tone: Energetic, Aspirational

### Instagram
- Format: Vertical/Square
- Length: 15-30 seconds
- Type: Reels, Stories
```

---

## 🐛 Troubleshooting

### Instagram Rate Limiting

```bash
# Clear session and retry
python clear_instagram_session.py

# Use VPN if IP is blocked
# Wait 24-48 hours for rate limit reset
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
ollama serve

# Verify models
ollama list

# Test API
curl http://localhost:11434/api/tags
```

### Database Connection Issues

```bash
# PostgreSQL
psql -U postgres -c "SELECT 1;"

# MongoDB
mongosh --eval "db.runCommand({ping:1})"
```

### Video Processing Errors

```bash
# Check FFmpeg installation
ffmpeg -version

# Check video file integrity
ffprobe /path/to/video.mp4
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Instaloader](https://github.com/instaloader/instaloader) - Instagram scraping
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloading
- [Crawl4AI](https://github.com/unclecode/crawl4ai) - Web scraping
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Ultralytics](https://github.com/ultralytics/ultralytics) - YOLOv8
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Audio transcription
- [FastAPI](https://fastapi.tiangolo.com/) - API framework

---

<div align="center">

**Built with ❤️ for Real Estate Marketing Intelligence**

[⬆ Back to Top](#-viralflow-ai---real-estate-marketing-intelligence-platform)

</div>
