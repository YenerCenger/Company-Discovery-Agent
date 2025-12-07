"""
Tam Pipeline - Ülke/Şehir Seçiminden MongoDB'ye

Bu script tüm sistemi baştan sona çalıştırır:

Akış:
    1. Ülke/Şehir seçimi
    2. Google ile şirket arama
    3. LLM ile şirket analizi
    4. Sosyal medya profilleri bulma
    5. Video postları bulma
    6. Video indirme (yt-dlp)
    7. Video analizi (Whisper + YOLO + OCR)
    8. MongoDB'ye sonuç kaydetme

Kullanım:
    python run_pipeline.py --city Istanbul --country Turkey --limit 5
    python run_pipeline.py --city Miami --country USA --limit 10
    python run_pipeline.py --status                    # Analiz sonuçlarını göster
    python run_pipeline.py --analyze-pending           # İndirilen ama analiz edilmemiş videoları analiz et
"""
import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlmodel import select
from database.session import get_db_session
from database.models import Company, SocialProfile, SocialPost, VideoDownloadJob
from agents.company_discovery import CompanyDiscoveryAgent
from agents.profile_finder import ProfileFinderAgent
from agents.video_finder import VideoFinderAgent
from agents.video_downloader import VideoDownloaderAgent
from schemas.requests import CompanyDiscoveryInput
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


# ==================== VIDEO ANALYSIS ====================

async def analyze_single_video(job: VideoDownloadJob, company_name: str, company_id: UUID) -> Optional[dict]:
    """
    Tek bir video analiz et ve MongoDB'ye kaydet.
    
    Args:
        job: VideoDownloadJob
        company_name: Şirket adı
        company_id: Şirket UUID
    
    Returns:
        Analiz sonucu dict veya None
    """
    from modules.video_processor_agent.core.database import db, get_analysis_collection
    from modules.video_processor_agent.services.pipeline_service import pipeline_service
    
    if not job.file_path or not Path(job.file_path).exists():
        print(f"    ✗ Dosya bulunamadı: {job.file_path}")
        return None
    
    # Connect to MongoDB
    await db.connect()
    
    try:
        collection = get_analysis_collection()
        
        # Check if already analyzed
        existing = await collection.find_one({
            "postgresql_job_id": str(job.id)
        })
        
        if existing:
            print(f"    ⚠ Zaten analiz edilmiş: {Path(job.file_path).name}")
            return existing
        
        # Run analysis
        print(f"    → Analiz: {Path(job.file_path).name}")
        
        # Convert UUID to MongoDB ObjectId-like string
        company_id_str = str(company_id).replace("-", "")[:24]
        
        result = pipeline_service.process_video(
            video_path=job.file_path,
            company_name=company_name,
            company_id=company_id_str,
            video_url=job.post_url,
        )
        
        # Update metadata
        result.metadata.platform = job.platform
        result.metadata.video_url = job.post_url
        
        # Get post stats if available
        with get_db_session() as session:
            post = session.get(SocialPost, job.social_post_id)
            if post:
                result.metadata.view_count = post.view_count
                result.metadata.like_count = post.like_count
                result.metadata.comment_count = post.comment_count
        
        # Save to MongoDB
        result_dict = result.model_dump(by_alias=True, exclude={'id'})
        result_dict["postgresql_job_id"] = str(job.id)
        result_dict["postgresql_company_id"] = str(company_id)
        
        insert_result = await collection.insert_one(result_dict)
        
        print(f"    ✓ Tamamlandı! MongoDB ID: {insert_result.inserted_id}")
        
        return result_dict
        
    except Exception as e:
        print(f"    ✗ Analiz hatası: {e}")
        return None
    finally:
        await db.close()


async def analyze_all_pending_videos():
    """İndirilen ama analiz edilmemiş tüm videoları analiz et."""
    from modules.video_processor_agent.core.database import db, get_analysis_collection
    
    print("\n" + "=" * 70)
    print("BEKLEYEN VİDEOLARI ANALİZ ET")
    print("=" * 70)
    
    # Get all completed download jobs
    with get_db_session() as session:
        statement = select(VideoDownloadJob).where(
            VideoDownloadJob.status == "done",
            VideoDownloadJob.file_path.isnot(None)
        )
        jobs = session.exec(statement).all()
        
        if not jobs:
            print("\n⚠ Analiz edilecek video yok.")
            return
        
        print(f"\n✓ {len(jobs)} indirilen video bulundu")
        
        # Connect to MongoDB to check which are already analyzed
        await db.connect()
        collection = get_analysis_collection()
        
        pending_jobs = []
        for job in jobs:
            existing = await collection.find_one({
                "postgresql_job_id": str(job.id)
            })
            if not existing:
                pending_jobs.append(job)
        
        await db.close()
        
        if not pending_jobs:
            print("⚠ Tüm videolar zaten analiz edilmiş.")
            return
        
        print(f"→ {len(pending_jobs)} video analiz edilecek\n")
        
        # Analyze each pending video
        analyzed = 0
        failed = 0
        
        for i, job in enumerate(pending_jobs, 1):
            # Get company info
            post = session.get(SocialPost, job.social_post_id)
            if not post:
                continue
            
            profile = session.get(SocialProfile, post.social_profile_id)
            if not profile:
                continue
            
            company = session.get(Company, profile.company_id)
            if not company:
                continue
            
            print(f"\n[{i}/{len(pending_jobs)}] {company.name}")
            
            result = await analyze_single_video(job, company.name, company.id)
            
            if result:
                analyzed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 70)
        print(f"Analiz Tamamlandı: {analyzed} başarılı, {failed} başarısız")
        print("=" * 70)


async def show_analysis_results():
    """MongoDB'deki tüm analiz sonuçlarını göster."""
    from modules.video_processor_agent.core.database import db, get_analysis_collection
    
    print("\n" + "=" * 70)
    print("MONGODB ANALİZ SONUÇLARI")
    print("=" * 70)
    
    await db.connect()
    
    try:
        collection = get_analysis_collection()
        cursor = collection.find({}).sort("processed_at", -1).limit(30)
        
        results = []
        async for doc in cursor:
            results.append(doc)
        
        if not results:
            print("\n⚠ Henüz analiz sonucu yok.")
            return
        
        print(f"\n✓ Toplam {len(results)} analiz sonucu\n")
        
        for i, result in enumerate(results, 1):
            status_icon = "✓" if result.get('status') == 'completed' else "✗"
            segments = len(result.get('segments', []))
            objects = len(result.get('all_objects', []))
            
            print(f"{i}. {status_icon} {result.get('video_filename', 'Unknown')}")
            print(f"   Şirket: {result.get('company_name', 'Unknown')}")
            print(f"   Status: {result.get('status', 'Unknown')}")
            print(f"   Segments: {segments}, Objects: {objects}")
            
            # Show first transcript if available
            segments_data = result.get('segments', [])
            if segments_data and segments_data[0].get('transcript'):
                transcript = segments_data[0]['transcript'][:80]
                print(f"   Transcript: {transcript}...")
            
            print()
        
    finally:
        await db.close()


# ==================== MAIN PIPELINE ====================

class FullPipeline:
    """
    Tam pipeline - Ülke/Şehir seçiminden MongoDB'ye
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.discovery_agent = CompanyDiscoveryAgent(db_session, logger)
        self.profile_agent = ProfileFinderAgent(db_session, logger)
        self.video_finder_agent = VideoFinderAgent(db_session, logger)
        self.downloader_agent = VideoDownloaderAgent(db_session, logger)
    
    def run(self, city: str, country: str, limit: int = 5) -> dict:
        """
        Tam pipeline'ı çalıştır.
        
        Args:
            city: Şehir adı
            country: Ülke adı
            limit: Maksimum şirket sayısı
        
        Returns:
            İstatistikler
        """
        print("\n" + "=" * 70)
        print("TAM PIPELINE BAŞLATILIYOR")
        print("=" * 70)
        print(f"\nŞehir: {city}")
        print(f"Ülke: {country}")
        print(f"Limit: {limit} şirket")
        print(f"Video/Şirket: {settings.VIDEO_DOWNLOAD_PER_COMPANY}")
        
        results = {
            'companies': 0,
            'profiles': 0,
            'videos_found': 0,
            'videos_downloaded': 0,
            'videos_analyzed': 0
        }
        
        # ========================================
        # STEP 1: COMPANY DISCOVERY
        # ========================================
        print("\n" + "-" * 70)
        print("[1/6] ŞİRKET KEŞFİ (Google + LLM)")
        print("-" * 70)
        
        discovery_input = CompanyDiscoveryInput(
            city=city,
            country=country,
            limit=limit
        )
        
        try:
            companies = self.discovery_agent.execute(discovery_input)
        except Exception as e:
            print(f"  ✗ Şirket keşfi hatası: {e}")
            return results
        
        if not companies:
            print("  ⚠ Hiç şirket bulunamadı.")
            return results
        
        results['companies'] = len(companies)
        print(f"  ✓ {len(companies)} şirket bulundu:")
        for c in companies[:5]:
            print(f"    - {c.name} (skor: {c.importance_score:.2f})")
        if len(companies) > 5:
            print(f"    ... ve {len(companies) - 5} tane daha")
        
        # ========================================
        # STEP 2: PROFILE FINDER
        # ========================================
        print("\n" + "-" * 70)
        print("[2/6] SOSYAL MEDYA PROFİLLERİ")
        print("-" * 70)
        
        all_profiles = []
        for company in companies:
            print(f"  → {company.name}...", end=" ")
            try:
                profiles = self.profile_agent.execute(company)
                all_profiles.extend(profiles)
                if profiles:
                    print(f"✓ {len(profiles)} profil")
                else:
                    print("⚠ profil yok")
            except Exception as e:
                print(f"✗ hata: {e}")
        
        if not all_profiles:
            print("  ⚠ Hiç sosyal medya profili bulunamadı.")
            return results
        
        results['profiles'] = len(all_profiles)
        print(f"\n  ✓ Toplam {len(all_profiles)} profil bulundu")
        
        # ========================================
        # STEP 3: VIDEO FINDER
        # ========================================
        print("\n" + "-" * 70)
        print("[3/6] VİDEO POSTLARI BULMA")
        print("-" * 70)
        
        all_posts = []
        for profile in all_profiles:
            print(f"  → @{profile.username} ({profile.platform})...", end=" ")
            try:
                posts = self.video_finder_agent.execute(profile)
                all_posts.extend(posts)
                if posts:
                    print(f"✓ {len(posts)} video")
                else:
                    print("⚠ video yok")
            except Exception as e:
                print(f"✗ hata: {e}")
        
        if not all_posts:
            print("  ⚠ Hiç video bulunamadı.")
            return results
        
        results['videos_found'] = len(all_posts)
        print(f"\n  ✓ Toplam {len(all_posts)} video bulundu")
        
        # ========================================
        # STEP 4: VIDEO DOWNLOAD
        # ========================================
        print("\n" + "-" * 70)
        print("[4/6] VİDEO İNDİRME")
        print("-" * 70)
        
        # Group posts by company and limit
        posts_by_company = {}
        for post in all_posts:
            profile = next((p for p in all_profiles if p.id == post.social_profile_id), None)
            if profile:
                company_id = profile.company_id
                if company_id not in posts_by_company:
                    posts_by_company[company_id] = []
                posts_by_company[company_id].append(post)
        
        # Limit posts per company
        posts_to_download = []
        for company_id, posts in posts_by_company.items():
            limited = posts[:settings.VIDEO_DOWNLOAD_PER_COMPANY]
            posts_to_download.extend(limited)
        
        print(f"  → {len(posts_to_download)} video indirilecek ({settings.VIDEO_DOWNLOAD_PER_COMPANY}/şirket)")
        
        try:
            download_jobs = self.downloader_agent.execute(posts_to_download)
        except Exception as e:
            print(f"  ✗ İndirme hatası: {e}")
            download_jobs = []
        
        downloaded_count = sum(1 for j in download_jobs if j.status == "done")
        results['videos_downloaded'] = downloaded_count
        
        print(f"\n  ✓ {downloaded_count}/{len(posts_to_download)} video indirildi")
        
        # Commit to save download jobs
        self.db.commit()
        
        return results


def run_discovery_pipeline(city: str, country: str, limit: int) -> dict:
    """
    Discovery pipeline'ını SYNC olarak çalıştır.
    (Crawl4AI asyncio.run() kullandığı için bu kısım sync olmalı)
    """
    with get_db_session() as session:
        pipeline = FullPipeline(session)
        results = pipeline.run(city, country, limit)
        session.commit()
    
    return results


async def run_video_analysis(results: dict, company_name: str = None) -> dict:
    """İndirilen videoları analiz et."""
    
    if results['videos_downloaded'] == 0:
        print("\n⚠ İndirilmiş video yok, analiz atlanıyor.")
        return results
    
    # ========================================
    # STEP 5: VIDEO ANALYSIS
    # ========================================
    print("\n" + "-" * 70)
    print("[5/7] VİDEO ANALİZİ (Whisper + YOLO + OCR)")
    print("-" * 70)
    
    # Get all newly downloaded jobs for this run
    with get_db_session() as session:
        statement = select(VideoDownloadJob).where(
            VideoDownloadJob.status == "done",
            VideoDownloadJob.file_path.isnot(None)
        ).order_by(VideoDownloadJob.created_at.desc()).limit(results['videos_downloaded'] + 5)
        
        jobs = session.exec(statement).all()
        
        analyzed = 0
        analyzed_company_name = company_name
        
        for job in jobs:
            # Get company info
            post = session.get(SocialPost, job.social_post_id)
            if not post:
                continue
            
            profile = session.get(SocialProfile, post.social_profile_id)
            if not profile:
                continue
            
            company = session.get(Company, profile.company_id)
            if not company:
                continue
            
            if not analyzed_company_name:
                analyzed_company_name = company.name
            
            result = await analyze_single_video(job, company.name, company.id)
            
            if result:
                analyzed += 1
        
        results['videos_analyzed'] = analyzed
        results['company_name'] = analyzed_company_name
    
    return results


async def run_report_analysis(results: dict) -> dict:
    """MongoDB'deki verilerle rapor oluştur."""
    
    if results.get('videos_analyzed', 0) == 0:
        print("\n⚠ Analiz edilmiş video yok, rapor oluşturma atlanıyor.")
        return results
    
    # ========================================
    # STEP 6: REPORT ANALYSIS
    # ========================================
    print("\n" + "-" * 70)
    print("[6/7] RAPOR ANALİZİ (LLM Yorumlama + Öneriler)")
    print("-" * 70)
    
    try:
        from modules.report_analysis_agent.services.mongodb_service import get_mongodb_service
        from modules.report_analysis_agent.agents.preprocessing_agent import preprocess_videos, convert_video_data_to_input
        from modules.report_analysis_agent.agents.stats_agent import compute_statistics
        from modules.report_analysis_agent.agents.interpretation_agent import llm_interpretation
        from modules.report_analysis_agent.agents.recommendation_agent import llm_recommendation
        from modules.report_analysis_agent.services.report_builder import build_report, save_report
        from modules.report_analysis_agent.models.video_model import Company as ReportCompany, Profile as ReportProfile
        
        # MongoDB'den veri çek
        print("  → MongoDB'den veriler çekiliyor...")
        mongodb_service = get_mongodb_service()
        
        company_name = results.get('company_name')
        api_response = await mongodb_service.get_api_response(
            company_name=company_name,
            limit=100,
            include_failed=False
        )
        
        if not api_response.data:
            print("  ⚠ MongoDB'de analiz verisi bulunamadı")
            return results
        
        print(f"  ✓ {len(api_response.data)} video verisi çekildi")
        
        # VideoData'ları VideoInput'a dönüştür
        print("  → Veriler işleniyor...")
        video_inputs = []
        for video_data in api_response.data:
            if video_data.status != "completed":
                continue
            try:
                video_input = convert_video_data_to_input(video_data)
                video_inputs.append(video_input)
            except Exception as e:
                print(f"    ⚠ Dönüştürme hatası: {e}")
                continue
        
        if not video_inputs:
            print("  ⚠ Geçerli video verisi yok")
            return results
        
        # Preprocessing
        print("  → Preprocessing...")
        preprocessed_videos = preprocess_videos(video_inputs)
        
        if not preprocessed_videos:
            print("  ⚠ Preprocessing sonrası video kalmadı")
            return results
        
        # İstatistik hesapla
        print("  → İstatistikler hesaplanıyor...")
        stats_summary = compute_statistics(preprocessed_videos)
        
        # Company ve Profile oluştur
        first_video = api_response.data[0]
        report_company = ReportCompany(
            id=first_video.company_id,
            name=first_video.company_name,
            official_website=None,
            hq_city=None,
            hq_country=None,
            rank_score=None
        )
        
        profiles = [ReportProfile(
            id=f"profile_{first_video.metadata.platform}",
            company_id=first_video.company_id,
            platform=first_video.metadata.platform,
            profile_url=None,
            followers=0,
            post_count=len(api_response.data),
            engagement_score=0.0
        )]
        
        # LLM Yorumlama
        print("  → LLM yorumlama yapılıyor...")
        interpretation_output = llm_interpretation(stats_summary, preprocessed_videos)
        
        # LLM Öneriler
        print("  → LLM öneriler oluşturuluyor...")
        recommendations = llm_recommendation(
            interpretation_output,
            report_company,
            profiles
        )
        
        # Rapor oluştur
        print("  → Rapor oluşturuluyor...")
        preprocessing_summary = {
            "input_count": len(video_inputs),
            "output_count": len(preprocessed_videos),
            "dropped_count": len(video_inputs) - len(preprocessed_videos)
        }
        
        json_report, md_report = build_report(
            preprocessing_summary,
            stats_summary,
            interpretation_output,
            recommendations,
            report_company.name
        )
        
        file_paths = save_report(json_report, md_report)
        
        results['report_id'] = file_paths["report_id"]
        results['report_json'] = file_paths["json_path"]
        results['report_md'] = file_paths["md_path"]
        
        print(f"  ✓ Rapor oluşturuldu: {file_paths['report_id']}")
        
    except Exception as e:
        print(f"  ✗ Rapor oluşturma hatası: {e}")
        import traceback
        traceback.print_exc()
    
    return results


async def run_full_analysis_pipeline(results: dict, company_name: str = None) -> dict:
    """Video analizi + Rapor oluşturma."""
    
    # Video analizi
    results = await run_video_analysis(results, company_name)
    
    # Rapor oluşturma
    results = await run_report_analysis(results)
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 70)
    print("[7/7] SONUÇ ÖZETİ")
    print("=" * 70)
    print(f"""
  Şirketler Keşfedildi:    {results['companies']}
  Sosyal Profiller:        {results['profiles']}
  Videolar Bulundu:        {results['videos_found']}
  Videolar İndirildi:      {results['videos_downloaded']}
  Videolar Analiz Edildi:  {results.get('videos_analyzed', 0)}
  Rapor ID:                {results.get('report_id', 'N/A')}
""")
    
    if results.get('report_md'):
        print(f"  Rapor Dosyası:           {results['report_md']}")
    
    print("=" * 70)
    
    return results


def run_full_pipeline(city: str, country: str, limit: int):
    """
    Tam pipeline - önce discovery (sync), sonra analiz + rapor (async).
    """
    # Step 1-4: Discovery pipeline (SYNC - Crawl4AI asyncio.run() kullanıyor)
    results = run_discovery_pipeline(city, country, limit)
    
    # Step 5-7: Video analysis + Report (ASYNC)
    if results['videos_downloaded'] > 0:
        asyncio.run(run_full_analysis_pipeline(results))
    else:
        print("\n⚠ İndirilmiş video yok, analiz atlanıyor.")
    
    return results


# ==================== DIRECT URL PROCESSING ====================

import re
from uuid import uuid4

def detect_platform(url: str) -> tuple[str, str, str]:
    """URL'den platform, username ve post ID algıla."""
    url_lower = url.lower().strip()
    
    if "instagram.com" in url_lower:
        match = re.search(r'instagram\.com/(?:reel|p)/([^/?]+)', url_lower)
        post_id = match.group(1) if match else f"ig_{uuid4().hex[:8]}"
        return "instagram", "instagram_user", post_id
    elif "tiktok.com" in url_lower:
        match = re.search(r'tiktok\.com/@([^/]+)/video/(\d+)', url_lower)
        if match:
            return "tiktok", match.group(1), match.group(2)
        return "tiktok", "tiktok_user", f"tt_{uuid4().hex[:8]}"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        match = re.search(r'(?:shorts/|watch\?v=|youtu\.be/)([^/?&]+)', url_lower)
        post_id = match.group(1) if match else f"yt_{uuid4().hex[:8]}"
        return "youtube", "youtube_channel", post_id
    else:
        return "unknown", "unknown_user", f"vid_{uuid4().hex[:8]}"


async def process_direct_url(url: str, company_name: str = "Direct URL Company"):
    """
    Doğrudan URL ile video indir ve analiz et.
    Instagram API rate limit'e takıldığında kullanılır.
    """
    from services.video_download import VideoDownloadService
    from modules.video_processor_agent.core.database import db, get_analysis_collection
    from modules.video_processor_agent.services.pipeline_service import pipeline_service
    
    print("\n" + "=" * 70)
    print("DOĞRUDAN URL İŞLEME")
    print("=" * 70)
    print(f"\nURL: {url}")
    
    # 1. Platform algıla
    print("\n[1/4] Platform algılanıyor...")
    platform, username, post_id = detect_platform(url)
    print(f"  Platform: {platform}")
    print(f"  Post ID: {post_id}")
    
    # 2. PostgreSQL'e kaydet
    print("\n[2/4] Veritabanına kaydediliyor...")
    
    with get_db_session() as session:
        # Company oluştur veya getir
        statement = select(Company).where(Company.name == company_name)
        company = session.exec(statement).first()
        
        if not company:
            company = Company(
                name=company_name,
                website_url=f"https://{platform}.com",
                city="Unknown",
                country="Unknown",
                source="direct_url",
                importance_score=1.0,
                is_active=True,
            )
            session.add(company)
            session.flush()
            session.refresh(company)
            print(f"  ✓ Company oluşturuldu: {company.name}")
        
        # Profile oluştur veya getir
        profile_statement = select(SocialProfile).where(
            SocialProfile.company_id == company.id,
            SocialProfile.platform == platform
        )
        profile = session.exec(profile_statement).first()
        
        if not profile:
            profile = SocialProfile(
                company_id=company.id,
                platform=platform,
                profile_url=f"https://{platform}.com/{username}",
                username=username,
                followers_count=0,
                posts_count=0,
                is_active=True,
            )
            session.add(profile)
            session.flush()
            session.refresh(profile)
            print(f"  ✓ Profile oluşturuldu: {platform}/{username}")
        
        # Post var mı kontrol et
        post_statement = select(SocialPost).where(
            SocialPost.social_profile_id == profile.id,
            SocialPost.external_post_id == post_id
        )
        existing_post = session.exec(post_statement).first()
        
        if existing_post:
            # Job'u kontrol et
            job_statement = select(VideoDownloadJob).where(
                VideoDownloadJob.social_post_id == existing_post.id
            )
            existing_job = session.exec(job_statement).first()
            
            if existing_job and existing_job.status == "done" and existing_job.file_path:
                print(f"  ⚠ Bu video zaten indirilmiş: {existing_job.file_path}")
                job = existing_job
                post = existing_post
            else:
                post = existing_post
                job = existing_job
        else:
            # Yeni post oluştur
            from datetime import datetime, timezone
            post = SocialPost(
                social_profile_id=profile.id,
                platform=platform,
                post_type="reel" if platform == "instagram" else "video",
                post_url=url,
                external_post_id=post_id,
                caption_text=f"Direct URL - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                published_at=datetime.now(timezone.utc),
                view_count=0,
                like_count=0,
                comment_count=0,
            )
            session.add(post)
            session.flush()
            session.refresh(post)
            
            # Yeni job oluştur
            job = VideoDownloadJob(
                social_post_id=post.id,
                platform=platform,
                post_url=url,
                status="pending",
            )
            session.add(job)
            session.flush()
            session.refresh(job)
            print(f"  ✓ Post ve Job oluşturuldu")
        
        company_id = company.id
        job_id = job.id
        file_path = job.file_path
        
        session.commit()
    
    # 3. Video indir (eğer indirilmemişse)
    if not file_path or not Path(file_path).exists():
        print("\n[3/4] Video indiriliyor...")
        
        download_service = VideoDownloadService()
        result = download_service.download(
            post_url=url,
            platform=platform,
            post_id=post_id
        )
        
        if result and result.get("status") == "success":
            file_path = result.get("file_path")
            print(f"  ✓ Video indirildi: {file_path}")
            
            # Job güncelle
            with get_db_session() as session:
                job = session.get(VideoDownloadJob, job_id)
                job.status = "done"
                job.file_path = file_path
                job.updated_at = datetime.now(timezone.utc)
                session.add(job)
                session.commit()
        else:
            error = result.get("error", "Unknown error") if result else "Download failed"
            print(f"  ✗ İndirme hatası: {error}")
            return
    else:
        print(f"\n[3/4] Video zaten mevcut: {file_path}")
    
    # 4. Analiz et
    print("\n[4/4] Video analiz ediliyor...")
    
    await db.connect()
    
    try:
        collection = get_analysis_collection()
        
        # Zaten analiz edilmiş mi?
        existing = await collection.find_one({
            "postgresql_job_id": str(job_id)
        })
        
        if existing:
            print(f"  ⚠ Bu video zaten analiz edilmiş")
            print(f"  MongoDB ID: {existing.get('_id')}")
            print(f"  Status: {existing.get('status')}")
            print(f"  Segments: {len(existing.get('segments', []))}")
            return
        
        # Analiz yap
        print(f"  → Analiz başlatılıyor...")
        
        company_id_str = str(company_id).replace("-", "")[:24]
        
        result = pipeline_service.process_video(
            video_path=file_path,
            company_name=company_name,
            company_id=company_id_str,
            video_url=url,
        )
        
        # Metadata güncelle
        result.metadata.platform = platform
        result.metadata.video_url = url
        
        # MongoDB'ye kaydet
        result_dict = result.model_dump(by_alias=True, exclude={'id'})
        result_dict["postgresql_job_id"] = str(job_id)
        result_dict["postgresql_company_id"] = str(company_id)
        
        insert_result = await collection.insert_one(result_dict)
        
        # Sonuç özeti
        print("\n" + "=" * 70)
        print("SONUÇ")
        print("=" * 70)
        print(f"  Status: {result.status}")
        print(f"  MongoDB ID: {insert_result.inserted_id}")
        print(f"  Segments: {len(result.segments)}")
        print(f"  Objects: {len(result.all_objects)}")
        
        if result.all_objects:
            print(f"  Detected: {', '.join(result.all_objects[:10])}")
        
        if result.segments and result.segments[0].transcript:
            transcript = result.segments[0].transcript[:100]
            print(f"  Transcript: {transcript}...")
        
        print("\n✓ İşlem tamamlandı!")
        
    except Exception as e:
        print(f"  ✗ Analiz hatası: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


# ==================== CLI ====================

async def generate_report_only(company_name: str = None):
    """Mevcut MongoDB verilerinden rapor oluştur."""
    results = {
        'companies': 0,
        'profiles': 0,
        'videos_found': 0,
        'videos_downloaded': 0,
        'videos_analyzed': 1,  # Rapor için en az 1 analiz gerekli
        'company_name': company_name
    }
    
    await run_report_analysis(results)


def main():
    parser = argparse.ArgumentParser(
        description="Tam Pipeline - Ülke/Şehir Seçiminden MongoDB'ye + Rapor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Tam pipeline (keşif → indirme → analiz → rapor)
  python run_pipeline.py --city Istanbul --country Turkey --limit 5
  
  # Doğrudan URL ile
  python run_pipeline.py --url "https://www.instagram.com/reel/ABC123/"
  
  # MongoDB'den rapor oluştur
  python run_pipeline.py --report
  python run_pipeline.py --report --company "Şirket Adı"
  
  # Durum kontrol
  python run_pipeline.py --status
  python run_pipeline.py --analyze-pending
        """
    )
    
    parser.add_argument("--city", type=str, help="Şehir adı (örn: Istanbul)")
    parser.add_argument("--country", type=str, help="Ülke adı (örn: Turkey)")
    parser.add_argument("--limit", type=int, default=5, help="Maksimum şirket sayısı (default: 5)")
    parser.add_argument("--url", type=str, help="Doğrudan video URL (Instagram/TikTok/YouTube)")
    parser.add_argument("--company", type=str, default=None, help="Şirket adı (URL veya rapor için)")
    parser.add_argument("--status", action="store_true", help="MongoDB analiz sonuçlarını göster")
    parser.add_argument("--analyze-pending", action="store_true", help="Bekleyen videoları analiz et")
    parser.add_argument("--report", action="store_true", help="MongoDB'deki verilerden rapor oluştur")
    
    args = parser.parse_args()
    
    if args.status:
        asyncio.run(show_analysis_results())
    elif args.analyze_pending:
        asyncio.run(analyze_all_pending_videos())
    elif args.report:
        # MongoDB'den rapor oluştur
        asyncio.run(generate_report_only(args.company))
    elif args.url:
        # Doğrudan URL ile işle (Instagram rate limit bypass)
        company_name = args.company or "Direct URL Company"
        asyncio.run(process_direct_url(args.url, company_name))
    elif args.city and args.country:
        # Discovery sync, analiz + rapor async
        run_full_pipeline(args.city, args.country, args.limit)
    else:
        parser.print_help()
        print("\n⚠ Kullanım: --city + --country veya --url veya --report veya --status")
        sys.exit(1)


if __name__ == "__main__":
    main()
