"""
LLM-based parser for extracting company data from any HTML source

This parser uses Ollama + Gemma 3:4b to intelligently extract real estate
company information from any website, making it site-agnostic and suitable
for international markets.
"""

from typing import List, Dict
import structlog
from services.llm_service import HTMLCompanyExtractor

logger = structlog.get_logger(__name__)


class LLMParser:
    """Parser that uses LLM to extract company data from HTML"""
    
    def __init__(self):
        """Initialize LLM parser with company extractor"""
        self.extractor = HTMLCompanyExtractor()
        
        # Check if Ollama is available on init
        if not self.extractor.check_ollama_available():
            logger.warning(
                "Ollama not available - LLM parsing will fail",
                hint="Start Ollama: 'ollama serve' and pull model: 'ollama pull gemma2:2b'"
            )
    
    def extract_companies(
        self,
        html: str,
        query_context: str = "",
        limit: int = 50
    ) -> List[Dict]:
        """
        Extract company information from HTML using LLM
        
        Args:
            html: Raw HTML content from any website
            query_context: Search context (e.g., "Miami Florida real estate")
            limit: Maximum number of companies to extract
            
        Returns:
            List of company dictionaries with standardized fields:
            - name: Company/agency name
            - website_url: Company website (if available)
            - source: Where the data came from
        """
        logger.info(
            "Starting LLM-based company extraction",
            query_context=query_context,
            html_length=len(html)
        )
        
        try:
            companies = self.extractor.extract_companies(
                html_content=html,
                query_context=query_context,
                limit=limit
            )
            
            # Post-process and validate
            validated_companies = []
            for company in companies:
                if self._is_valid_company(company):
                    validated_companies.append(self._normalize_company(company))
            
            logger.info(
                f"LLM extraction completed",
                extracted=len(companies),
                validated=len(validated_companies)
            )
            
            return validated_companies
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}", exc_info=True)
            return []
    
    def _is_valid_company(self, company: Dict) -> bool:
        """
        Validate that company data meets minimum requirements
        
        Args:
            company: Company dictionary
            
        Returns:
            True if valid, False otherwise
        """
        # Must have a name
        if not company.get("name"):
            return False
        
        name = company["name"].strip()
        
        # Name must be reasonable length
        if len(name) < 3 or len(name) > 200:
            return False
        
        # Skip generic terms
        generic_terms = [
            "search results",
            "click here",
            "learn more",
            "read more",
            "view all",
            "see all",
            "advertisement",
            "sponsored",
            "loading"
        ]
        
        name_lower = name.lower()
        for term in generic_terms:
            if term in name_lower:
                return False
        
        return True
    
    def _normalize_company(self, company: Dict) -> Dict:
        """
        Normalize company data to standard format
        
        Args:
            company: Raw company dictionary from LLM
            
        Returns:
            Normalized company dictionary
        """
        # Ensure required fields
        normalized = {
            "name": company.get("name", "").strip(),
            "website_url": company.get("website_url") or company.get("url"),
            "source": company.get("source", "llm_extraction")
        }
        
        # Clean website URL
        if normalized["website_url"]:
            url = normalized["website_url"].strip()
            # Ensure http/https
            if url and not url.startswith(("http://", "https://")):
                url = "https://" + url
            normalized["website_url"] = url
        
        # Add optional fields if present
        optional_fields = [
            "phone",
            "address", 
            "description",
            "rating",
            "reviews_count"
        ]
        
        for field in optional_fields:
            if field in company and company[field]:
                normalized[field] = company[field]
        
        return normalized
