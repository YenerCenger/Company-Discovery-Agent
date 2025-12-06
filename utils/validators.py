import validators
from typing import Optional
from database.models import PlatformEnum


def validate_url(url: str) -> bool:
    """
    Validate if a string is a valid URL

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    result = validators.url(url)
    return result is True


def validate_platform(platform: str) -> bool:
    """
    Validate if a platform is supported

    Args:
        platform: Platform name to validate

    Returns:
        True if platform is supported, False otherwise
    """
    try:
        return platform in [p.value for p in PlatformEnum]
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    import re
    # Remove invalid characters for Windows/Unix filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    return sanitized or "unnamed"


def validate_email(email: str) -> bool:
    """
    Validate if a string is a valid email address

    Args:
        email: Email string to validate

    Returns:
        True if valid email, False otherwise
    """
    result = validators.email(email)
    return result is True
