from pathlib import Path
from typing import Optional, Dict, List
from scrapers.social.base import BaseSocialScraper
from config.settings import settings
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class InstagramScraper(BaseSocialScraper):
    """Instagram scraper with real instaloader support"""

    def __init__(self):
        super().__init__()
        self.session_file = settings.INSTAGRAM_SESSION_FILE

    def _get_platform_name(self) -> str:
        return "instagram"

    def _get_authenticated_loader(self, force_relogin: bool = False):
        """Get Instaloader instance with authentication"""
        import instaloader

        L = instaloader.Instaloader()

        # If force_relogin, delete old session first
        if force_relogin and self.session_file.exists():
            try:
                self.session_file.unlink()
                logger.info("Deleted old session file for re-login")
            except Exception as e:
                logger.warning(f"Failed to delete old session: {e}")

        # Try to load existing session
        if self.session_file.exists() and not force_relogin:
            try:
                L.load_session_from_file(
                    settings.INSTAGRAM_USERNAME,
                    str(self.session_file)
                )
                logger.info("Loaded Instagram session from file")
                return L
            except Exception as e:
                logger.warning(f"Failed to load session: {e}, will try to re-login")
                # Delete invalid session file
                try:
                    self.session_file.unlink()
                except:
                    pass

        # Login with credentials
        if settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD:
            try:
                L.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
                # Create data directory if not exists
                self.session_file.parent.mkdir(parents=True, exist_ok=True)
                L.save_session_to_file(str(self.session_file))
                logger.info("Instagram login successful, session saved")
                return L
            except Exception as e:
                error_msg = str(e)
                # Check for checkpoint error
                if "Checkpoint required" in error_msg or "checkpoint" in error_msg.lower():
                    logger.warning(
                        "Instagram checkpoint required. Please:",
                        hint="1. Open the checkpoint URL in browser, 2. Complete verification, 3. Try again"
                    )
                    # Extract checkpoint URL if available
                    if "https://" in error_msg:
                        import re
                        url_match = re.search(r'https://[^\s]+', error_msg)
                        if url_match:
                            checkpoint_url = url_match.group(0)
                            logger.warning(f"Checkpoint URL: {checkpoint_url}")
                else:
                    logger.error(f"Instagram login failed: {e}")
                # Don't raise, fall back to public access

        # Fall back to non-authenticated
        logger.warning("No Instagram credentials, using public access")
        return L

    def _search_duckduckgo_for_instagram(self, company_name: str, limit: int = 5) -> List[str]:
        """
        Search DuckDuckGo for Instagram profiles using crawl4ai (headless browser)
        DuckDuckGo doesn't have cookie consent popups like Google
        
        Strategy: Search "company_name instagram" to find Instagram profiles
        
        Args:
            company_name: Company name
            limit: Maximum number of results to return
            
        Returns:
            List of Instagram profile URLs found via DuckDuckGo
        """
        import time
        import random
        import re
        
        # Clean company name - remove Turkish characters
        def clean_turkish_chars(text: str) -> str:
            replacements = {
                'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S',
                'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U',
                'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
            }
            for tr, en in replacements.items():
                text = text.replace(tr, en)
            return text
        
        company_clean = clean_turkish_chars(company_name)
        
        # DuckDuckGo search URL - no cookie consent!
        search_query = f'{company_clean} instagram'
        ddg_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
        
        logger.info(f"Searching DuckDuckGo for Instagram profiles", company_name=company_name, url=ddg_url)
        
        try:
            # requests ile DuckDuckGo'yu aç (crawl4ai engelleniyordu)
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            response = requests.get(ddg_url, headers=headers, timeout=15)
            response.raise_for_status()
            response_text = response.text
            
            if not response_text:
                logger.warning("Empty HTML from DuckDuckGo")
                return []
            
            logger.info(f"DuckDuckGo HTML received: {len(response_text)} chars")
            
            # DEBUG: HTML'i dosyaya kaydet (ilk 50000 karakter)
            try:
                debug_file = Path(__file__).parent.parent / "data" / "google_debug.html"
                debug_file.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response_text[:50000])
                logger.info(f"DuckDuckGo HTML saved to {debug_file}")
            except Exception as e:
                logger.debug(f"Could not save debug HTML: {e}")
            
            # Parse HTML - Basit yaklaşım: Regex ile direkt Instagram linklerini bul
            from bs4 import BeautifulSoup
            
            instagram_profiles = []
            seen_usernames = set()
            
            # Strategy 1: Daha esnek regex - URL encoded ve normal linkleri bul
            # Google'da linkler şu formatlarda olabilir:
            # - instagram.com/username
            # - www.instagram.com/username  
            # - https://instagram.com/username
            # - https%3A%2F%2Finstagram.com%2Fusername (URL encoded)
            
            # Önce URL decode yap
            import urllib.parse
            decoded_html = urllib.parse.unquote(response_text)
            
            # Daha esnek pattern - sadece instagram.com/ sonrasındaki username'i al
            instagram_pattern = r'(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)'
            matches = re.findall(instagram_pattern, decoded_html, re.IGNORECASE)
            
            # DEBUG: Kaç match bulundu
            logger.info(f"Regex found {len(matches)} potential usernames in DuckDuckGo HTML")
            
            for username in matches:
                # Sistem sayfalarını skip et
                invalid = ['www', 'accounts', 'explore', 'direct', 'about', 'blog', 'developers', 'popular', 'help', 'legal', 'stories', 'reels', 'tv', 'p', 'reel', 'tags', 'locations']
                if username.lower() not in invalid and username.lower() not in seen_usernames:
                    seen_usernames.add(username.lower())
                    url = f"https://instagram.com/{username}"
                    instagram_profiles.append({
                        "url": url,
                        "username": username,
                        "position": len(instagram_profiles) + 1
                    })
                    logger.debug(f"Found Instagram profile via regex: @{username}")
                    if len(instagram_profiles) >= limit:
                        break
            
            # Strategy 2: BeautifulSoup ile link extraction (fallback)
            if not instagram_profiles:
                logger.debug("Regex found nothing, trying BeautifulSoup")
                soup = BeautifulSoup(response_text, 'html.parser')
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    href = link.get('href', '')
                    
                    # Skip ads ve Google'ın kendi linkleri
                    if any(x in href for x in ['googleadservices.com', 'doubleclick.net', 'google.com/search', 'google.com/url']):
                        continue
                    
                    # Instagram linki mi?
                    if 'instagram.com' in href:
                        # Post/reel değil, profil olmalı
                        if any(x in href for x in ['/p/', '/reel/', '/tv/', '/stories/', '/explore/', '/accounts/']):
                            continue
                        
                        # URL'yi temizle - Google'ın redirect URL'lerini handle et
                        import urllib.parse
                        
                        if href.startswith('/url?q='):
                            href = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
                        elif href.startswith('/url?'):
                            # Google'ın redirect URL'i
                            try:
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                if 'q' in parsed:
                                    href = urllib.parse.unquote(parsed['q'][0])
                            except:
                                pass
                        
                        # URL decode
                        try:
                            href = urllib.parse.unquote(href)
                        except:
                            pass
                        
                        # Username çıkar
                        username = None
                        if 'instagram.com/' in href:
                            # instagram.com/username veya instagram.com/@username
                            parts = href.split('instagram.com/')
                            if len(parts) > 1:
                                username = parts[1].split('/')[0].split('?')[0].split('#')[0]
                                if username.startswith('@'):
                                    username = username[1:]
                        
                        # Geçerli username mi?
                        if username and len(username) > 0:
                            # Sistem sayfalarını skip et
                            invalid = ['www', 'accounts', 'explore', 'direct', 'about', 'blog', 'developers', 'popular', 'help', 'legal', 'stories', 'reels', 'tv', 'p', 'reel', 'tags', 'locations']
                            if username.lower() not in invalid:
                                if username.lower() not in seen_usernames:
                                    seen_usernames.add(username.lower())
                                    url = f"https://instagram.com/{username}"
                                    instagram_profiles.append({
                                        "url": url,
                                        "username": username,
                                        "position": len(instagram_profiles) + 1  # İlk bulunan = en üstte
                                    })
                                    logger.debug(f"Found Instagram profile: @{username} (position: {len(instagram_profiles)})")
                                    
                                    # İlk birkaç sonuç yeterli (Google'ın en üstteki sonuçları)
                                    if len(instagram_profiles) >= limit:
                                        break
            
            # Sort by position (Google's ranking - first results are usually best)
            instagram_profiles.sort(key=lambda x: x["position"])
            
            # Limit to first N results (Google's top results are usually the best)
            instagram_profiles = instagram_profiles[:limit]
            
            # Return just URLs for now (we'll check followers later)
            instagram_urls = [p["url"] for p in instagram_profiles]
            
            # Bulunan profilleri logla
            if instagram_profiles:
                usernames = [f"@{p['username']}" for p in instagram_profiles]
                logger.info(
                    f"🔍 DuckDuckGo found {len(instagram_urls)} Instagram profiles: {', '.join(usernames)}"
                )
            else:
                logger.info(f"DuckDuckGo found 0 Instagram profiles")
            
            # Debug: Eğer hiç bulamadıysak HTML'in bir kısmını logla
            if not instagram_urls:
                logger.debug(f"DuckDuckGo HTML length: {len(response_text)} chars")
                # Instagram kelimesi var mı kontrol et
                if 'instagram' in response_text.lower():
                    logger.debug("'instagram' found in DuckDuckGo HTML but couldn't extract profiles")
                else:
                    logger.debug("'instagram' NOT found in DuckDuckGo HTML")
            
            return instagram_urls
            
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
            return []

    def _try_common_usernames(self, company_name: str, limit: int = 5) -> List[Dict]:
        """
        Try common username patterns and return found profiles
        Uses Google Dorking first, then falls back to direct username checks
        
        Args:
            company_name: Company name
            limit: Maximum number of profiles to return
            
        Returns:
            List of profile dictionaries with username and followers_count
        """
        import instaloader
        import time
        import random
        
        L = self._get_authenticated_loader()
        
        found_profiles = []
        
        # Strategy 1: Google Dorking (safer, avoids bot detection)
        # Google'ın ilk sonuçları genelde en büyük/doğru firmalar oluyor
        google_urls = self._search_duckduckgo_for_instagram(company_name, limit=limit)
        
        if google_urls:
            logger.info(f"Checking {len(google_urls)} profiles found via Google (top results are usually best)")
            for i, url in enumerate(google_urls, 1):
                try:
                    # Extract username from URL
                    username = url.split('instagram.com/')[-1].split('/')[0].split('?')[0]

                    # Random delay between requests (longer delays to avoid rate limiting)
                    delay = random.uniform(5, 8)  # 5-8 saniye arası bekle
                    if i > 1:  # İlk istekten sonra bekle
                        time.sleep(delay)

                    try:
                        profile = instaloader.Profile.from_username(L.context, username)
                        found_profiles.append({
                            "username": profile.username,
                            "followers": profile.followers,
                            "profile": profile,
                            "source": "google",
                            "google_position": i  # Google'daki sıralama
                        })
                        logger.info(
                            f"Found profile via Google (position {i}): @{username} ({profile.followers:,} followers)"
                        )
                    except (instaloader.exceptions.LoginRequiredException, instaloader.exceptions.QueryReturnedBadRequestException):
                        # Session yoksa veya 401 hatası alırsa, follower bilgisi olmadan ekle
                        logger.warning(f"Could not fetch full profile for @{username} (login required), using basic info")
                        # Mock profile objesi oluştur (minimal bilgi ile)
                        class MockProfile:
                            def __init__(self, uname):
                                self.username = uname
                                self.followers = 0  # Bilinmiyor
                                self.mediacount = 0
                                self.biography = ""

                        mock_profile = MockProfile(username)
                        found_profiles.append({
                            "username": username,
                            "followers": 0,  # Follower sayısını bilemiyoruz
                            "profile": mock_profile,
                            "source": "google",
                            "google_position": i
                        })
                        logger.info(f"Added profile without follower count: @{username} (position {i})")
                    
                    # Google'ın ilk 2-3 sonucu genelde en iyisi, onları kontrol et yeter
                    # Ama limit'e kadar devam et
                    if len(found_profiles) >= limit:
                        break
                        
                except instaloader.exceptions.ProfileNotExistsException:
                    logger.debug(f"Profile @{username} not found (from Google result)")
                    continue
                except Exception as e:
                    logger.debug(f"Error checking {username}: {e}")
                    continue
        
        # Strategy 2: Fallback to common username patterns (ONLY if Google found nothing)
        if len(found_profiles) == 0:
            logger.info("Trying common username patterns as fallback")
            
            # Türkçe karakterleri temizle - Instagram username'lerde Türkçe karakter yok
            def clean_turkish(text: str) -> str:
                replacements = {
                    'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S',
                    'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U',
                    'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
                }
                for tr, en in replacements.items():
                    text = text.replace(tr, en)
                return text
            
            # Clean company name
            name_clean = clean_turkish(company_name.lower().strip())
            name_clean = name_clean.replace(" real estate", "").replace(" properties", "")
            name_clean = name_clean.replace(" group", "").replace(" company", "")
            name_clean = name_clean.replace(" inc", "").replace(" ltd", "").replace(" llc", "")
            name_clean = name_clean.replace(" yapi", "").replace(" insaat", "")  # Türkçe kelimeler
            
            # Generate simple variations
            base = name_clean.replace(" ", "").replace("&", "").replace(".", "").replace(",", "")
            base = base.replace("-", "").replace("_", "").replace("'", "").replace('"', "")
            
            if base and len(base) >= 3:
                # Ana firma adı ve varyasyonları
                usernames_to_try = [
                    base,  # folkart
                    f"{base}yapi",  # folkartyapi (yapı şirketleri için)
                    f"{base}_yapi",  # folkart_yapi
                    f"{base}insaat",  # folkartinsaat
                    f"{base}_insaat",  # folkart_insaat
                    f"{base}official",  # folkartofficial
                    f"{base}_official",  # folkart_official
                ]
                
                logger.info(f"Trying usernames: {usernames_to_try[:5]}")
                
                if " " in name_clean:
                    parts = [p.replace(" ", "").replace("-", "") for p in name_clean.split() if p]
                    if len(parts) > 1:
                        usernames_to_try.extend(["_".join(parts)])
                
                for username in usernames_to_try[:3]:  # Limit to 3 more attempts
                    if len(found_profiles) >= limit:
                        break
                    
                    # Skip if already found
                    if any(p["username"] == username for p in found_profiles):
                        continue
                    
                    try:
                        # Random delay
                        time.sleep(random.uniform(3, 6))
                        
                        profile = instaloader.Profile.from_username(L.context, username)
                        found_profiles.append({
                            "username": profile.username,
                            "followers": profile.followers,
                            "profile": profile
                        })
                        logger.debug(f"Found profile: @{username} ({profile.followers:,} followers)")
                    except instaloader.exceptions.ProfileNotExistsException:
                        continue
                    except Exception as e:
                        logger.debug(f"Error checking {username}: {e}")
                        continue
        
        return found_profiles

    def _generate_username_variations(self, company_name: str) -> List[str]:
        """
        Generate possible Instagram username variations from company name
        
        Args:
            company_name: Company name
            
        Returns:
            List of possible username variations
        """
        variations = []
        name_lower = company_name.lower().strip()
        
        # Remove common words
        name_clean = name_lower.replace(" real estate", "").replace(" properties", "")
        name_clean = name_clean.replace(" group", "").replace(" company", "")
        name_clean = name_clean.replace(" inc", "").replace(" ltd", "")
        name_clean = name_clean.replace(" llc", "").replace(" corp", "")
        
        # Basic cleaning
        base = name_clean.replace(" ", "").replace("&", "").replace(".", "").replace(",", "")
        base = base.replace("-", "").replace("_", "").replace("'", "").replace('"', "")
        
        if not base:
            return variations
        
        # Variation 1: Direct (no spaces, no special chars)
        variations.append(base)
        
        # Variation 2-4: With separator (if has multiple words)
        parts = [p.replace(" ", "").replace("-", "").replace(".", "") for p in name_clean.split() if p]
        if len(parts) > 1:
            variations.append("_".join(parts))  # With underscore
            variations.append(".".join(parts))    # With dot
            variations.append("-".join(parts))    # With dash
        
        # Variation 5: Official suffix
        variations.append(f"{base}official")
        variations.append(f"{base}_official")
        
        # Variation 6: Country/region suffix (common)
        variations.append(f"{base}_tr")  # Turkey
        variations.append(f"{base}_usa")  # USA
        variations.append(f"{base}_uk")  # UK
        
        # Variation 7: Resmi/official in Turkish
        if any(x in name_lower for x in ["türk", "turkey", "istanbul", "ankara"]):
            variations.append(f"{base}resmi")
            variations.append(f"{base}_resmi")
        
        # Remove duplicates and empty strings
        variations = list(dict.fromkeys([v for v in variations if v and len(v) >= 3]))
        
        # Limit to first 10 variations to avoid too many requests
        return variations[:10]

    # Real implementations using instaloader
    def _find_profile_real(self, company_name: str, website_url: str = None) -> Optional[Dict]:
        """
        Real Instagram profile search using Instagram's search API
        
        Strategy:
        1. Search Instagram with company name directly
        2. Get first 5 results
        3. Select profile with highest follower count
        
        Args:
            company_name: Company name
            website_url: Company website URL (optional, not used yet)
            
        Returns:
            Profile data dictionary or None if not found
        """
        try:
            import instaloader

            L = self._get_authenticated_loader()

            logger.info(f"Searching Instagram for profile", company_name=company_name)

            # Try common username patterns
            found_profiles = self._try_common_usernames(company_name, limit=5)
            
            if not found_profiles:
                logger.warning(f"No Instagram profiles found", company_name=company_name)
                return None

            # Sort by follower count (highest first)
            # We want the most popular profile for the company
            found_profiles.sort(key=lambda x: -x["followers"])

            # Get the profile with highest follower count
            best_match = found_profiles[0]
            profile = best_match["profile"]

            logger.info(
                f"Considered {len(found_profiles)} profiles, selected highest follower count",
                company_name=company_name,
                profiles=[f"@{p['profile'].username} ({p['followers']:,})" for p in found_profiles[:5]]
            )
            
            logger.info(
                f"✅ Selected Instagram profile: @{profile.username} ({profile.followers:,} followers)",
                company_name=company_name
            )

            return {
                "username": profile.username,
                "profile_url": f"https://instagram.com/{profile.username}",
                "followers_count": profile.followers,
                "posts_count": profile.mediacount,
                "bio": profile.biography,
                "avg_likes": self._calculate_avg_likes(profile),
                "avg_comments": self._calculate_avg_comments(profile),
                "posts_per_week": self._calculate_posting_frequency(profile),
                "video_ratio": self._calculate_video_ratio(profile)
            }

        except ImportError:
            logger.error("instaloader not installed. Install with: pip install instaloader")
            raise NotImplementedError("instaloader not installed. Use mock data with USE_MOCK_SCRAPERS=true")
        except Exception as e:
            logger.error(f"Error finding Instagram profile", error=str(e), exc_info=True)
            return None

    def _get_recent_posts_real(self, profile_url: str, limit: int) -> List[Dict]:
        """
        Real Instagram posts fetching using instaloader

        Fetches recent posts/reels from an Instagram profile
        """
        try:
            import instaloader

            L = self._get_authenticated_loader()

            # Extract username from profile URL
            username = profile_url.split("/")[-1] if "/" in profile_url else profile_url
            username = username.strip("/")

            logger.info(f"Fetching Instagram posts", username=username, limit=limit)

            try:
                profile = instaloader.Profile.from_username(L.context, username)
            except instaloader.exceptions.ConnectionException as e:
                error_str = str(e)
                
                # Check for rate limiting
                if "Please wait a few minutes" in error_str or "rate limit" in error_str.lower():
                    logger.warning(
                        "Instagram rate limit reached",
                        username=username,
                        hint="Please wait a few minutes before trying again"
                    )
                    return []
                
                # Handle 401 Unauthorized - session expired (but not rate limit)
                if "401" in error_str or "Unauthorized" in error_str:
                    if "Please wait" not in error_str:
                        logger.warning(
                            "Instagram session expired (401), attempting to re-login",
                            username=username
                        )
                        try:
                            L = self._get_authenticated_loader(force_relogin=True)
                            profile = instaloader.Profile.from_username(L.context, username)
                        except Exception as retry_error:
                            retry_error_str = str(retry_error)
                            if "Please wait" in retry_error_str:
                                logger.warning(
                                    "Rate limited after re-login",
                                    username=username,
                                    hint="Please wait a few minutes"
                                )
                            else:
                                logger.error(
                                    "Re-login failed",
                                    username=username,
                                    error=retry_error_str
                                )
                            return []
                    else:
                        logger.warning(
                            "Instagram rate limit (401)",
                            username=username,
                            hint="Please wait a few minutes"
                        )
                        return []
                else:
                    logger.error(f"Instagram connection error: {e}")
                    return []

            posts = []
            count = 0
            error_count = 0
            max_errors = 3  # Maximum consecutive errors before giving up

            try:
                for post in profile.get_posts():
                    try:
                        if count >= limit:
                            break

                        # Only get video posts (reels, videos, IGTV)
                        if not post.is_video:
                            continue

                        posts.append({
                            "external_post_id": post.shortcode,
                            "post_url": f"https://instagram.com/p/{post.shortcode}",
                            "post_type": "reel" if post.typename == "GraphVideo" else "video",
                            "caption_text": post.caption if post.caption else "",
                            "published_at": post.date_utc.isoformat() + "Z",
                            "like_count": post.likes,
                            "comment_count": post.comments,
                            "view_count": post.video_view_count if post.is_video else 0,
                            "saved_count": 0  # Not available via instaloader
                        })

                        count += 1
                        error_count = 0  # Reset error count on success

                    except (KeyError, AttributeError) as e:
                        # Handle individual post errors
                        error_count += 1
                        logger.warning(
                            f"Error processing post {count + 1}",
                            username=username,
                            error=str(e),
                            error_count=error_count
                        )
                        if error_count >= max_errors:
                            logger.warning(
                                f"Too many consecutive errors, stopping post fetch",
                                username=username,
                                posts_found=len(posts)
                            )
                            break
                        continue

            except (KeyError, instaloader.exceptions.ConnectionException) as e:
                # Handle API/data format errors
                logger.warning(
                    f"Instagram API error while fetching posts",
                    username=username,
                    error=str(e),
                    posts_found=len(posts),
                    hint="This might be due to rate limiting or Instagram API changes"
                )
                # Return whatever posts we managed to get
                if posts:
                    logger.info(f"Returning {len(posts)} posts despite error")
                    return posts
                else:
                    logger.warning(
                        "No posts could be fetched",
                        username=username,
                        hint="Profile might be private, rate limited, or API format changed"
                    )
                    return []

            logger.info(f"Fetched Instagram posts", username=username, count=len(posts))
            return posts

        except ImportError:
            logger.error("instaloader not installed. Install with: pip install instaloader")
            raise NotImplementedError("instaloader not installed. Use mock data with USE_MOCK_SCRAPERS=true")
        except Exception as e:
            logger.error(f"Error fetching Instagram posts", error=str(e), exc_info=True)
            return []

    def _get_profile_metadata_real(self, profile_url: str) -> Optional[Dict]:
        """
        Real Instagram profile metadata using instaloader

        Gets detailed profile information
        """
        try:
            import instaloader

            L = self._get_authenticated_loader()

            # Extract username from profile URL
            username = profile_url.split("/")[-1] if "/" in profile_url else profile_url
            username = username.strip("/")

            logger.info(f"Fetching Instagram metadata", username=username)

            try:
                profile = instaloader.Profile.from_username(L.context, username)
            except instaloader.exceptions.ConnectionException as e:
                error_str = str(e)
                
                # Check for rate limiting
                if "Please wait a few minutes" in error_str or "rate limit" in error_str.lower():
                    logger.warning(
                        "Instagram rate limit reached",
                        username=username,
                        hint="Please wait a few minutes before trying again"
                    )
                    return None
                
                # Handle 401 Unauthorized - session expired (but not rate limit)
                if "401" in error_str or "Unauthorized" in error_str:
                    if "Please wait" not in error_str:
                        logger.warning(
                            "Instagram session expired (401), attempting to re-login",
                            username=username
                        )
                        try:
                            L = self._get_authenticated_loader(force_relogin=True)
                            profile = instaloader.Profile.from_username(L.context, username)
                        except Exception as retry_error:
                            retry_error_str = str(retry_error)
                            if "Please wait" in retry_error_str:
                                logger.warning(
                                    "Rate limited after re-login",
                                    username=username,
                                    hint="Please wait a few minutes"
                                )
                            else:
                                logger.error(
                                    "Re-login failed",
                                    username=username,
                                    error=retry_error_str
                                )
                            return None
                    else:
                        logger.warning(
                            "Instagram rate limit (401)",
                            username=username,
                            hint="Please wait a few minutes"
                        )
                        return None
                else:
                    logger.error(f"Instagram connection error: {e}")
                    return None

            return {
                "username": profile.username,
                "profile_url": f"https://instagram.com/{profile.username}",
                "followers_count": profile.followers,
                "posts_count": profile.mediacount,
                "bio": profile.biography,
                "avg_likes": self._calculate_avg_likes(profile),
                "avg_comments": self._calculate_avg_comments(profile),
                "posts_per_week": self._calculate_posting_frequency(profile),
                "video_ratio": self._calculate_video_ratio(profile)
            }

        except ImportError:
            logger.error("instaloader not installed. Install with: pip install instaloader")
            raise NotImplementedError("instaloader not installed. Use mock data with USE_MOCK_SCRAPERS=true")
        except Exception as e:
            logger.error(f"Error fetching Instagram metadata", error=str(e), exc_info=True)
            return None

    # Helper methods
    def _calculate_avg_likes(self, profile) -> int:
        """Calculate average likes from recent posts"""
        try:
            posts = list(profile.get_posts())[:10]  # Sample last 10 posts
            if not posts:
                return 0
            total_likes = sum(p.likes for p in posts)
            return int(total_likes / len(posts))
        except Exception:
            return 0

    def _calculate_avg_comments(self, profile) -> int:
        """Calculate average comments from recent posts"""
        try:
            posts = list(profile.get_posts())[:10]
            if not posts:
                return 0
            total_comments = sum(p.comments for p in posts)
            return int(total_comments / len(posts))
        except Exception:
            return 0

    def _calculate_posting_frequency(self, profile) -> float:
        """Calculate posts per week"""
        try:
            posts = list(profile.get_posts())[:20]
            if len(posts) < 2:
                return 0.0

            # Get date range
            oldest = posts[-1].date_utc
            newest = posts[0].date_utc
            days = (newest - oldest).days or 1

            posts_per_day = len(posts) / days
            return round(posts_per_day * 7, 1)  # Convert to per week
        except Exception:
            return 0.0

    def _calculate_video_ratio(self, profile) -> float:
        """Calculate ratio of video posts"""
        try:
            posts = list(profile.get_posts())[:20]
            if not posts:
                return 0.0

            video_count = sum(1 for p in posts if p.is_video)
            return round(video_count / len(posts), 2)
        except Exception:
            return 0.0
