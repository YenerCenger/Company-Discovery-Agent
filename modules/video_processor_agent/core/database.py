"""
Database connection management.

This module manages database connections:
- MongoDB (Motor): For storing video analysis results
- PostgreSQL (SQLModel): For reading video download jobs from Company Discovery Agent

Uses Singleton pattern for global database instances.
"""
import logging
from typing import Optional, List
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload

from modules.video_processor_agent.core.config import settings

# Import main project's database session and models
from database.session import engine
from database.models import VideoDownloadJob, SocialPost, SocialProfile, Company

logger = logging.getLogger(__name__)


# ==================== MONGODB CONNECTION (Analysis Results) ====================

class Database:
    """
    MongoDB database connection manager.
    
    Manages a single database instance using Singleton pattern.
    Provides asynchronous connections using async/await pattern.
    
    Example usage:
        await db.connect()
        collection = db.get_collection("videos")
        await db.close()
    """
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """
        Connects to MongoDB.
        
        Creates an optimized connection with connection pooling and timeout settings.
        Raises exception if connection fails.
        
        Raises:
            ConnectionFailure: If unable to connect to MongoDB
            ServerSelectionTimeoutError: If server selection fails
        """
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGO_URL,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=30000,
            )
            
            self.db = self.client[settings.DB_NAME]
            
            await self.client.admin.command("ping")
            
            logger.info(f"MongoDB connection successful: {settings.DB_NAME}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection error: {e}")
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise
    
    async def close(self) -> None:
        """
        Closes the database connection.
        
        Cleans up the entire connection pool and releases resources.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """
        Returns the specified collection (table).
        
        Args:
            collection_name: Collection name (e.g., "videos", "analysis_results")
            
        Returns:
            Motor collection object
            
        Raises:
            RuntimeError: If database connection is not established
        """
        if self.db is None:
            raise RuntimeError(
                "Database connection not established! Call 'await db.connect()' first."
            )
        return self.db[collection_name]
    
    async def ping(self) -> bool:
        """
        Checks if the database connection is healthy.
        
        Returns:
            True: Connection is healthy
            False: Connection is unhealthy or not established
        """
        try:
            if self.client is None:
                return False
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.warning(f"Database ping failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Checks if the database connection is open.
        
        Returns:
            True: Connection is open
            False: Connection is closed
        """
        return self.client is not None and self.db is not None
    
    async def __aenter__(self):
        """Context manager entry (async with support)."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (async with support)."""
        await self.close()


# ==================== GLOBAL MONGODB INSTANCE ====================
# Singleton pattern: Single database instance throughout the application
db = Database()


# ==================== MONGODB COLLECTION HELPERS ====================

def get_video_collection():
    """
    Returns the videos collection.
    
    Returns:
        Motor collection object for videos
    """
    return db.get_collection("videos")


def get_analysis_collection():
    """
    Returns the analysis_results collection.
    
    Returns:
        Motor collection object for analysis_results
    """
    return db.get_collection("analysis_results")


def get_company_collection():
    """
    Returns the companies collection.
    
    Returns:
        Motor collection object for companies
    """
    return db.get_collection("companies")


# ==================== POSTGRESQL HELPERS (Video Download Jobs) ====================

class VideoJobResult:
    """
    DTO for video download job with related data.
    
    Contains all necessary information for video processing.
    """
    def __init__(
        self,
        job_id: UUID,
        file_path: str,
        video_url: str,
        platform: str,
        company_id: UUID,
        company_name: str,
        view_count: Optional[int] = None,
        like_count: Optional[int] = None,
        comment_count: Optional[int] = None,
    ):
        self.job_id = job_id
        self.file_path = file_path
        self.video_url = video_url
        self.platform = platform
        self.company_id = company_id
        self.company_name = company_name
        self.view_count = view_count or 0
        self.like_count = like_count or 0
        self.comment_count = comment_count or 0


def get_completed_video_jobs(limit: int = 100) -> List[VideoJobResult]:
    """
    Gets all completed (status='done') video download jobs from PostgreSQL.
    
    Joins with SocialPost, SocialProfile, and Company to get full context.
    
    Args:
        limit: Maximum number of jobs to return
    
    Returns:
        List of VideoJobResult with complete video information
    """
    with Session(engine) as session:
        statement = (
            select(VideoDownloadJob)
            .where(VideoDownloadJob.status == "done")
            .where(VideoDownloadJob.file_path.isnot(None))
            .limit(limit)
        )
        jobs = session.exec(statement).all()
        
        results = []
        for job in jobs:
            # Get related SocialPost
            post = session.get(SocialPost, job.social_post_id)
            if not post:
                logger.warning(f"SocialPost not found for job {job.id}")
                continue
            
            # Get related SocialProfile
            profile = session.get(SocialProfile, post.social_profile_id)
            if not profile:
                logger.warning(f"SocialProfile not found for post {post.id}")
                continue
            
            # Get related Company
            company = session.get(Company, profile.company_id)
            if not company:
                logger.warning(f"Company not found for profile {profile.id}")
                continue
            
            results.append(VideoJobResult(
                job_id=job.id,
                file_path=job.file_path,
                video_url=job.post_url,
                platform=job.platform,
                company_id=company.id,
                company_name=company.name,
                view_count=post.view_count,
                like_count=post.like_count,
                comment_count=post.comment_count,
            ))
        
        logger.info(f"Found {len(results)} completed video jobs")
        return results


def get_video_job_by_id(job_id: UUID) -> Optional[VideoJobResult]:
    """
    Gets a specific video download job by ID.
    
    Args:
        job_id: UUID of the VideoDownloadJob
    
    Returns:
        VideoJobResult if found, None otherwise
    """
    with Session(engine) as session:
        job = session.get(VideoDownloadJob, job_id)
        if not job or job.status != "done" or not job.file_path:
            return None
        
        # Get related SocialPost
        post = session.get(SocialPost, job.social_post_id)
        if not post:
            return None
        
        # Get related SocialProfile
        profile = session.get(SocialProfile, post.social_profile_id)
        if not profile:
            return None
        
        # Get related Company
        company = session.get(Company, profile.company_id)
        if not company:
            return None
        
        return VideoJobResult(
            job_id=job.id,
            file_path=job.file_path,
            video_url=job.post_url,
            platform=job.platform,
            company_id=company.id,
            company_name=company.name,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
        )


def get_video_jobs_by_company(company_id: UUID) -> List[VideoJobResult]:
    """
    Gets all completed video jobs for a specific company.
    
    Args:
        company_id: UUID of the Company
    
    Returns:
        List of VideoJobResult for the company
    """
    with Session(engine) as session:
        # Get company
        company = session.get(Company, company_id)
        if not company:
            logger.warning(f"Company not found: {company_id}")
            return []
        
        # Get all profiles for this company
        profile_statement = select(SocialProfile).where(
            SocialProfile.company_id == company_id
        )
        profiles = session.exec(profile_statement).all()
        
        if not profiles:
            return []
        
        profile_ids = [p.id for p in profiles]
        
        # Get all posts for these profiles
        post_statement = select(SocialPost).where(
            SocialPost.social_profile_id.in_(profile_ids)
        )
        posts = session.exec(post_statement).all()
        
        if not posts:
            return []
        
        post_ids = [p.id for p in posts]
        post_map = {p.id: p for p in posts}
        
        # Get all completed download jobs for these posts
        job_statement = (
            select(VideoDownloadJob)
            .where(VideoDownloadJob.social_post_id.in_(post_ids))
            .where(VideoDownloadJob.status == "done")
            .where(VideoDownloadJob.file_path.isnot(None))
        )
        jobs = session.exec(job_statement).all()
        
        results = []
        for job in jobs:
            post = post_map.get(job.social_post_id)
            if not post:
                continue
            
            results.append(VideoJobResult(
                job_id=job.id,
                file_path=job.file_path,
                video_url=job.post_url,
                platform=job.platform,
                company_id=company.id,
                company_name=company.name,
                view_count=post.view_count,
                like_count=post.like_count,
                comment_count=post.comment_count,
            ))
        
        logger.info(f"Found {len(results)} completed video jobs for company {company.name}")
        return results


def get_unprocessed_video_jobs(processed_filenames: List[str], limit: int = 100) -> List[VideoJobResult]:
    """
    Gets completed video jobs that haven't been processed yet.
    
    Args:
        processed_filenames: List of already processed video filenames
        limit: Maximum number of jobs to return
    
    Returns:
        List of VideoJobResult that need processing
    """
    all_jobs = get_completed_video_jobs(limit=limit * 2)  # Get more to filter
    
    # Filter out already processed
    unprocessed = []
    for job in all_jobs:
        # Extract filename from file_path
        from pathlib import Path
        filename = Path(job.file_path).name
        
        if filename not in processed_filenames:
            unprocessed.append(job)
            if len(unprocessed) >= limit:
                break
    
    logger.info(f"Found {len(unprocessed)} unprocessed video jobs")
    return unprocessed
