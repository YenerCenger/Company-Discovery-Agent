"""
Test Google search for Instagram profiles
"""
import re
import urllib.parse
from pathlib import Path

# crawl4ai ile Google'ı aç
from scrapers.crawl4ai_handler import Crawl4AIHandler

def test_google_search(company_name: str):
    """Test Google search for Instagram profiles"""
    
    # Türkçe karakterleri temizle
    def clean_turkish(text: str) -> str:
        replacements = {
            'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S',
            'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U',
            'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        return text
    
    company_clean = clean_turkish(company_name)
    search_query = f'{company_clean} instagram'
    # DuckDuckGo - no cookie consent!
    ddg_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
    
    print(f"\n🔍 Searching DuckDuckGo: {ddg_url}\n")
    
    # requests ile HTML al (DuckDuckGo crawl4ai'ı engelliyor)
    import requests as req
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    response = req.get(ddg_url, headers=headers, timeout=15)
    html = response.text
    
    if not html:
        print("❌ No HTML received from DuckDuckGo")
        return
    
    print(f"✅ HTML received: {len(html)} characters")
    
    # HTML'i dosyaya kaydet
    debug_file = Path("data/google_debug.html")
    debug_file.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"📄 HTML saved to: {debug_file}")
    
    # Instagram kelimesi var mı?
    if 'instagram' in html.lower():
        print("✅ 'instagram' found in HTML")
        
        # URL decode
        decoded_html = urllib.parse.unquote(html)
        
        # Regex ile username'leri bul
        pattern = r'(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)'
        matches = re.findall(pattern, decoded_html, re.IGNORECASE)
        
        # Geçersiz username'leri filtrele
        invalid = ['www', 'accounts', 'explore', 'direct', 'about', 'blog', 'developers', 'popular', 'help', 'legal', 'p', 'reel', 'tv', 'stories']
        valid_usernames = [m for m in matches if m.lower() not in invalid and len(m) > 2]
        
        # Unique yap
        unique_usernames = list(dict.fromkeys(valid_usernames))
        
        print(f"\n📱 Found {len(unique_usernames)} Instagram profiles:")
        for i, username in enumerate(unique_usernames[:10], 1):
            print(f"   {i}. @{username}")
    else:
        print("❌ 'instagram' NOT found in HTML")
        
        # HTML'in ilk 1000 karakterini göster
        print(f"\n📄 First 1000 chars of HTML:")
        print(html[:1000])

if __name__ == "__main__":
    import sys
    
    company = sys.argv[1] if len(sys.argv) > 1 else "Folkart Yapi"
    test_google_search(company)

