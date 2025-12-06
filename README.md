# AI Real-Estate Marketing Intelligence System

A Python-based system for discovering real estate companies, finding their social media profiles, and downloading their video content for analysis.

## Overview

This is the **FIRST LAYER** of an AI Real-Estate Marketing Intelligence system - focused on **data ingestion and orchestration** (NOT multimodal analysis).

### What it does:

1. **Discovers** real estate & construction companies in a target city/country
2. **Finds** their social media profiles (Instagram, TikTok, YouTube)
3. **Extracts** recent video posts from these profiles
4. **Downloads** videos to local storage
5. **Persists** everything in PostgreSQL for future analysis

## Architecture

### Tech Stack

- **Language:** Python 3.11+
- **Database:** PostgreSQL with SQLModel ORM
- **Scraping:** crawl4ai + BeautifulSoup (for companies), stubbed social scrapers
- **Video Download:** yt-dlp
- **Configuration:** Pydantic Settings
- **Logging:** Structlog

### Key Design Patterns

- **Repository Pattern** - Clean data access layer
- **Template Method** - Base agent with common functionality
- **Strategy Pattern** - Pluggable scraper implementations
- **Chain of Responsibility** - Sequential agent pipeline

## Project Structure

```
c:\Users\erdog\Python-2023\Company Discovery Agent\
├── config/              # Settings & logging configuration
├── database/            # SQLModel models, session, repositories
├── agents/              # 4 core agents
├── scrapers/            # Company & social media scrapers (stubbed)
├── services/            # Scoring & video download services
├── utils/               # Retry, validation, text processing
├── schemas/             # Pydantic request/response models
├── data/
│   ├── downloads/       # Downloaded videos (gitignored)
│   └── mock_data/       # Mock JSON for development
├── scripts/             # Database initialization scripts
└── main.py              # Entry point orchestrator
```

## Installation

### Prerequisites

1. **Python 3.11+**
2. **PostgreSQL** (running locally or remote)
3. **yt-dlp** for video downloads

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 3. Initialize database
python scripts/init_db.py
```

### Environment Configuration

Edit `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate_intel

# Features
USE_MOCK_SCRAPERS=true    # Use mock data (set false for real scrapers)
DEBUG=true
LOG_LEVEL=INFO

# Paths
DOWNLOAD_BASE_PATH=./data/downloads

# Agent Parameters
COMPANY_DISCOVERY_DEFAULT_LIMIT=50
VIDEO_FINDER_DAYS_BACK=90
VIDEO_FINDER_MIN_VIEWS=100
```

## Usage

### Run Full Pipeline

Discover companies in Miami, find their social profiles, extract videos, and download them:

```bash
python main.py --city "Miami" --country "USA" --limit 50
```

**Output:**
```
============================================================
PIPELINE RESULTS
============================================================
Companies Discovered:  50
Social Profiles Found: 142
Video Posts Found:     387
Videos Downloaded:     312
============================================================
```

### Run Individual Steps

```bash
# Only discover companies
python main.py --city "Miami" --country "USA" --step discovery

# Other steps (full implementation in progress)
python main.py --city "Miami" --country "USA" --step profiles
python main.py --city "Miami" --country "USA" --step videos
```

## Database Schema

### Tables

**1. companies** - Discovered real estate companies
- id (UUID), name, website_url, city, country
- source, importance_score, is_active
- created_at, updated_at

**2. social_profiles** - Social media profiles for companies
- id (UUID), company_id (FK), platform (instagram/tiktok/youtube)
- profile_url, username, followers_count, posts_count
- engagement_score, content_type, last_scraped_at
- created_at, updated_at

**3. social_posts** - Individual video posts
- id (UUID), social_profile_id (FK), platform, post_type
- post_url, external_post_id, caption_text
- published_at, like_count, comment_count, view_count, saved_count
- created_at, updated_at

**4. video_download_jobs** - Video download tracking
- id (UUID), social_post_id (FK), platform, post_url
- status (pending/downloading/done/error)
- error_message, file_path
- created_at, updated_at

## Agent Pipeline

```
┌─────────────────────────────────────┐
│  AgentOrchestrator (main.py)        │
└──────────────┬──────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ CompanyDiscoveryAgent │
   │ Input: city, country  │
   │ Output: [Company]     │
   └───────┬───────────────┘
           │ for each company
           ▼
   ┌───────────────────────┐
   │  ProfileFinderAgent   │
   │ Input: Company        │
   │ Output: [Profile]     │
   └───────┬───────────────┘
           │ for each profile
           ▼
   ┌───────────────────────┐
   │   VideoFinderAgent    │
   │ Input: SocialProfile  │
   │ Output: [Post]        │
   └───────┬───────────────┘
           │ batch posts
           ▼
   ┌───────────────────────┐
   │ VideoDownloaderAgent  │
   │ Input: [SocialPost]   │
   │ Output: [Job]         │
   └───────────────────────┘
```

## Development Status

### ✅ Completed

- Complete project structure
- Configuration & logging (Pydantic Settings + Structlog)
- Database models (SQLModel with 4 tables)
- Repository pattern for data access
- All 4 agents implemented
- Mock data for Instagram, TikTok, YouTube
- Video download service (yt-dlp wrapper)
- Scoring algorithms (importance, engagement)
- Main orchestrator with CLI

### 🚧 In Progress

- **Social Media Scrapers:** Currently stubbed with mock data
  - Instagram: Will use instaloader or Playwright
  - TikTok: Will use unofficial API or Playwright
  - YouTube: Will use YouTube Data API v3
- **Company Scraper:** Returns mock data, needs crawl4ai implementation

### 📋 Future Enhancements

- Real social media scraper implementation
- Async/await refactor for better performance
- Celery + Redis queue for background jobs
- FastAPI REST API layer
- Testing suite (pytest with 80%+ coverage)
- Alembic migrations setup
- Monitoring & observability (Prometheus, Grafana)

## Key Files

| File | Purpose |
|------|---------|
| [config/settings.py](config/settings.py) | Pydantic Settings (DATABASE_URL, USE_MOCK_SCRAPERS, etc.) |
| [database/models.py](database/models.py) | SQLModel schema (4 tables) |
| [database/repositories.py](database/repositories.py) | Repository pattern (CRUD + deduplication) |
| [agents/base.py](agents/base.py) | Base agent with template method pattern |
| [scrapers/social/base.py](scrapers/social/base.py) | Base social scraper (mock data loader) |
| [main.py](main.py) | Orchestrator + CLI entry point |

## Example Run

```bash
$ python main.py --city "Miami" --country "USA" --limit 10

2024-12-06 10:00:00 [INFO] Starting AI Real-Estate Marketing Intelligence System
2024-12-06 10:00:00 [INFO] CompanyDiscoveryAgent starting
2024-12-06 10:00:02 [INFO] Scraped companies count=10
2024-12-06 10:00:03 [INFO] Company discovery completed total_processed=10 returned=10
2024-12-06 10:00:03 [INFO] ProfileFinderAgent starting company_name="Luxury Homes Miami"
2024-12-06 10:00:04 [INFO] Found instagram profile username=luxuryrealestate_miami
2024-12-06 10:00:05 [INFO] Found tiktok profile username=@miami.realestate.pro
2024-12-06 10:00:06 [INFO] Found youtube profile username=MiamiLuxuryRealEstate
...
```

## Contributing

This is a development project. Key areas for contribution:

1. Implement real social media scrapers
2. Add comprehensive tests
3. Optimize database queries
4. Add error recovery mechanisms
5. Implement rate limiting and proxy rotation

## License

MIT License

## Contact

For questions or issues, please open an issue on GitHub.
