from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class CompanyDiscoveryInput(BaseModel):
    """Input schema for Company Discovery Agent"""
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    limit: int = Field(50, description="Maximum number of companies to discover", ge=1, le=200)


class ProfileFinderInput(BaseModel):
    """Input schema for Profile Finder Agent"""
    company_id: UUID = Field(..., description="Company UUID")
    company_name: str = Field(..., description="Company name")
    website_url: Optional[str] = Field(None, description="Company website URL")
    city: str = Field(..., description="City name")


class VideoFinderInput(BaseModel):
    """Input schema for Video Finder Agent"""
    profile_id: UUID = Field(..., description="Social profile UUID")
    profile_url: str = Field(..., description="Social profile URL")
    platform: str = Field(..., description="Platform name (instagram, tiktok, youtube)")
    days_back: int = Field(90, description="Number of days to look back", ge=1, le=365)


class VideoDownloadInput(BaseModel):
    """Input schema for Video Downloader Agent"""
    post_id: UUID = Field(..., description="Social post UUID")
    post_url: str = Field(..., description="Post URL")
    platform: str = Field(..., description="Platform name")
    external_post_id: str = Field(..., description="External post ID")
