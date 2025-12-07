"""
Crawl4AI cache'ini temizle
Gerçek veriler için cache'i temizleyin
"""

from pathlib import Path
from config.settings import settings

cache_dir = Path(__file__).parent / "data" / "crawl_cache"

if cache_dir.exists():
    cache_files = list(cache_dir.glob("*.json"))
    if cache_files:
        print(f"🗑️  {len(cache_files)} cache dosyası bulundu")
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                print(f"   ✅ Silindi: {cache_file.name}")
            except Exception as e:
                print(f"   ❌ Silinemedi {cache_file.name}: {e}")
        print(f"\n✅ Cache temizlendi!")
    else:
        print("ℹ️  Cache dosyası yok")
else:
    print("ℹ️  Cache dizini yok")






