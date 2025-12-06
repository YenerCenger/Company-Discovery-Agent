import asyncio
import time
import random
from typing import Optional
from pathlib import Path
import json
import structlog
from config.settings import settings

logger = structlog.get_logger(__name__)


class Crawl4AIHandler:
    """Wrapper for crawl4ai AsyncWebCrawler with rate limiting and caching"""

    def __init__(self):
        self.delay_ms = settings.CRAWL4AI_DELAY_MS
        self.timeout = settings.CRAWL4AI_TIMEOUT
        self.user_agents = settings.CRAWL4AI_USER_AGENTS.split(",")
        self.cache_enabled = settings.CRAWL4AI_CACHE_ENABLED
        self.cache_expiry_hours = settings.CRAWL4AI_CACHE_EXPIRY_HOURS
        self.cache_dir = Path(__file__).parent.parent / "data" / "crawl_cache"
        self.last_request_time = 0

        # Create cache directory
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _apply_rate_limiting(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        delay_seconds = self.delay_ms / 1000.0

        if elapsed < delay_seconds:
            sleep_time = delay_seconds - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for a URL"""
        # Simple hash of URL for filename
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    def _get_cached_result(self, url: str) -> Optional[str]:
        """Get cached HTML if available and not expired"""
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(url)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check expiry
            cached_time = cache_data.get("timestamp", 0)
            expiry_seconds = self.cache_expiry_hours * 3600
            if time.time() - cached_time > expiry_seconds:
                logger.debug(f"Cache expired for {url}")
                return None

            logger.info(f"Cache hit for {url}")
            return cache_data.get("html")

        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None

    def _save_to_cache(self, url: str, html: str):
        """Save HTML to cache"""
        if not self.cache_enabled:
            return

        try:
            cache_path = self._get_cache_path(url)
            cache_data = {
                "url": url,
                "timestamp": time.time(),
                "html": html
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)

            logger.debug(f"Saved to cache: {url}")

        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the list"""
        return random.choice(self.user_agents).strip()

    async def _crawl_async(self, url: str) -> str:
        """Async crawl using crawl4ai"""
        from crawl4ai import AsyncWebCrawler

        # Apply rate limiting
        self._apply_rate_limiting()

        # Check cache first
        cached_html = self._get_cached_result(url)
        if cached_html:
            return cached_html

        logger.info(f"Crawling URL: {url}")

        try:
            async with AsyncWebCrawler(
                headless=True,
                verbose=False
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                    page_timeout=self.timeout * 1000,  # Convert to milliseconds
                    user_agent=self._get_random_user_agent()
                )

                if not result.success:
                    logger.error(f"Crawl failed for {url}: {result.error_message}")
                    return ""

                html = result.html

                # Save to cache
                self._save_to_cache(url, html)

                return html

        except Exception as e:
            logger.error(f"Crawl error for {url}: {e}", exc_info=True)
            return ""

    def crawl_sync(self, url: str) -> str:
        """
        Synchronous wrapper for async crawl

        Args:
            url: URL to crawl

        Returns:
            HTML content as string
        """
        try:
            return asyncio.run(self._crawl_async(url))
        except Exception as e:
            logger.error(f"Sync crawl error: {e}", exc_info=True)
            return ""
