"""
LLM kullanmayan test scripti
Şirket bulma ve Instagram profil/post çekme testi

Bu script LLM gerektirmez çünkü:
1. Company scraper mock data döndürüyor
2. Instagram scraper direkt instaloader kullanıyor
"""

from scrapers.company_scraper import CompanyScraper
from scrapers.social.instagram import InstagramScraper
from config.logging_config import get_logger
import sys

logger = get_logger(__name__)


def test_company_discovery():
    """Test 1: Şirket bulma (mock data)"""
    print("\n" + "="*60)
    print("TEST 1: Şirket Bulma (Mock Data)")
    print("="*60)
    
    scraper = CompanyScraper()
    
    # Test şehir/ülke
    city = "Miami"
    country = "USA"
    
    print(f"\n🔍 {city}, {country} için şirket aranıyor...")
    
    try:
        companies = scraper.search_companies(city=city, country=country, limit=5)
        
        print(f"\n✅ {len(companies)} şirket bulundu:\n")
        for i, company in enumerate(companies, 1):
            print(f"  {i}. {company['name']}")
            print(f"     Website: {company.get('website_url', 'N/A')}")
            print(f"     Kaynak: {company.get('source', 'N/A')}")
            print()
        
        return companies
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return []


def test_instagram_profile_search(company_name: str):
    """Test 2: Instagram profil arama"""
    print("\n" + "="*60)
    print(f"TEST 2: Instagram Profil Arama - {company_name}")
    print("="*60)
    
    instagram_scraper = InstagramScraper()
    
    print(f"\n🔍 '{company_name}' için Instagram profili aranıyor...")
    
    try:
        profile = instagram_scraper.find_profile(
            company_name=company_name,
            website_url=None
        )
        
        if profile:
            print(f"\n✅ Instagram profili bulundu!\n")
            print(f"  Kullanıcı Adı: @{profile['username']}")
            print(f"  Profil URL: {profile['profile_url']}")
            print(f"  Takipçi: {profile.get('followers_count', 'N/A'):,}")
            print(f"  Post Sayısı: {profile.get('posts_count', 'N/A'):,}")
            print(f"  Bio: {profile.get('bio', 'N/A')[:100]}...")
            print(f"  Ortalama Beğeni: {profile.get('avg_likes', 'N/A'):,}")
            print(f"  Haftalık Post: {profile.get('posts_per_week', 'N/A')}")
            print(f"  Video Oranı: {profile.get('video_ratio', 'N/A')}")
            return profile
        else:
            print(f"\n⚠️  Instagram profili bulunamadı")
            return None
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_instagram_posts(profile_url: str, limit: int = 5):
    """Test 3: Instagram post'ları çekme"""
    print("\n" + "="*60)
    print(f"TEST 3: Instagram Post'ları Çekme")
    print("="*60)
    
    instagram_scraper = InstagramScraper()
    
    print(f"\n📥 {profile_url} profilinden {limit} video post çekiliyor...")
    
    try:
        posts = instagram_scraper.get_recent_posts(profile_url=profile_url, limit=limit)
        
        if posts:
            print(f"\n✅ {len(posts)} video post bulundu:\n")
            for i, post in enumerate(posts, 1):
                print(f"  {i}. {post.get('post_type', 'video').upper()}")
                print(f"     URL: {post['post_url']}")
                print(f"     Tarih: {post.get('published_at', 'N/A')}")
                print(f"     👁️  Görüntülenme: {post.get('view_count', 0):,}")
                print(f"     ❤️  Beğeni: {post.get('like_count', 0):,}")
                print(f"     💬 Yorum: {post.get('comment_count', 0):,}")
                if post.get('caption_text'):
                    caption = post['caption_text'][:80]
                    print(f"     📝 Başlık: {caption}...")
                print()
            return posts
        else:
            print(f"\n⚠️  Video post bulunamadı")
            return []
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_full_pipeline():
    """Tam pipeline testi: Şirket bul -> Profil bul -> Post çek"""
    print("\n" + "="*70)
    print("FULL PIPELINE TEST: Şirket Bulma → Instagram Profil → Post Çekme")
    print("="*70)
    
    # Test 1: Şirket bulma
    companies = test_company_discovery()
    
    if not companies:
        print("\n❌ Şirket bulunamadı, test durduruldu")
        return
    
    # Test 2: İlk şirket için Instagram profil arama
    first_company = companies[0]
    profile = test_instagram_profile_search(first_company['name'])
    
    if not profile:
        print("\n⚠️  Instagram profili bulunamadı, test devam ediyor...")
        # Manuel bir profil URL'i ile test edebiliriz
        print("\n💡 Manuel profil URL ile test edebilirsiniz:")
        print("   python test_without_llm.py --profile-url https://instagram.com/USERNAME")
        return
    
    # Test 3: Post'ları çek
    posts = test_instagram_posts(profile['profile_url'], limit=3)
    
    # Özet
    print("\n" + "="*70)
    print("TEST ÖZETİ")
    print("="*70)
    print(f"✅ Bulunan Şirketler: {len(companies)}")
    print(f"✅ Bulunan Profiller: {1 if profile else 0}")
    print(f"✅ Çekilen Post'lar: {len(posts)}")
    print("="*70 + "\n")


def test_manual_profile(profile_url: str):
    """Manuel profil URL ile test"""
    print("\n" + "="*60)
    print("MANUEL PROFIL TESTİ")
    print("="*60)
    
    # Profil metadata
    instagram_scraper = InstagramScraper()
    
    print(f"\n📊 Profil bilgileri çekiliyor: {profile_url}")
    metadata = instagram_scraper.get_profile_metadata(profile_url)
    
    if metadata:
        print(f"\n✅ Profil bilgileri:\n")
        print(f"  Kullanıcı Adı: @{metadata['username']}")
        print(f"  Takipçi: {metadata.get('followers_count', 'N/A'):,}")
        print(f"  Post Sayısı: {metadata.get('posts_count', 'N/A'):,}")
        print(f"  Bio: {metadata.get('bio', 'N/A')}")
        print(f"  Ortalama Beğeni: {metadata.get('avg_likes', 'N/A'):,}")
        print(f"  Haftalık Post: {metadata.get('posts_per_week', 'N/A')}")
        print(f"  Video Oranı: {metadata.get('video_ratio', 'N/A')}")
    
    # Post'ları çek
    posts = test_instagram_posts(profile_url, limit=5)
    
    return metadata, posts


def main():
    """Ana test fonksiyonu"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LLM kullanmayan test scripti - Şirket bulma ve Instagram testi"
    )
    
    parser.add_argument(
        "--profile-url",
        type=str,
        help="Manuel test için Instagram profil URL'i (örn: https://instagram.com/username)"
    )
    
    parser.add_argument(
        "--company-name",
        type=str,
        help="Belirli bir şirket adı ile Instagram profil arama"
    )
    
    args = parser.parse_args()
    
    if args.profile_url:
        # Manuel profil testi
        test_manual_profile(args.profile_url)
    elif args.company_name:
        # Belirli şirket için profil arama
        profile = test_instagram_profile_search(args.company_name)
        if profile:
            test_instagram_posts(profile['profile_url'], limit=5)
    else:
        # Tam pipeline testi
        test_full_pipeline()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test kullanıcı tarafından durduruldu")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

