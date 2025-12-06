"""Check pipeline results in database"""
from database.session import get_db_session
from database.models import Company, SocialProfile, SocialPost, VideoDownloadJob
from sqlmodel import select, func

with get_db_session() as session:
    # Count records
    companies_count = session.exec(select(func.count()).select_from(Company)).one()
    profiles_count = session.exec(select(func.count()).select_from(SocialProfile)).one()
    posts_count = session.exec(select(func.count()).select_from(SocialPost)).one()
    jobs_count = session.exec(select(func.count()).select_from(VideoDownloadJob)).one()

    print(f"\n=== Pipeline Results ===")
    print(f"  Companies: {companies_count}")
    print(f"  Social Profiles: {profiles_count}")
    print(f"  Posts: {posts_count}")
    print(f"  Download Jobs: {jobs_count}")

    # Show companies
    if companies_count > 0:
        print(f"\n=== Companies ===")
        companies = session.exec(select(Company).limit(5)).all()
        for c in companies:
            print(f"  - {c.name} ({c.source})")

    # Show profiles
    if profiles_count > 0:
        print(f"\n=== Social Profiles ===")
        profiles = session.exec(select(SocialProfile).limit(5)).all()
        for p in profiles:
            print(f"  - {p.platform}: {p.username} ({p.followers_count} followers)")

    # Show download jobs
    if jobs_count > 0:
        print(f"\n=== Download Jobs ===")
        jobs = session.exec(select(VideoDownloadJob).limit(5)).all()
        for j in jobs:
            print(f"  - {j.status}: {j.post_url[:50]}...")

    print()
