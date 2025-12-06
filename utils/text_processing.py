import re
from typing import List


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for deduplication

    Removes common suffixes, converts to lowercase, removes extra whitespace

    Args:
        name: Original company name

    Returns:
        Normalized company name

    Examples:
        "Luxury Homes LLC" -> "luxury homes"
        "ABC Real Estate, Inc." -> "abc real estate"
    """
    # Convert to lowercase
    normalized = name.lower()

    # Remove common company suffixes
    suffixes = [
        r'\b(llc|inc|ltd|corporation|corp|company|co|group|gmbh|limited)\b\.?',
        r'\b(plc|lp|llp|sa|ag|nv|bv)\b\.?'
    ]
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized)

    # Remove special characters except spaces
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)

    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def extract_domain_from_url(url: str) -> str:
    """
    Extract domain from URL

    Args:
        url: Full URL

    Returns:
        Domain name without protocol or path

    Examples:
        "https://www.example.com/path" -> "example.com"
        "http://subdomain.example.co.uk" -> "subdomain.example.co.uk"
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path

    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters

    Args:
        text: Original text

    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Original text
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def extract_keywords(text: str) -> List[str]:
    """
    Extract potential keywords from text

    Args:
        text: Source text

    Returns:
        List of extracted keywords
    """
    # Convert to lowercase
    text = text.lower()

    # Remove special characters
    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    # Split into words
    words = text.split()

    # Filter short words and common stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    keywords = [word for word in words if len(word) > 3 and word not in stopwords]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords
