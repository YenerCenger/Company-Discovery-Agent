from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class CompanyResponse(BaseModel):
    """Response schema for company data"""
    id: UUID
    name: str
    website_url: Optional[str]
    city: str
    country: str
    source: str
    importance_score: float
    is_active: bool
    created_at: datetime


class SocialProfileResponse(BaseModel):
    """Response schema for social profile data"""
    id: UUID
    company_id: UUID
    platform: str
    profile_url: str
    username: str
    followers_count: Optional[int]
    posts_count: Optional[int]
    engagement_score: Optional[float]
    content_type: Optional[str]


class SocialPostResponse(BaseModel):
    """Response schema for social post data"""
    id: UUID
    social_profile_id: UUID
    platform: str
    post_type: str
    post_url: str
    external_post_id: str
    caption_text: Optional[str]
    published_at: Optional[datetime]
    like_count: Optional[int]
    comment_count: Optional[int]
    view_count: Optional[int]


class VideoDownloadJobResponse(BaseModel):
    """Response schema for video download job"""
    id: UUID
    social_post_id: UUID
    platform: str
    post_url: str
    status: str
    file_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime


class PipelineStatsResponse(BaseModel):
    """Response schema for pipeline execution statistics"""
    companies_discovered: int
    profiles_found: int
    posts_found: int
    videos_downloaded: int
    errors: List[str] = []
