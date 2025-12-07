"""
Instagram session dosyasını temizle
401 hatası alıyorsanız bu scripti çalıştırın
"""

from pathlib import Path
from config.settings import settings

session_file = settings.INSTAGRAM_SESSION_FILE

if session_file.exists():
    try:
        session_file.unlink()
        print(f"✅ Session dosyası silindi: {session_file}")
        print("📝 Bir sonraki çalıştırmada yeni login yapılacak")
    except Exception as e:
        print(f"❌ Session dosyası silinemedi: {e}")
else:
    print(f"ℹ️  Session dosyası zaten yok: {session_file}")






