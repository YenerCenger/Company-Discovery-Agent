"""
Quick test script for Instagram scraper
"""
from scrapers.social.instagram import InstagramScraper
from config.logging_config import get_logger
import json

logger = get_logger(__name__)

def test_with_mock():
    """Test with mock data"""
    print("\n" + "="*60)
    print("TEST 1: Mock Data")
    print("="*60)

    scraper = InstagramScraper(use_mock=True)

    # Find profile
    profile = scraper.find_profile("Luxury Homes")
    if profile:
        print(f"\nProfile Found:")
        print(f"  Username: {profile['username']}")
        print(f"  Followers: {profile['followers_count']:,}")
        print(f"  Posts: {profile['posts_count']}")
        print(f"  Avg Likes: {profile['avg_likes']}")
        print(f"  Video Ratio: {profile['video_ratio']*100:.0f}%")

    # Get posts
    posts = scraper.get_recent_posts("https://instagram.com/luxuryrealestate_miami", limit=10)
    print(f"\nFound {len(posts)} posts")

    if posts:
        print("\nTop 3 posts by views:")
        sorted_posts = sorted(posts, key=lambda p: p.get('view_count', 0), reverse=True)
        for i, post in enumerate(sorted_posts[:3], 1):
            print(f"  {i}. {post.get('view_count', 0):,} views | {post.get('like_count', 0):,} likes")

    return True


def test_real_profile():
    """Test with real Instagram profile"""
    print("\n" + "="*60)
    print("TEST 2: Real Instagram Profile")
    print("="*60)

    scraper = InstagramScraper(use_mock=False)

    # Test with a known public profile
    # Using Instagram's official account as test
    test_username = "instagram"

    print(f"\nSearching for: @{test_username}")
    print("NOTE: This will make a real request to Instagram!")
    print("If rate limited, the test will fail (expected behavior)")

    try:
        profile = scraper.find_profile(test_username)

        if profile:
            print(f"\nProfile Found:")
            print(f"  Username: @{profile['username']}")
            print(f"  Followers: {profile['followers_count']:,}")
            print(f"  Posts: {profile['posts_count']}")
            print(f"  Bio: {profile['bio'][:100]}...")

            # Get a few posts
            print(f"\nFetching recent videos from @{profile['username']}...")
            posts = scraper.get_recent_posts(profile['profile_url'], limit=5)

            print(f"Found {len(posts)} video posts")

            if posts:
                print("\nRecent videos:")
                for i, post in enumerate(posts[:3], 1):
                    views = post.get('view_count', 0)
                    likes = post.get('like_count', 0)
                    print(f"  {i}. {views:,} views | {likes:,} likes")
                    print(f"     {post['post_url']}")

            return True
        else:
            print("Profile not found")
            return False

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nThis is expected if:")
        print("  - You're rate limited by Instagram")
        print("  - Network issues")
        print("  - Profile is private")
        print("\nTry with USE_MOCK_SCRAPERS=true instead")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("INSTAGRAM SCRAPER TEST")
    print("="*60)

    # Test 1: Mock data (always works)
    success_mock = test_with_mock()

    # Test 2: Real profile (may fail due to rate limiting)
    print("\n\nWould you like to test with REAL Instagram profile?")
    print("WARNING: This will make actual requests to Instagram")
    print("You may get rate limited!")

    # For automated testing, skip real test
    # Uncomment below to enable:
    # success_real = test_real_profile()

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Mock Data Test: {'PASSED' if success_mock else 'FAILED'}")
    # print(f"Real Profile Test: {'PASSED' if success_real else 'FAILED'}")
    print("\nTo test with real Instagram:")
    print("  1. Set USE_MOCK_SCRAPERS=false in .env")
    print("  2. Uncomment the real test in this script")
    print("  3. Run again")
    print("="*60)
