from typing import List
from agents.base import BaseAgent
from database.models import Company, SocialProfile
from database.repositories import SocialProfileRepository
from scrapers.social.instagram import InstagramScraper
from services.scoring import calculate_engagement_score
from config.logging_config import get_logger
from datetime import datetime


class ProfileFinderAgent(BaseAgent[Company, SocialProfile]):
    """
    Agent for finding social media profiles for companies

    Responsibilities:
    1. Search for profiles on Instagram
    2. Calculate engagement scores
    3. Classify content type
    4. Persist profiles to database
    5. Return list of found profiles
    """

    def __init__(self, db_session, logger=None):
        super().__init__(db_session, logger or get_logger(__name__))
        self.profile_repo = SocialProfileRepository(db_session)

        # Initialize Instagram scraper only
        self.instagram_scraper = InstagramScraper()

        self.scrapers = {
            "instagram": self.instagram_scraper
        }

    def process(self, input_data: Company) -> List[SocialProfile]:
        """
        Find social profiles for a company

        Args:
            input_data: Company object

        Returns:
            List of SocialProfile objects
        """
        self.logger.info(
            "Finding social profiles",
            company_id=str(input_data.id),
            company_name=input_data.name
        )

        profiles = []

        # Search each platform
        for platform, scraper in self.scrapers.items():
            try:
                # Check if profile already exists
                existing = self.profile_repo.find_by_company_and_platform(
                    company_id=input_data.id,
                    platform=platform
                )

                if existing:
                    self.logger.info(
                        f"{platform} profile already exists",
                        company_name=input_data.name,
                        profile_url=existing.profile_url
                    )
                    profiles.append(existing)
                    continue

                # Find profile
                profile_data = scraper.find_profile(
                    company_name=input_data.name,
                    website_url=input_data.website_url
                )

                if not profile_data:
                    self.logger.info(
                        f"No {platform} profile found",
                        company_name=input_data.name
                    )
                    continue

                # Check if this profile URL already exists (might be for different company)
                existing_by_url = self.profile_repo.find_by_profile_url(
                    profile_url=profile_data["profile_url"]
                )

                if existing_by_url:
                    self.logger.info(
                        f"{platform} profile URL already exists",
                        company_name=input_data.name,
                        profile_url=profile_data["profile_url"],
                        existing_company_id=str(existing_by_url.company_id)
                    )
                    # Use existing profile instead of creating duplicate
                    profiles.append(existing_by_url)
                    continue

                # Calculate engagement score
                engagement_score = calculate_engagement_score(profile_data)

                # Create profile
                profile = self.profile_repo.create({
                    "company_id": input_data.id,
                    "platform": platform,
                    "profile_url": profile_data["profile_url"],
                    "username": profile_data["username"],
                    "followers_count": profile_data.get("followers_count"),
                    "posts_count": profile_data.get("posts_count"),
                    "engagement_score": engagement_score,
                    "content_type": "mixed",  # Will be classified later by VideoFinderAgent
                    "last_scraped_at": datetime.utcnow(),
                    "is_active": True
                })

                profiles.append(profile)

                self.logger.info(
                    f"Found {platform} profile",
                    company_name=input_data.name,
                    username=profile.username,
                    engagement_score=engagement_score
                )

            except Exception as e:
                self.logger.error(
                    f"Error finding {platform} profile",
                    company_name=input_data.name,
                    error=str(e)
                )
                # Continue with other platforms

        # Commit all changes
        self.db.commit()

        self.logger.info(
            "Profile search completed",
            company_name=input_data.name,
            profiles_found=len(profiles)
        )

        return profiles
