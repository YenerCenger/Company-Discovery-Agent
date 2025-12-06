from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class BaseSocialScraper(ABC):
    """Base interface for social media scrapers"""

    def __init__(self):
        """Initialize social scraper"""
        pass

    @abstractmethod
    def _get_platform_name(self) -> str:
        """Get platform name (instagram, etc.)"""
        pass

    def find_profile(self, company_name: str, website_url: Optional[str] = None) -> Optional[Dict]:
        """
        Find social profile for a company

        Args:
            company_name: Name of the company
            website_url: Company website URL (optional)

        Returns:
            Profile data dictionary or None if not found
        """
        return self._find_profile_real(company_name, website_url)

    def get_recent_posts(self, profile_url: str, limit: int = 50) -> List[Dict]:
        """
        Get recent posts from a profile

        Args:
            profile_url: Social profile URL
            limit: Maximum number of posts to retrieve

        Returns:
            List of post data dictionaries
        """
        return self._get_recent_posts_real(profile_url, limit)

    def get_profile_metadata(self, profile_url: str) -> Optional[Dict]:
        """
        Get profile metadata (followers, posts count, etc.)

        Args:
            profile_url: Social profile URL

        Returns:
            Profile metadata dictionary or None if not found
        """
        return self._get_profile_metadata_real(profile_url)

    # Real implementation methods (to be overridden by subclasses)
    @abstractmethod
    def _find_profile_real(self, company_name: str, website_url: Optional[str]) -> Optional[Dict]:
        """Real implementation for finding profile (override in subclasses)"""
        pass

    @abstractmethod
    def _get_recent_posts_real(self, profile_url: str, limit: int) -> List[Dict]:
        """Real implementation for getting posts (override in subclasses)"""
        pass

    @abstractmethod
    def _get_profile_metadata_real(self, profile_url: str) -> Optional[Dict]:
        """Real implementation for getting metadata (override in subclasses)"""
        pass
