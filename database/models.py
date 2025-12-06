from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class PlatformEnum(str, Enum):
    """Social media platforms"""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PostTypeEnum(str, Enum):
    """Types of social media posts"""
    REEL = "reel"
    POST = "post"
    SHORT = "short"
    VIDEO = "video"


class JobStatusEnum(str, Enum):
    """Video download job statuses"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    ERROR = "error"


class Company(SQLModel, table=True):
    """
    Real estate and construction companies discovered by the system
    """
    __tablename__ = "companies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    website_url: Optional[str] = None
    city: str = Field(index=True)
    country: str = Field(index=True)
    source: str  # "google", "directory_x", "manual"
    importance_score: Optional[float] = Field(default=0.0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    social_profiles: List["SocialProfile"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class SocialProfile(SQLModel, table=True):
    """
    Social media profiles (Instagram, TikTok, YouTube) for companies
    """
    __tablename__ = "social_profiles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id")
    platform: str  # Will use PlatformEnum values
    profile_url: str = Field(unique=True)
    username: str
    followers_count: Optional[int] = None
    posts_count: Optional[int] = None
    engagement_score: Optional[float] = None
    content_type: Optional[str] = None  # "listing-focused", "educational", "mixed"
    last_scraped_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    company: Company = Relationship(back_populates="social_profiles")
    posts: List["SocialPost"] = Relationship(
        back_populates="social_profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class SocialPost(SQLModel, table=True):
    """
    Individual posts/videos from social media profiles
    """
    __tablename__ = "social_posts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    social_profile_id: UUID = Field(foreign_key="social_profiles.id")
    platform: str  # Will use PlatformEnum values
    post_type: str  # Will use PostTypeEnum values
    post_url: str
    external_post_id: str
    caption_text: Optional[str] = None
    published_at: Optional[datetime] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    view_count: Optional[int] = None
    saved_count: Optional[int] = None
    last_scraped_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    social_profile: SocialProfile = Relationship(back_populates="posts")
    download_jobs: List["VideoDownloadJob"] = Relationship(
        back_populates="social_post",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class VideoDownloadJob(SQLModel, table=True):
    """
    Video download jobs and their status
    """
    __tablename__ = "video_download_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    social_post_id: UUID = Field(foreign_key="social_posts.id")
    platform: str  # Will use PlatformEnum values
    post_url: str
    status: str = Field(default="pending")  # Will use JobStatusEnum values
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    social_post: SocialPost = Relationship(back_populates="download_jobs")
