"""
LLM ile internetten şirket bulma test scripti
Ollama + LLM Parser ile HTML'den şirket bilgileri çıkarma testi
"""

from scrapers.company_scraper import CompanyScraper
from scrapers.crawl4ai_handler import Crawl4AIHandler
from scrapers.parsers.llm_parser import LLMParser
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


def test_llm_extraction():
    """Test 2: LLM ile örnek HTML'den şirket çıkarma"""
    print("\n" + "="*60)
    print("TEST 2: LLM ile Şirket Çıkarma (Örnek HTML)")
    print("="*60)
    
    # Örnek HTML içeriği (gerçek bir emlak sitesinden)
    sample_html = """
    <html>
    <body>
        <h1>Miami Real Estate Companies</h1>
        <div class="company">
            <h2>Miami Luxury Homes</h2>
            <p>Website: https://miamiluxuryhomes.com</p>
            <p>Phone: (305) 555-0100</p>
        </div>
        <div class="company">
            <h2>Ocean View Properties</h2>
            <p>Website: https://oceanviewproperties.com</p>
            <p>Phone: (305) 555-0200</p>
        </div>
        <div class="company">
            <h2>Sunset Realty Group</h2>
            <p>Website: https://sunsetrealty.com</p>
        </div>
    </body>
    </html>
    """
    
    print("\n📄 Örnek HTML içeriği hazırlanıyor...")
    print(f"   HTML uzunluğu: {len(sample_html)} karakter")
    
    try:
        parser = LLMParser()
        
        print("\n🤖 LLM ile şirket bilgileri çıkarılıyor...")
        print("   (Bu işlem birkaç saniye sürebilir)")
        
        companies = parser.extract_companies(
            html=sample_html,
            query_context="Miami Florida real estate",
            limit=10
        )
        
        if companies:
            print(f"\n✅ {len(companies)} şirket bulundu:\n")
            for i, company in enumerate(companies, 1):
                print(f"  {i}. {company.get('name', 'N/A')}")
                if company.get('website_url'):
                    print(f"     🌐 {company['website_url']}")
                if company.get('phone'):
                    print(f"     📞 {company['phone']}")
                if company.get('source'):
                    print(f"     📍 Kaynak: {company['source']}")
                print()
            return True
        else:
            print("\n⚠️  Şirket bulunamadı")
            return False
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_web_scraping_with_llm(city: str = "Miami", country: str = "USA"):
    """Test 3: Web sitesinden HTML çekip LLM ile şirket bulma"""
    print("\n" + "="*60)
    print(f"TEST 3: Web Scraping + LLM - {city}, {country}")
    print("="*60)
    
    print(f"\n🔍 {city}, {country} için emlak şirketleri aranıyor...")
    print("   (Bu işlem birkaç dakika sürebilir)")
    
    try:
        scraper = CompanyScraper()
        
        companies = scraper.search_companies(
            city=city,
            country=country,
            limit=10
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
            
            print("\n📊 Kaynak Dağılımı:")
            for source, count in sources.items():
                print(f"   {source}: {count} şirket")
            
            return True
        else:
            print("\n⚠️  Şirket bulunamadı")
            return False
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_url_llm(url: str):
    """Test 4: Belirli bir URL'den LLM ile şirket çıkarma"""
    print("\n" + "="*60)
    print(f"TEST 4: Direkt URL + LLM")
    print("="*60)
    
    print(f"\n🌐 URL: {url}")
    print("   HTML çekiliyor...")
    
    try:
        handler = Crawl4AIHandler()
        html = handler.crawl_sync(url)
        
        if not html or len(html) < 1000:
            print(f"\n⚠️  HTML çekilemedi veya çok kısa ({len(html) if html else 0} karakter)")
            return False
        
        print(f"   ✅ HTML çekildi: {len(html):,} karakter")
        
        print("\n🤖 LLM ile şirket bilgileri çıkarılıyor...")
        print("   (Bu işlem birkaç saniye sürebilir)")
        
        parser = LLMParser()
        companies = parser.extract_companies(
            html=html,
            query_context=f"Real estate companies from {url}",
            limit=20
        )
        
        if companies:
            print(f"\n✅ {len(companies)} şirket bulundu:\n")
            for i, company in enumerate(companies[:10], 1):  # İlk 10'unu göster
                print(f"  {i}. {company.get('name', 'N/A')}")
                if company.get('website_url'):
                    print(f"     🌐 {company['website_url']}")
                if company.get('phone'):
                    print(f"     📞 {company['phone']}")
                print()
            
            if len(companies) > 10:
                print(f"   ... ve {len(companies) - 10} şirket daha")
            
            return True
        else:
            print("\n⚠️  Şirket bulunamadı")
            return False
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ana test fonksiyonu"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LLM ile internetten şirket bulma test scripti"
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
        "--url",
        type=str,
        help="Test için direkt URL (örn: https://www.realtor.com/realestateagents/miami-florida)"
    )
    
    parser.add_argument(
        "--skip-ollama-check",
        action="store_true",
        help="Ollama kontrolünü atla"
    )
    
    args = parser.parse_args()
    
    results = {
        "ollama": False,
        "llm_extraction": False,
        "web_scraping": False,
        "direct_url": False
    }
    
    # Test 1: Ollama kontrolü
    if not args.skip_ollama_check:
        results["ollama"] = test_ollama_connection()
        if not results["ollama"]:
            print("\n⚠️  Ollama çalışmıyor, diğer testler başarısız olabilir")
            response = input("\nDevam etmek istiyor musunuz? (e/h): ")
            if response.lower() != 'e':
                return
    else:
        results["ollama"] = True
        print("\n⏭️  Ollama kontrolü atlandı")
    
    # Test 2: LLM extraction (örnek HTML)
    results["llm_extraction"] = test_llm_extraction()
    
    # Test 3: Web scraping + LLM
    if args.city and args.country:
        results["web_scraping"] = test_web_scraping_with_llm(
            city=args.city,
            country=args.country
        )
    
    # Test 4: Direkt URL
    if args.url:
        results["direct_url"] = test_direct_url_llm(args.url)
    
    # Özet
    print("\n" + "="*60)
    print("TEST ÖZETİ")
    print("="*60)
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}: {'Başarılı' if result else 'Başarısız'}")
    print("="*60 + "\n")


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

