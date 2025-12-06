class RealEstateIntelError(Exception):
    """Base exception for the Real Estate Intelligence application"""
    pass


class ScraperError(RealEstateIntelError):
    """Scraping-related errors"""
    pass


class DatabaseError(RealEstateIntelError):
    """Database operation errors"""
    pass


class VideoDownloadError(RealEstateIntelError):
    """Video download errors"""
    pass


class ValidationError(RealEstateIntelError):
    """Data validation errors"""
    pass
