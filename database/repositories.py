from sqlmodel import Session, select
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime, timedelta
from database.models import Company, SocialProfile, SocialPost, VideoDownloadJob
from utils.text_processing import normalize_company_name


class CompanyRepository:
    """Repository for Company entity operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, company_data: dict) -> Company:
        """Create a new company"""
        company = Company(**company_data)
        self.session.add(company)
        self.session.flush()
        self.session.refresh(company)
        return company

    def upsert_by_name_city(self, company_data: dict) -> Company:
        """
        Upsert company by normalized name + city + country
        Updates importance_score if new score is higher
        """
        normalized_name = normalize_company_name(company_data["name"])

        # Check if company exists
        statement = select(Company).where(
            Company.city == company_data["city"],
            Company.country == company_data["country"]
        )
        existing_companies = self.session.exec(statement).all()

        # Find matching company by normalized name
        existing = None
        for comp in existing_companies:
            if normalize_company_name(comp.name) == normalized_name:
                existing = comp
                break

        if existing:
            # Update if importance score is higher
            if company_data.get("importance_score", 0) > existing.importance_score:
                existing.importance_score = company_data["importance_score"]
                existing.website_url = company_data.get("website_url") or existing.website_url
                existing.source = company_data.get("source") or existing.source
                existing.updated_at = datetime.utcnow()
                self.session.add(existing)
                self.session.flush()
                self.session.refresh(existing)
            return existing
        else:
            return self.create(company_data)

    def find_active_companies(self, city: str, country: str) -> List[Company]:
        """Find all active companies for a location"""
        statement = select(Company).where(
            Company.city == city,
            Company.country == country,
            Company.is_active == True
        )
        return list(self.session.exec(statement).all())

    def update_importance_score(self, company_id: UUID, score: float) -> None:
        """Update company importance score"""
        company = self.session.get(Company, company_id)
        if company:
            company.importance_score = score
            company.updated_at = datetime.utcnow()
            self.session.add(company)


class SocialProfileRepository:
    """Repository for SocialProfile entity operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, profile_data: dict) -> SocialProfile:
        """Create a new social profile"""
        profile = SocialProfile(**profile_data)
        self.session.add(profile)
        self.session.flush()
        self.session.refresh(profile)
        return profile

    def find_by_company_and_platform(
        self, company_id: UUID, platform: str
    ) -> Optional[SocialProfile]:
        """Find a social profile by company and platform"""
        statement = select(SocialProfile).where(
            SocialProfile.company_id == company_id,
            SocialProfile.platform == platform,
            SocialProfile.is_active == True
        )
        return self.session.exec(statement).first()

    def find_by_profile_url(self, profile_url: str) -> Optional[SocialProfile]:
        """Find a social profile by URL"""
        statement = select(SocialProfile).where(
            SocialProfile.profile_url == profile_url
        )
        return self.session.exec(statement).first()

    def update_metadata(
        self,
        profile_id: UUID,
        followers_count: int = None,
        posts_count: int = None,
        engagement_score: float = None
    ) -> None:
        """Update social profile metadata"""
        profile = self.session.get(SocialProfile, profile_id)
        if profile:
            if followers_count is not None:
                profile.followers_count = followers_count
            if posts_count is not None:
                profile.posts_count = posts_count
            if engagement_score is not None:
                profile.engagement_score = engagement_score
            profile.last_scraped_at = datetime.utcnow()
            profile.updated_at = datetime.utcnow()
            self.session.add(profile)


class SocialPostRepository:
    """Repository for SocialPost entity operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, post_data: dict) -> SocialPost:
        """Create a new social post"""
        post = SocialPost(**post_data)
        self.session.add(post)
        self.session.flush()
        self.session.refresh(post)
        return post

    def find_by_external_id(
        self, profile_id: UUID, external_post_id: str
    ) -> Optional[SocialPost]:
        """Find a post by external ID"""
        statement = select(SocialPost).where(
            SocialPost.social_profile_id == profile_id,
            SocialPost.external_post_id == external_post_id
        )
        return self.session.exec(statement).first()

    def find_recent_by_profile(
        self, profile_id: UUID, days: int = 90
    ) -> List[SocialPost]:
        """Find posts from the last N days for a profile"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        statement = select(SocialPost).where(
            SocialPost.social_profile_id == profile_id,
            SocialPost.published_at >= cutoff_date
        ).order_by(SocialPost.published_at.desc())
        return list(self.session.exec(statement).all())

    def find_video_posts_without_download(self, limit: int = 100) -> List[SocialPost]:
        """Find video posts that haven't been downloaded yet"""
        statement = (
            select(SocialPost)
            .where(
                SocialPost.post_type.in_(["reel", "short", "video"])
            )
            .limit(limit)
        )
        posts = list(self.session.exec(statement).all())

        # Filter out posts that already have download jobs
        posts_without_jobs = []
        for post in posts:
            if not post.download_jobs:
                posts_without_jobs.append(post)

        return posts_without_jobs


class VideoDownloadJobRepository:
    """Repository for VideoDownloadJob entity operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, job_data: dict) -> VideoDownloadJob:
        """Create a new download job"""
        job = VideoDownloadJob(**job_data)
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job

    def update_status(
        self,
        job_id: UUID,
        status: str,
        file_path: str = None,
        error_message: str = None
    ) -> None:
        """Update download job status"""
        job = self.session.get(VideoDownloadJob, job_id)
        if job:
            job.status = status
            if file_path:
                job.file_path = file_path
            if error_message:
                job.error_message = error_message
            job.updated_at = datetime.utcnow()
            self.session.add(job)

    def find_pending_jobs(self, limit: int = 100) -> List[VideoDownloadJob]:
        """Find pending download jobs"""
        statement = select(VideoDownloadJob).where(
            VideoDownloadJob.status == "pending"
        ).limit(limit)
        return list(self.session.exec(statement).all())

    def find_by_post(self, post_id: UUID) -> Optional[VideoDownloadJob]:
        """Find download job for a specific post"""
        statement = select(VideoDownloadJob).where(
            VideoDownloadJob.social_post_id == post_id
        ).order_by(VideoDownloadJob.created_at.desc())
        return self.session.exec(statement).first()
