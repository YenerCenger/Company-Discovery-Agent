"""
Tam Pipeline Test: Şirket Bulma + Instagram Profil Bulma
LLM ile internetten şirket bulma ve Instagram profil arama testi
"""

from scrapers.company_scraper import CompanyScraper
from scrapers.social.instagram import InstagramScraper
from services.llm_service import HTMLCompanyExtractor
from config.logging_config import get_logger
import sys

logger = get_logger(__name__)


def test_ollama_connection():
    """Test 1: Ollama bağlantısını kontrol et"""
    print("\n" + "="*60)
    print("TEST 1: Ollama Bağlantı Kontrolü")
    print("="*60)
    
    extractor = HTMLCompanyExtractor()
    
    print("\n🔍 Ollama kontrol ediliyor...")
    
    if extractor.check_ollama_available():
        print(f"\n✅ Ollama çalışıyor!")
        print(f"   Model: {extractor.llm.model}")
        print(f"   URL: {extractor.llm.base_url}")
        return True
    else:
        print(f"\n❌ Ollama bulunamadı veya model yüklü değil")
        print(f"   Model: {extractor.llm.model}")
        print(f"   URL: {extractor.llm.base_url}")
        print(f"\n💡 Çözüm:")
        print(f"   1. Ollama'nın çalıştığından emin olun: ollama serve")
        print(f"   2. Modeli yükleyin: ollama pull {extractor.llm.model}")
        return False


def test_company_discovery_with_llm(city: str, country: str, limit: int = 5):
    """Test 2: LLM ile internetten şirket bulma"""
    print("\n" + "="*60)
    print(f"TEST 2: LLM ile Şirket Bulma - {city}, {country}")
    print("="*60)
    
    print(f"\n🔍 {city}, {country} için emlak şirketleri aranıyor...")
    print("   (Bu işlem birkaç dakika sürebilir)")
    
    try:
        scraper = CompanyScraper()
        
        companies = scraper.search_companies(
            city=city,
            country=country,
            limit=limit
        )
        
        if companies:
            print(f"\n✅ {len(companies)} şirket bulundu:\n")
            for i, company in enumerate(companies, 1):
                print(f"  {i}. {company.get('name', 'N/A')}")
                if company.get('website_url'):
                    print(f"     🌐 {company['website_url']}")
                if company.get('source'):
                    print(f"     📍 Kaynak: {company['source']}")
                print()
            
            # Kaynaklara göre grupla
            sources = {}
            for company in companies:
                source = company.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            print("📊 Kaynak Dağılımı:")
            for source, count in sources.items():
                print(f"   {source}: {count} şirket")
            
            return companies
        else:
            print("\n⚠️  Şirket bulunamadı")
            return []
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_instagram_profile_search(company_name: str):
    """Test 3: Instagram profil arama"""
    print("\n" + "="*60)
    print(f"TEST 3: Instagram Profil Arama - {company_name}")
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
            if profile.get('bio'):
                bio = profile['bio'][:100]
                print(f"  Bio: {bio}...")
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


def test_instagram_posts(profile_url: str, limit: int = 3):
    """Test 4: Instagram post'ları çekme"""
    print("\n" + "="*60)
    print(f"TEST 4: Instagram Post'ları Çekme")
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


def test_full_pipeline(city: str, country: str, limit: int = 5):
    """Tam Pipeline Testi: Şirket Bul → Instagram Profil Bul → Post Çek"""
    print("\n" + "="*70)
    print("FULL PIPELINE TEST: Şirket Bulma → Instagram Profil → Post Çekme")
    print("="*70)
    
    results = {
        "companies_found": 0,
        "profiles_found": 0,
        "posts_found": 0,
        "companies_with_profiles": []
    }
    
    # Test 1: Ollama kontrolü
    if not test_ollama_connection():
        print("\n⚠️  Ollama çalışmıyor, test devam ediyor ama LLM çalışmayabilir")
        response = input("\nDevam etmek istiyor musunuz? (e/h): ")
        if response.lower() != 'e':
            return results
    
    # Test 2: Şirket bulma
    companies = test_company_discovery_with_llm(city, country, limit)
    results["companies_found"] = len(companies)
    
    if not companies:
        print("\n❌ Şirket bulunamadı, test durduruldu")
        return results
    
    # Test 3: Her şirket için Instagram profil arama
    print("\n" + "="*70)
    print("TEST 3: Tüm Şirketler için Instagram Profil Arama")
    print("="*70)
    
    profiles_found = []
    for i, company in enumerate(companies, 1):
        company_name = company.get('name', '')
        if not company_name:
            continue
        
        print(f"\n[{i}/{len(companies)}] {company_name} için Instagram profili aranıyor...")
        
        profile = test_instagram_profile_search(company_name)
        
        if profile:
            profiles_found.append({
                "company": company,
                "profile": profile
            })
            results["companies_with_profiles"].append({
                "company_name": company_name,
                "instagram_username": profile['username'],
                "profile_url": profile['profile_url'],
                "followers": profile.get('followers_count', 0)
            })
    
    results["profiles_found"] = len(profiles_found)
    
    # Test 4: Bulunan profillerden post çekme (ilk profil)
    if profiles_found:
        print("\n" + "="*70)
        print("TEST 4: İlk Bulunan Profilden Post Çekme")
        print("="*70)
        
        first_profile = profiles_found[0]
        profile_url = first_profile['profile']['profile_url']
        company_name = first_profile['company']['name']
        
        print(f"\n📥 {company_name} (@{first_profile['profile']['username']}) profilinden post'lar çekiliyor...")
        
        posts = test_instagram_posts(profile_url, limit=5)
        results["posts_found"] = len(posts)
    
    # Özet
    print("\n" + "="*70)
    print("PIPELINE TEST ÖZETİ")
    print("="*70)
    print(f"✅ Bulunan Şirketler: {results['companies_found']}")
    print(f"✅ Bulunan Instagram Profilleri: {results['profiles_found']}")
    print(f"✅ Çekilen Post'lar: {results['posts_found']}")
    
    if results['companies_with_profiles']:
        print(f"\n📊 Şirketler ve Instagram Profilleri:")
        for item in results['companies_with_profiles']:
            print(f"   • {item['company_name']}")
            print(f"     Instagram: @{item['instagram_username']} ({item['followers']:,} takipçi)")
            print(f"     URL: {item['profile_url']}")
            print()
    
    print("="*70 + "\n")
    
    return results


def main():
    """Ana test fonksiyonu"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tam Pipeline Test: Şirket Bulma + Instagram Profil Bulma"
    )
    
    parser.add_argument(
        "--city",
        type=str,
        default="Miami",
        help="Şehir adı (varsayılan: Miami)"
    )
    
    parser.add_argument(
        "--country",
        type=str,
        default="USA",
        help="Ülke adı (varsayılan: USA)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Bulunacak şirket sayısı (varsayılan: 5)"
    )
    
    parser.add_argument(
        "--skip-ollama-check",
        action="store_true",
        help="Ollama kontrolünü atla"
    )
    
    args = parser.parse_args()
    
    if args.skip_ollama_check:
        # Sadece şirket bulma ve Instagram testi
        companies = test_company_discovery_with_llm(args.city, args.country, args.limit)
        if companies:
            for company in companies[:3]:  # İlk 3 şirket için test
                test_instagram_profile_search(company.get('name', ''))
    else:
        # Tam pipeline testi
        test_full_pipeline(args.city, args.country, args.limit)


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

