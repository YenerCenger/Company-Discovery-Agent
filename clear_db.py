"""Clear all records from database"""
from database.session import get_db_session
from database.models import SocialProfile, SocialPost, VideoDownloadJob, Company
from sqlmodel import select

with get_db_session() as session:
    # Delete in order (respecting foreign keys)
    for job in session.exec(select(VideoDownloadJob)).all():
        session.delete(job)

    for post in session.exec(select(SocialPost)).all():
        session.delete(post)

    for profile in session.exec(select(SocialProfile)).all():
        session.delete(profile)

    for company in session.exec(select(Company)).all():
        session.delete(company)

    session.commit()
    print("Database cleared successfully!")
