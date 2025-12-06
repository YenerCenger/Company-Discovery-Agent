import re
from typing import Optional, Dict
import structlog

logger = structlog.get_logger(__name__)


class ContactExtractor:
    """Extract contact information (phone, email, address) from text"""

    # Regex patterns
    PHONE_PATTERN = re.compile(r'\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    ADDRESS_PATTERN = re.compile(
        r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)[,\s]+'
        r'[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}'
    )

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """
        Extract phone number from text

        Args:
            text: Text to search

        Returns:
            Phone number or None
        """
        if not text:
            return None

        match = cls.PHONE_PATTERN.search(text)
        if match:
            phone = match.group(0).strip()
            # Normalize format
            return cls._normalize_phone(phone)

        return None

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        """
        Extract email address from text

        Args:
            text: Text to search

        Returns:
            Email address or None
        """
        if not text:
            return None

        match = cls.EMAIL_PATTERN.search(text)
        if match:
            return match.group(0).strip().lower()

        return None

    @classmethod
    def extract_address(cls, text: str) -> Optional[str]:
        """
        Extract street address from text

        Args:
            text: Text to search

        Returns:
            Address or None
        """
        if not text:
            return None

        match = cls.ADDRESS_PATTERN.search(text)
        if match:
            return match.group(0).strip()

        return None

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, Optional[str]]:
        """
        Extract all contact information from text

        Args:
            text: Text to search

        Returns:
            Dictionary with phone, email, address
        """
        return {
            "phone": cls.extract_phone(text),
            "email": cls.extract_email(text),
            "address": cls.extract_address(text)
        }

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number format"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        # Format as (XXX) XXX-XXXX
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone  # Return original if can't normalize
