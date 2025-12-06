from typing import Dict, List
from utils.validators import validate_url


def calculate_importance_score(company_data: Dict) -> float:
    """
    Calculate importance score for a company

    Score components:
    - Website quality: 0.3 (has website, valid URL, HTTPS)
    - Search ranking: 0.3 (position in search results)
    - Online presence: 0.2 (has social media mentioned)
    - Info completeness: 0.2 (has address, phone, etc.)

    Args:
        company_data: Dictionary with company information

    Returns:
        Importance score between 0.0 and 1.0
    """
    score = 0.0

    # Website quality score (30%)
    website_url = company_data.get("website_url")
    if website_url:
        if validate_url(website_url):
            score += 0.2
            if website_url.startswith("https://"):
                score += 0.1

    # Search ranking score (30%)
    # Higher ranking (lower number) = higher score
    search_position = company_data.get("search_position", 100)
    ranking_score = max(0, (100 - search_position) / 100 * 0.3)
    score += ranking_score

    # Online presence score (20%)
    has_social = company_data.get("has_social_media", False)
    if has_social:
        score += 0.2

    # Info completeness score (20%)
    completeness = 0
    fields = ["address", "phone", "email", "description"]
    for field in fields:
        if company_data.get(field):
            completeness += 0.05

    score += completeness

    return min(1.0, max(0.0, score))


def calculate_engagement_score(profile_data: Dict) -> float:
    """
    Calculate engagement score for a social profile

    Score components:
    - Like rate: 0.4 (avg_likes / followers)
    - Comment rate: 0.3 (avg_comments / followers)
    - Posting frequency: 0.2 (posts per week)
    - Video ratio: 0.1 (percentage of video posts)

    Args:
        profile_data: Dictionary with profile information

    Returns:
        Engagement score between 0.0 and 1.0
    """
    score = 0.0
    followers = profile_data.get("followers_count", 1)
    if followers == 0:
        followers = 1  # Avoid division by zero

    # Like rate (40%)
    avg_likes = profile_data.get("avg_likes", 0)
    like_rate = min(1.0, (avg_likes / followers) * 100)  # Normalize to percentage
    score += like_rate * 0.4

    # Comment rate (30%)
    avg_comments = profile_data.get("avg_comments", 0)
    comment_rate = min(1.0, (avg_comments / followers) * 100)
    score += comment_rate * 0.3

    # Posting frequency (20%)
    posts_per_week = profile_data.get("posts_per_week", 0)
    # Normalize: 7+ posts per week = max score
    frequency_score = min(1.0, posts_per_week / 7)
    score += frequency_score * 0.2

    # Video ratio (10%)
    video_ratio = profile_data.get("video_ratio", 0)  # Should be 0.0 to 1.0
    score += video_ratio * 0.1

    return min(1.0, max(0.0, score))


def classify_content_type(posts: List[Dict]) -> str:
    """
    Classify content type based on post analysis

    Classifications:
    - listing-focused: >60% posts show properties
    - educational: >40% posts are tips/advice
    - mixed: Neither dominates

    Args:
        posts: List of post dictionaries with captions and metadata

    Returns:
        Content type classification
    """
    if not posts:
        return "mixed"

    # Keywords for listing-focused content
    listing_keywords = [
        "for sale", "listing", "property", "price", "bedroom", "bathroom",
        "sqft", "square feet", "just listed", "new listing", "open house",
        "sold", "tour", "showing", "apartment", "condo", "house", "home for sale"
    ]

    # Keywords for educational content
    educational_keywords = [
        "tip", "advice", "how to", "guide", "learn", "tutorial", "strategy",
        "market update", "trend", "analysis", "investment", "first time buyer",
        "mortgage", "financing", "did you know", "important to know"
    ]

    listing_count = 0
    educational_count = 0

    for post in posts:
        caption = post.get("caption_text", "").lower()

        # Check for listing keywords
        if any(keyword in caption for keyword in listing_keywords):
            listing_count += 1

        # Check for educational keywords
        if any(keyword in caption for keyword in educational_keywords):
            educational_count += 1

    total_posts = len(posts)
    listing_ratio = listing_count / total_posts
    educational_ratio = educational_count / total_posts

    if listing_ratio > 0.6:
        return "listing-focused"
    elif educational_ratio > 0.4:
        return "educational"
    else:
        return "mixed"


def calculate_post_quality_score(post_data: Dict) -> float:
    """
    Calculate quality score for a post

    Score components:
    - Engagement: 0.5 (likes + comments + saves)
    - View count: 0.3 (for videos)
    - Caption quality: 0.2 (length, hashtags)

    Args:
        post_data: Dictionary with post information

    Returns:
        Quality score between 0.0 and 1.0
    """
    score = 0.0

    # Engagement score (50%)
    likes = post_data.get("like_count", 0)
    comments = post_data.get("comment_count", 0)
    saves = post_data.get("saved_count", 0)
    total_engagement = likes + (comments * 3) + (saves * 5)  # Weight comments and saves higher

    # Normalize based on typical high-performing post
    engagement_score = min(1.0, total_engagement / 1000)
    score += engagement_score * 0.5

    # View count (30%)
    views = post_data.get("view_count", 0)
    view_score = min(1.0, views / 10000)
    score += view_score * 0.3

    # Caption quality (20%)
    caption = post_data.get("caption_text", "")
    caption_score = 0
    if caption:
        # Length check (50-300 chars is good)
        length = len(caption)
        if 50 <= length <= 300:
            caption_score += 0.5
        # Has hashtags
        if "#" in caption:
            caption_score += 0.5

    score += (caption_score / 2) * 0.2

    return min(1.0, max(0.0, score))
