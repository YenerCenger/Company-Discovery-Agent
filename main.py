"""
Main entry point for AI Real-Estate Marketing Intelligence System

This orchestrator coordinates the full pipeline:
1. Company Discovery Agent
2. Profile Finder Agent
3. Video Finder Agent
4. Video Downloader Agent

Supports both CLI and REST API modes:
- CLI Mode: python main.py --city Miami --country USA --limit 50
- API Mode: python main.py --mode api
"""

import argparse
from typing import Dict, Optional, List
from datetime import datetime, timezone
from uuid import UUID
import uvicorn

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

# Database and agents
from database.session import get_db_session
from agents.company_discovery import CompanyDiscoveryAgent
from agents.profile_finder import ProfileFinderAgent
from agents.video_finder import VideoFinderAgent
from agents.video_downloader import VideoDownloaderAgent
from schemas.requests import CompanyDiscoveryInput
from database.models import Company, SocialProfile, SocialPost, VideoDownloadJob
from config.logging_config import get_logger
from config.settings import settings
from sqlmodel import select

logger = get_logger(__name__)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class DiscoverRequest(BaseModel):
    """Request model for discovery endpoint"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "city": "Miami",
            "country": "USA",
            "companies": 10
        }
    })
    
    city: str = Field(..., description="City name (e.g., Miami)")
    country: str = Field(..., description="Country name (e.g., USA)")
    companies: Optional[int] = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of companies to discover (1-100)"
    )


class DiscoverResponse(BaseModel):
    """Response model for discovery endpoint"""
    job_id: str
    status: str
    message: str
    companies_discovered: int
    profiles_found: int
    videos_found: int
    videos_downloaded: int


class CompanyResponse(BaseModel):
    """Company information response"""
    id: str
    name: str
    website_url: Optional[str]
    city: str
    country: str
    importance_score: float
    created_at: datetime


class ProfileResponse(BaseModel):
    """Social profile response"""
    id: str
    company_id: str
    company_name: str
    platform: str
    username: str
    profile_url: str
    followers_count: Optional[int]
    engagement_score: Optional[float]
    content_type: Optional[str]


class VideoResponse(BaseModel):
    """Video post response"""
    id: str
    profile_id: str
    username: str
    post_url: str
    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    published_at: Optional[datetime]
    download_status: Optional[str]
    file_path: Optional[str]


class StatusResponse(BaseModel):
    """System status response"""
    status: str
    total_companies: int
    total_profiles: int
    total_videos: int
    downloaded_videos: int
    pending_downloads: int


# Background job tracking (in production, use Redis/Celery)
job_status = {}


# ============================================================================
# AGENT ORCHESTRATOR
# ============================================================================

class AgentOrchestrator:
    """
    Orchestrates the execution of all agents in sequence

    Pipeline:
    Company Discovery � Profile Finder � Video Finder � Video Downloader
    """

    def __init__(self, db_session):
        """
        Initialize orchestrator with database session

        Args:
            db_session: SQLModel database session
        """
        self.db = db_session
        self.logger = get_logger(self.__class__.__name__)

        # Initialize all agents
        self.discovery_agent = CompanyDiscoveryAgent(db_session, self.logger)
        self.profile_agent = ProfileFinderAgent(db_session, self.logger)
        self.video_finder_agent = VideoFinderAgent(db_session, self.logger)
        self.downloader_agent = VideoDownloaderAgent(db_session, self.logger)

    def run_full_pipeline(
        self,
        city: str,
        country: str,
        limit: int = 50
    ) -> Dict[str, int]:
        """
        Run the complete pipeline from company discovery to video download

        Args:
            city: City name (e.g., "Miami")
            country: Country name (e.g., "USA")
            limit: Maximum number of companies to discover

        Returns:
            Dictionary with statistics:
            - companies: Number of companies discovered
            - profiles: Number of social profiles found
            - posts: Number of video posts found
            - downloads: Number of videos downloaded
        """
        self.logger.info(
            "=== Starting Full Pipeline ===",
            city=city,
            country=country,
            limit=limit
        )

        # Step 1: Discover companies
        self.logger.info("Step 1/4: Discovering companies")
        discovery_input = CompanyDiscoveryInput(
            city=city,
            country=country,
            limit=limit
        )
        companies = self.discovery_agent.execute(discovery_input)

        if not companies:
            self.logger.warning("No companies discovered. Pipeline stopped.")
            return {
                'companies': 0,
                'profiles': 0,
                'posts': 0,
                'downloads': 0
            }

        # Step 2: Find social profiles for each company
        self.logger.info(
            "Step 2/4: Finding social profiles",
            company_count=len(companies)
        )
        all_profiles = []
        for company in companies:
            profiles = self.profile_agent.execute(company)
            all_profiles.extend(profiles)

        if not all_profiles:
            self.logger.warning("No social profiles found. Pipeline stopped.")
            return {
                'companies': len(companies),
                'profiles': 0,
                'posts': 0,
                'downloads': 0
            }

        # Step 3: Find videos for each profile
        self.logger.info(
            "Step 3/4: Finding video posts",
            profile_count=len(all_profiles)
        )
        all_posts = []
        for profile in all_profiles:
            posts = self.video_finder_agent.execute(profile)
            all_posts.extend(posts)

        if not all_posts:
            self.logger.warning("No video posts found. Pipeline stopped.")
            return {
                'companies': len(companies),
                'profiles': len(all_profiles),
                'posts': 0,
                'downloads': 0
            }

        # Step 4: Download videos (limit per company)
        # Group posts by company
        posts_by_company = {}
        for post in all_posts:
            # Get company_id from the profile
            profile = next((p for p in all_profiles if p.id == post.social_profile_id), None)
            if profile:
                company_id = profile.company_id
                if company_id not in posts_by_company:
                    posts_by_company[company_id] = []
                posts_by_company[company_id].append(post)

        # Limit posts per company based on VIDEO_DOWNLOAD_PER_COMPANY setting
        posts_to_download = []
        for company_id, posts in posts_by_company.items():
            # Take only the first N posts per company (already sorted by views/engagement)
            limited_posts = posts[:settings.VIDEO_DOWNLOAD_PER_COMPANY]
            posts_to_download.extend(limited_posts)

        self.logger.info(
            "Step 4/4: Downloading videos",
            total_posts=len(all_posts),
            posts_to_download=len(posts_to_download),
            limit_per_company=settings.VIDEO_DOWNLOAD_PER_COMPANY
        )
        download_jobs = self.downloader_agent.execute(posts_to_download)

        # Calculate results
        results = {
            'companies': len(companies),
            'profiles': len(all_profiles),
            'posts': len(all_posts),
            'downloads': sum(1 for j in download_jobs if j.status == "done")
        }

        self.logger.info(
            "=== Pipeline Completed ===",
            **results
        )

        return results

    def run_company_discovery_only(self, city: str, country: str, limit: int = 50):
        """Run only company discovery step"""
        discovery_input = CompanyDiscoveryInput(city=city, country=country, limit=limit)
        return self.discovery_agent.execute(discovery_input)

    def run_profile_finder_only(self, company_id: str):
        """Run only profile finder for a specific company"""
        from database.models import Company
        company = self.db.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")
        return self.profile_agent.execute(company)

    def run_video_finder_only(self, profile_id: str):
        """Run only video finder for a specific profile"""
        from database.models import SocialProfile
        profile = self.db.get(SocialProfile, profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        return self.video_finder_agent.execute(profile)


# ============================================================================
# BACKGROUND TASKS FOR API
# ============================================================================

def run_discovery_pipeline(job_id: str, city: str, country: str, limit: int):
    """Background task to run discovery pipeline"""
    try:
        job_status[job_id] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "progress": "Discovering companies..."
        }

        with get_db_session() as session:
            orchestrator = AgentOrchestrator(session)

            # Step 1: Discover companies
            job_status[job_id]["progress"] = "Discovering companies..."
            discovery_input = CompanyDiscoveryInput(
                city=city,
                country=country,
                limit=limit
            )
            companies = orchestrator.discovery_agent.execute(discovery_input)

            # Step 2: Find profiles
            job_status[job_id]["progress"] = f"Finding profiles for {len(companies)} companies..."
            all_profiles = []
            for company in companies:
                profiles = orchestrator.profile_agent.execute(company)
                all_profiles.extend(profiles)

            # Step 3: Find videos
            job_status[job_id]["progress"] = f"Finding videos from {len(all_profiles)} profiles..."
            all_posts = []
            for profile in all_profiles:
                posts = orchestrator.video_finder_agent.execute(profile)
                all_posts.extend(posts)

            # Step 4: Download videos (limit per company)
            job_status[job_id]["progress"] = f"Preparing to download videos (limit: {settings.VIDEO_DOWNLOAD_PER_COMPANY} per company)..."

            # Group posts by company
            posts_by_company = {}
            for post in all_posts:
                # Get company_id from the profile
                profile = next((p for p in all_profiles if p.id == post.social_profile_id), None)
                if profile:
                    company_id = profile.company_id
                    if company_id not in posts_by_company:
                        posts_by_company[company_id] = []
                    posts_by_company[company_id].append(post)

            # Limit posts per company based on VIDEO_DOWNLOAD_PER_COMPANY setting
            posts_to_download = []
            for company_id, posts in posts_by_company.items():
                # Take only the first N posts per company (already sorted by views/engagement)
                limited_posts = posts[:settings.VIDEO_DOWNLOAD_PER_COMPANY]
                posts_to_download.extend(limited_posts)

            job_status[job_id]["progress"] = f"Downloading {len(posts_to_download)} videos..."
            download_jobs = orchestrator.downloader_agent.execute(posts_to_download)

            # Update job status
            job_status[job_id] = {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "companies_discovered": len(companies),
                "profiles_found": len(all_profiles),
                "videos_found": len(all_posts),
                "videos_downloaded": sum(1 for j in download_jobs if j.status == "done")
            }

    except Exception as e:
        logger.error(f"Discovery pipeline failed", job_id=job_id, error=str(e))
        job_status[job_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now(timezone.utc)
        }


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Real Estate Marketing Intelligence API",
    description="Instagram video discovery and download for real estate companies",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Real Estate Marketing Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "discover": "POST /api/discover",
            "companies": "GET /api/companies",
            "profiles": "GET /api/profiles",
            "videos": "GET /api/videos",
            "status": "GET /api/status"
        }
    }


@app.post("/api/discover", response_model=DiscoverResponse)
async def discover_companies(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks
):
    """
    Start company discovery and video processing pipeline

    This endpoint:
    1. Discovers real estate companies in the specified city
    2. Finds their Instagram profiles
    3. Extracts top performing videos
    4. Downloads videos to local storage
    5. Saves everything to database

    The process runs in the background. Use GET /api/job/{job_id} to check progress.
    """
    import uuid
    job_id = str(uuid.uuid4())

    # Start background task
    background_tasks.add_task(
        run_discovery_pipeline,
        job_id,
        request.city,
        request.country,
        request.companies
    )

    logger.info(
        "Discovery job started",
        job_id=job_id,
        city=request.city,
        country=request.country,
        limit=request.companies
    )

    return DiscoverResponse(
        job_id=job_id,
        status="started",
        message=f"Discovery pipeline started for {request.city}, {request.country}",
        companies_discovered=0,
        profiles_found=0,
        videos_found=0,
        videos_downloaded=0
    )


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a discovery job"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status[job_id]


@app.get("/api/companies", response_model=List[CompanyResponse])
async def list_companies(
    city: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50
):
    """
    List discovered companies

    Filter by city and/or country, or get all companies.
    """
    with get_db_session() as session:
        statement = select(Company)

        if city:
            statement = statement.where(Company.city == city)
        if country:
            statement = statement.where(Company.country == country)

        statement = statement.order_by(Company.importance_score.desc()).limit(limit)

        companies = session.exec(statement).all()

        return [
            CompanyResponse(
                id=str(c.id),
                name=c.name,
                website_url=c.website_url,
                city=c.city,
                country=c.country,
                importance_score=c.importance_score or 0.0,
                created_at=c.created_at
            )
            for c in companies
        ]


@app.get("/api/profiles", response_model=List[ProfileResponse])
async def list_profiles(
    platform: Optional[str] = "instagram",
    limit: int = 50
):
    """
    List social media profiles

    Filter by platform (instagram, tiktok, youtube)
    """
    with get_db_session() as session:
        statement = select(SocialProfile).where(
            SocialProfile.platform == platform
        ).order_by(
            SocialProfile.engagement_score.desc()
        ).limit(limit)

        profiles = session.exec(statement).all()

        return [
            ProfileResponse(
                id=str(p.id),
                company_id=str(p.company_id),
                company_name=p.company.name if p.company else "Unknown",
                platform=p.platform,
                username=p.username,
                profile_url=p.profile_url,
                followers_count=p.followers_count,
                engagement_score=p.engagement_score,
                content_type=p.content_type
            )
            for p in profiles
        ]


@app.get("/api/videos", response_model=List[VideoResponse])
async def list_videos(
    sort_by: str = "views",
    min_views: int = 1000,
    limit: int = 100
):
    """
    List video posts

    Sort by: views, likes, engagement
    Filter by minimum views
    """
    with get_db_session() as session:
        statement = select(SocialPost).where(
            SocialPost.view_count >= min_views
        )

        if sort_by == "views":
            statement = statement.order_by(SocialPost.view_count.desc())
        elif sort_by == "likes":
            statement = statement.order_by(SocialPost.like_count.desc())
        else:
            statement = statement.order_by(SocialPost.view_count.desc())

        statement = statement.limit(limit)

        posts = session.exec(statement).all()

        # Get download status for each post
        results = []
        for post in posts:
            download_job = session.exec(
                select(VideoDownloadJob).where(
                    VideoDownloadJob.social_post_id == post.id
                ).order_by(VideoDownloadJob.created_at.desc())
            ).first()

            results.append(VideoResponse(
                id=str(post.id),
                profile_id=str(post.social_profile_id),
                username=post.social_profile.username if post.social_profile else "Unknown",
                post_url=post.post_url,
                view_count=post.view_count,
                like_count=post.like_count,
                comment_count=post.comment_count,
                published_at=post.published_at,
                download_status=download_job.status if download_job else None,
                file_path=download_job.file_path if download_job else None
            ))

        return results


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """
    Get overall system status

    Returns counts of companies, profiles, videos, and downloads
    """
    with get_db_session() as session:
        total_companies = session.exec(select(Company)).all()
        total_profiles = session.exec(select(SocialProfile)).all()
        total_videos = session.exec(select(SocialPost)).all()

        download_jobs = session.exec(select(VideoDownloadJob)).all()
        downloaded = sum(1 for j in download_jobs if j.status == "done")
        pending = sum(1 for j in download_jobs if j.status == "pending")

        return StatusResponse(
            status="online",
            total_companies=len(total_companies),
            total_profiles=len(total_profiles),
            total_videos=len(total_videos),
            downloaded_videos=downloaded,
            pending_downloads=pending
        )


# ============================================================================
# CLI FUNCTIONS
# ============================================================================

def run_cli(args):
    """Run in CLI mode"""
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Real-Estate Marketing Intelligence System"
    )

    parser.add_argument(
        "--city",
        type=str,
        required=True,
        help="City name (e.g., Miami)"
    )

def run_cli(args):
    """Run in CLI mode"""
    logger.info(
        "Starting AI Real-Estate Marketing Intelligence System (CLI Mode)",
        city=args.city,
        country=args.country,
        limit=args.limit,
        step=args.step
    )

    try:
        with get_db_session() as session:
            orchestrator = AgentOrchestrator(session)

            if args.step == "full":
                results = orchestrator.run_full_pipeline(
                    city=args.city,
                    country=args.country,
                    limit=args.limit
                )

                # Print results
                print("\n" + "="*60)
                print("PIPELINE RESULTS")
                print("="*60)
                print(f"Companies Discovered:  {results['companies']}")
                print(f"Social Profiles Found: {results['profiles']}")
                print(f"Video Posts Found:     {results['posts']}")
                print(f"Videos Downloaded:     {results['downloads']}")
                print("="*60 + "\n")

            elif args.step == "discovery":
                companies = orchestrator.run_company_discovery_only(
                    city=args.city,
                    country=args.country,
                    limit=args.limit
                )
                print(f"\nDiscovered {len(companies)} companies")
                for company in companies[:10]:  # Show first 10
                    print(f"  - {company.name} ({company.importance_score:.2f})")

            else:
                print(f"Step '{args.step}' not fully implemented in CLI")

        return 0

    except Exception as e:
        logger.error("Pipeline failed", error=str(e), exc_info=True)
        print(f"\nError: {str(e)}")
        return 1


def run_api():
    """Run in API server mode"""
    print("\n" + "="*60)
    print("Real Estate Marketing Intelligence API")
    print("="*60)
    print(f"\nStarting API server...")
    print(f"Docs: http://localhost:8000/docs")
    print(f"API:  http://localhost:8000/api")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point - supports both CLI and API modes"""
    parser = argparse.ArgumentParser(
        description="AI Real-Estate Marketing Intelligence System"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["cli", "api"],
        default="cli",
        help="Run mode: 'cli' for command-line or 'api' for REST API server (default: cli)"
    )

    parser.add_argument(
        "--city",
        type=str,
        required=False,
        help="City name (e.g., Miami) - required for CLI mode"
    )

    parser.add_argument(
        "--country",
        type=str,
        required=False,
        help="Country name (e.g., USA) - required for CLI mode"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=settings.COMPANY_DISCOVERY_DEFAULT_LIMIT,
        help=f"Maximum number of companies to discover (default: {settings.COMPANY_DISCOVERY_DEFAULT_LIMIT})"
    )

    parser.add_argument(
        "--step",
        type=str,
        choices=["full", "discovery", "profiles", "videos", "download"],
        default="full",
        help="Which step to run (default: full pipeline)"
    )

    args = parser.parse_args()

    # Route to appropriate mode
    if args.mode == "api":
        return run_api()
    else:
        # Validate required CLI arguments
        if not args.city or not args.country:
            parser.error("--city and --country are required for CLI mode")
        return run_cli(args)


if __name__ == "__main__":
    exit(main())
