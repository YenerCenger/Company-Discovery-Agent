#!/usr/bin/env python
"""
Reset Instagram session - Clean login

Usage:
    python reset_instagram_session.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import instaloader

# Load environment variables
load_dotenv()

# Get credentials
username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")

if not username or not password:
    print("❌ Error: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env file")
    exit(1)

# Session file path
session_file = Path(__file__).parent / "data" / ".instaloader_session"

print(f"🔐 Instagram Login Script")
print(f"Username: {username}")
print(f"Session file: {session_file}")
print()

# Remove old session
if session_file.exists():
    print(f"🗑️  Removing old session file...")
    session_file.unlink()
    print(f"✅ Old session removed")
else:
    print(f"ℹ️  No existing session found")

print()

# Create new session
print(f"🔄 Creating new session...")
L = instaloader.Instaloader()

try:
    # Login
    print(f"🔑 Logging in as {username}...")
    L.login(username, password)

    # Save session
    print(f"💾 Saving session to {session_file}...")
    L.save_session_to_file(str(session_file))

    print()
    print(f"✅ SUCCESS! Instagram session created")
    print(f"Session saved to: {session_file}")
    print()
    print(f"You can now use the main application.")

except instaloader.exceptions.BadCredentialsException:
    print()
    print(f"❌ ERROR: Invalid username or password")
    print(f"Please check your credentials in .env file:")
    print(f"   INSTAGRAM_USERNAME={username}")
    print(f"   INSTAGRAM_PASSWORD=***")
    exit(1)

except instaloader.exceptions.TwoFactorAuthRequiredException:
    print()
    print(f"❌ ERROR: Two-factor authentication is enabled")
    print(f"Please disable 2FA on your Instagram account or use a different account")
    exit(1)

except Exception as e:
    print()
    print(f"❌ ERROR: {e}")
    exit(1)
