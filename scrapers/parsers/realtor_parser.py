from typing import List, Dict
from bs4 import BeautifulSoup
import structlog
import re

logger = structlog.get_logger(__name__)


class RealtorParser:
    """Parser for Realtor.com real estate agent pages"""

    def extract_companies(self, html: str, limit: int = 50) -> List[Dict]:
        """
        Extract company information from Realtor.com HTML

        Args:
            html: HTML content from Realtor.com
            limit: Maximum number of companies to extract

        Returns:
            List of company dictionaries
        """
        companies = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Try multiple CSS selectors (Realtor.com structure varies)
            agent_cards = soup.select('.agent-list-card')
            if not agent_cards:
                agent_cards = soup.select('[data-testid="agent-card"]')
            if not agent_cards:
                agent_cards = soup.select('.AgentCard')

            logger.info(f"Found {len(agent_cards)} agent cards on page")

            for idx, card in enumerate(agent_cards[:limit]):
                try:
                    company_data = self._parse_agent_card(card, idx + 1)
                    if company_data:
                        companies.append(company_data)
                except Exception as e:
                    logger.warning(f"Failed to parse agent card {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse Realtor.com HTML: {e}", exc_info=True)

        logger.info(f"Extracted {len(companies)} companies from Realtor.com")
        return companies

    def _parse_agent_card(self, card, position: int) -> Dict:
        """Parse a single agent card"""
        try:
            # Extract name
            name_elem = card.select_one('.agent-name, [data-testid="agent-name"], h3, .AgentCard__Name')
            name = name_elem.get_text(strip=True) if name_elem else None

            # Extract URL (profile or website)
            url_elem = card.select_one('a[href*="realtor.com"], a[href*="http"]')
            website_url = url_elem['href'] if url_elem and 'href' in url_elem.attrs else None

            # Extract company/brokerage
            company_elem = card.select_one('.agent-company, [data-testid="brokerage"], .AgentCard__Brokerage')
            company_name = company_elem.get_text(strip=True) if company_elem else name

            # Extract phone
            phone_elem = card.select_one('.agent-phone, [data-testid="phone"], [href^="tel:"]')
            phone = None
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True) if phone_elem.get_text() else phone_elem.get('href', '')
                phone = self._extract_phone(phone_text)

            # Extract address
            address_elem = card.select_one('.agent-address, [data-testid="address"], .AgentCard__Address')
            address = address_elem.get_text(strip=True) if address_elem else None

            # Extract description/bio
            desc_elem = card.select_one('.agent-bio, .agent-description, p')
            description = desc_elem.get_text(strip=True) if desc_elem else None

            if not company_name:
                return None

            return {
                "name": company_name,
                "website_url": website_url or f"https://www.realtor.com/agent/{company_name.lower().replace(' ', '-')}",
                "source": "realtor.com",
                "search_position": position,
                "has_social_media": False,  # Unknown from listing page
                "address": address,
                "phone": phone,
                "email": None,  # Typically not shown on listing pages
                "description": description
            }

        except Exception as e:
            logger.warning(f"Failed to parse agent card: {e}")
            return None

    def _extract_phone(self, text: str) -> str:
        """Extract phone number from text"""
        # Remove "tel:" prefix if present
        text = text.replace('tel:', '')

        # Match US phone patterns
        phone_pattern = r'\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        match = re.search(phone_pattern, text)

        if match:
            return match.group(0).strip()

        return None
