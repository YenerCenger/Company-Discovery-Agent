import uuid
from datetime import datetime
from pathlib import Path


def generate_report_id() -> str:
    """Generate a unique report ID"""
    return str(uuid.uuid4())


def get_report_directory() -> Path:
    """Get or create report directory for today"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path("reports") / today
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir













