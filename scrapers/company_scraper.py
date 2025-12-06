from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from utils.retry import retry
from utils.exceptions import ScraperError
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class CompanyScraper:
    """Scraper for discovering real estate companies"""

    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT
        self.user_agent = settings.USER_AGENT

    @retry(max_attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def search_companies(self, city: str, country: str, limit: int = 50) -> List[Dict]:
        """
        Search for real estate companies in a given city/country

        Args:
            city: City name
            country: Country name
            limit: Maximum number of companies to return

        Returns:
            List of company dictionaries with name, website_url, source
        """
        logger.info(
            "Searching for companies",
            city=city,
            country=country,
            limit=limit,
            crawl4ai_enabled=settings.CRAWL4AI_ENABLED
        )

        query = f"{city} {country} real estate"
        companies = self._scrape_with_crawl4ai(query)

        logger.info(
            "Found companies",
            count=len(companies),
            city=city,
            country=country
        )

        return companies[:limit]

    def _scrape_with_crawl4ai(self, query: str) -> List[Dict]:
        """
        Implementation using crawl4ai + LLM parsing
        
        Strategy:
        1. Try direct real estate directory sites (e.g., Realtor.com, local directories)
        2. Fallback to Realtor.com if in USA
        3. Return mock data as last resort (Google blocks bots)

        Args:
            query: Search query (e.g., "Miami Florida real estate")

        Returns:
            List of company dictionaries
        """
        logger.info(f"Starting Crawl4AI + LLM scraping for query: {query}")

        try:
            from scrapers.crawl4ai_handler import Crawl4AIHandler
            from scrapers.parsers.llm_parser import LLMParser
            from scrapers.parsers.realtor_parser import RealtorParser

            handler = Crawl4AIHandler()
            llm_parser = LLMParser()
            companies = []

            # Strategy 1: Try direct real estate company websites
            directory_urls = []
            query_lower = query.lower()
            
            # USA - Real estate company websites (gerçek emlak şirketlerinin web siteleri)
            if any(x in query_lower for x in ["usa", "united states", "florida", "california", "texas", "new york"]):
                directory_urls.extend([
                    "https://www.coldwellbanker.com",  # Coldwell Banker - Büyük emlak şirketi
                    "https://www.century21.com",  # Century 21
                    "https://www.remax.com",  # RE/MAX
                    "https://www.kw.com",  # Keller Williams
                    "https://www.berkshirehathaway.com",  # Berkshire Hathaway HomeServices
                    "https://www.compass.com",  # Compass
                    "https://www.redfin.com",  # Redfin
                    "https://www.zillow.com",  # Zillow
                ])
            
            # Poland - Real estate company websites (gerçek emlak şirketlerinin web siteleri)
            elif "poland" in query_lower or "warsaw" in query_lower or "polska" in query_lower:
                directory_urls.extend([
                    "https://www.domiporta.pl",  # Domiporta - Büyük emlak şirketi
                    "https://www.morizon.pl",  # Morizon
                    "https://www.otodom.pl",  # Otodom
                    "https://www.nieruchomosci-online.pl",  # Nieruchomosci Online
                    "https://www.gratka.pl",  # Gratka
                ])
            
            # Turkey - Real estate company websites (gerçek emlak şirketlerinin web siteleri)
            elif "turkey" in query_lower or "istanbul" in query_lower or "türkiye" in query_lower:
                directory_urls.extend([
                    "https://www.folkart.com.tr",  # Folkart - Büyük emlak şirketi
                    "https://www.avcilarinsaat.com.tr",  # Avcılar İnşaat
                    "https://www.esenlerinsaat.com.tr",  # Esenler İnşaat
                    "https://www.aydininsaat.com.tr",  # Aydın İnşaat
                    "https://www.atainsaat.com.tr",  # Ata İnşaat
                    "https://www.kozyatagiinsaat.com.tr",  # Kozyatağı İnşaat
                ])
            
            # UK - Real estate company websites
            elif "uk" in query_lower or "united kingdom" in query_lower or "england" in query_lower or "london" in query_lower:
                directory_urls.extend([
                    "https://www.rightmove.co.uk",  # Rightmove - Büyük emlak şirketi
                    "https://www.zoopla.co.uk",  # Zoopla
                    "https://www.onthemarket.com",  # OnTheMarket
                    "https://www.primelocation.com",  # PrimeLocation
                ])
            
            # Germany - Real estate company websites
            elif "germany" in query_lower or "deutschland" in query_lower or "berlin" in query_lower:
                directory_urls.extend([
                    "https://www.immobilienscout24.de",  # ImmobilienScout24 - Büyük emlak şirketi
                    "https://www.immowelt.de",  # ImmoWelt
                    "https://www.immobilo.de",  # Immobilo
                ])
            
            # France - Real estate company websites
            elif "france" in query_lower or "france" in query_lower or "paris" in query_lower:
                directory_urls.extend([
                    "https://www.seloger.com",  # SeLoger - Büyük emlak şirketi
                    "https://www.pap.fr",  # PAP
                    "https://www.leboncoin.fr",  # LeBonCoin
                ])
            
            # Spain - Real estate company websites
            elif "spain" in query_lower or "espana" in query_lower or "madrid" in query_lower or "barcelona" in query_lower:
                directory_urls.extend([
                    "https://www.idealista.com",  # Idealista - Büyük emlak şirketi
                    "https://www.fotocasa.es",  # Fotocasa
                    "https://www.habitaclia.com",  # Habitaclia
                ])
            
            # Italy - Real estate company websites
            elif "italy" in query_lower or "italia" in query_lower or "rome" in query_lower or "milano" in query_lower:
                directory_urls.extend([
                    "https://www.immobiliare.it",  # Immobiliare.it - Büyük emlak şirketi
                    "https://www.casa.it",  # Casa.it
                    "https://www.idealista.it",  # Idealista Italia
                ])
            
            # Canada - Real estate company websites
            elif "canada" in query_lower or "toronto" in query_lower or "vancouver" in query_lower:
                directory_urls.extend([
                    "https://www.realtor.ca",  # Realtor.ca - Büyük emlak şirketi
                    "https://www.remax.ca",  # RE/MAX Canada
                    "https://www.century21.ca",  # Century 21 Canada
                ])
            
            # Australia - Real estate company websites
            elif "australia" in query_lower or "sydney" in query_lower or "melbourne" in query_lower:
                directory_urls.extend([
                    "https://www.realestate.com.au",  # RealEstate.com.au - Büyük emlak şirketi
                    "https://www.domain.com.au",  # Domain
                    "https://www.allhomes.com.au",  # AllHomes
                ])
            
            # UAE - Real estate company websites
            elif "uae" in query_lower or "dubai" in query_lower or "united arab emirates" in query_lower:
                directory_urls.extend([
                    "https://www.dubizzle.com",  # Dubizzle - Büyük emlak şirketi
                    "https://www.propertyfinder.ae",  # PropertyFinder
                    "https://www.bayut.com",  # Bayut
                ])
            
            # If no specific URLs found, try generic international real estate companies
            if not directory_urls:
                # Global real estate companies that work in multiple countries
                directory_urls.extend([
                    "https://www.remax.com",  # RE/MAX - Global
                    "https://www.century21.com",  # Century 21 - Global
                    "https://www.coldwellbanker.com",  # Coldwell Banker - Global
                ])
            
            # Try each directory URL with LLM
            for url in directory_urls:
                try:
                    logger.info(f"Strategy 1: Direct site + LLM: {url}")
                    html = handler.crawl_sync(url)

                    if html and len(html) > 5000:  # Ensure we got real content
                        logger.info(f"HTML retrieved: {len(html):,} characters from {url}")
                        companies = llm_parser.extract_companies(
                            html=html,
                            query_context=query,
                            limit=50
                        )
                        logger.info(f"LLM parser returned {len(companies)} companies from {url}")

                        if companies:
                            return companies  # Success!
                        else:
                            logger.warning(f"LLM found no companies from {url}, trying next URL")
                    else:
                        logger.warning(f"HTML too short or empty from {url}: {len(html) if html else 0} characters")

                except Exception as e:
                    logger.warning(f"Direct site {url} failed: {e}")
                    continue

            # No companies found from any URL - return empty list (no mock data)
            logger.warning("No companies found from any source, returning empty list")
            return []

        except Exception as e:
            logger.error(f"Crawl4AI scraping error: {e}", exc_info=True)
            return []
