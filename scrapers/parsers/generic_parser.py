from typing import List, Dict
from bs4 import BeautifulSoup
import structlog
import re

logger = structlog.get_logger(__name__)


class GenericParser:
    """Generic parser for any business directory or search results"""

    def extract_companies(self, html: str, limit: int = 50) -> List[Dict]:
        """
        Extract company information from generic HTML (Google, Yelp, etc.)

        Args:
            html: HTML content
            limit: Maximum number of companies to extract

        Returns:
            List of company dictionaries
        """
        companies = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Try multiple generic selectors for search results
            result_containers = []

            # Google search results
            result_containers.extend(soup.select('.g'))  # Google result container
            result_containers.extend(soup.select('[data-sokoban-container]'))  # Google newer format
            result_containers.extend(soup.select('.result'))  # Generic results
            result_containers.extend(soup.select('.search-result'))

            # Yelp patterns
            result_containers.extend(soup.select('[class*="businessName"]'))
            result_containers.extend(soup.select('.business-card'))

            # Generic listings
            result_containers.extend(soup.select('article'))
            result_containers.extend(soup.select('[role="listitem"]'))

            logger.info(f"Found {len(result_containers)} potential result containers")

            for idx, container in enumerate(result_containers[:limit]):
                try:
                    company_data = self._parse_result(container, idx + 1)
                    if company_data and self._is_valid_company(company_data):
                        companies.append(company_data)
                except Exception as e:
                    logger.debug(f"Failed to parse result {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse generic HTML: {e}", exc_info=True)

        logger.info(f"Extracted {len(companies)} companies from generic page")
        return companies

    def _parse_result(self, container, position: int) -> Dict:
        """Parse a single search result container"""
        try:
            # Extract name (try multiple patterns)
            name = None
            for selector in ['h2', 'h3', 'h4', '[class*="title"]', '[class*="name"]', 'a']:
                name_elem = container.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if name and len(name) > 5:  # Reasonable company name length
                        break

            if not name:
                return None

            # Extract URL
            website_url = None
            for link in container.select('a[href]'):
                href = link.get('href', '')
                if href and ('http' in href or href.startswith('/')):
                    # Skip Google internal links
                    if 'google.com' not in href and 'webcache' not in href:
                        website_url = href
                        break

            # Extract description/snippet
            description = None
            for selector in ['p', '.description', '[class*="snippet"]', '.text']:
                desc_elem = container.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if description and len(description) > 20:
                        break

            # Extract contact info from all text
            all_text = container.get_text()

            phone = self._extract_phone(all_text)
            email = self._extract_email(all_text)
            address = self._extract_address(all_text)

            return {
                "name": name,
                "website_url": website_url or f"http://search-result-{position}.com",
                "source": "generic_search",
                "search_position": position,
                "has_social_media": False,
                "address": address,
                "phone": phone,
                "email": email,
                "description": description
            }

        except Exception as e:
            logger.debug(f"Failed to parse result container: {e}")
            return None

    def _is_valid_company(self, company_data: Dict) -> bool:
        """Validate company data has minimum required fields"""
        if not company_data.get("name"):
            return False

        # Must have at least one form of contact
        has_contact = any([
            company_data.get("website_url"),
            company_data.get("phone"),
            company_data.get("email"),
            company_data.get("address")
        ])

        return has_contact

    def _extract_phone(self, text: str) -> str:
        """Extract phone number from text"""
        # US phone pattern
        phone_pattern = r'\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        match = re.search(phone_pattern, text)

        if match:
            return match.group(0).strip()

        return None

    def _extract_email(self, text: str) -> str:
        """Extract email from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)

        if match:
            return match.group(0).strip()

        return None

    def _extract_address(self, text: str) -> str:
        """Extract address from text (basic pattern)"""
        # Look for patterns like "123 Street Name, City, ST 12345"
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)[,\s]+[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}'
        match = re.search(address_pattern, text)

        if match:
            return match.group(0).strip()

        return None
