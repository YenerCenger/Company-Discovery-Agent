from typing import List
from agents.base import BaseAgent
from database.models import Company
from database.repositories import CompanyRepository
from scrapers.company_scraper import CompanyScraper
from services.scoring import calculate_importance_score
from schemas.requests import CompanyDiscoveryInput
from config.logging_config import get_logger


class CompanyDiscoveryAgent(BaseAgent[CompanyDiscoveryInput, Company]):
    """
    Agent for discovering real estate companies in a given location

    Responsibilities:
    1. Search for companies using CompanyScraper
    2. Calculate importance scores
    3. Deduplicate companies
    4. Persist to database
    5. Return top N companies
    """

    def __init__(self, db_session, logger=None):
        super().__init__(db_session, logger or get_logger(__name__))
        self.company_repo = CompanyRepository(db_session)
        self.company_scraper = CompanyScraper()

    def process(self, input_data: CompanyDiscoveryInput) -> List[Company]:
        """
        Discover companies for a given city/country

        Args:
            input_data: CompanyDiscoveryInput with city, country, limit

        Returns:
            List of Company objects
        """
        self.logger.info(
            "Starting company discovery",
            city=input_data.city,
            country=input_data.country,
            limit=input_data.limit
        )

        # Step 1: Scrape companies
        raw_companies = self.company_scraper.search_companies(
            city=input_data.city,
            country=input_data.country,
            limit=input_data.limit * 2  # Get more than needed for filtering
        )

        self.logger.info(
            "Scraped companies",
            count=len(raw_companies)
        )

        # Step 2: Process and score each company
        companies = []
        for raw_company in raw_companies:
            # Calculate importance score
            importance_score = calculate_importance_score(raw_company)

            # Prepare company data
            company_data = {
                "name": raw_company["name"],
                "website_url": raw_company.get("website_url"),
                "city": input_data.city,
                "country": input_data.country,
                "source": raw_company.get("source", "unknown"),
                "importance_score": importance_score,
                "is_active": True
            }

            # Upsert (handles deduplication)
            company = self.company_repo.upsert_by_name_city(company_data)
            companies.append(company)

        # Commit all changes
        self.db.commit()

        # Step 3: Sort by importance score and return top N
        companies.sort(key=lambda c: c.importance_score or 0, reverse=True)
        top_companies = companies[:input_data.limit]

        self.logger.info(
            "Company discovery completed",
            total_processed=len(companies),
            returned=len(top_companies)
        )

        return top_companies
