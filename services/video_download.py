import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
from config.settings import settings
from utils.validators import sanitize_filename
from utils.exceptions import VideoDownloadError
import structlog

logger = structlog.get_logger(__name__)


class VideoDownloadService:
    """Service for downloading videos using yt-dlp"""

    def __init__(self, download_base_path: Optional[Path] = None):
        """
        Initialize video download service

        Args:
            download_base_path: Base directory for downloads (defaults to settings)
        """
        self.base_path = download_base_path or settings.DOWNLOAD_BASE_PATH
        self.base_path = Path(self.base_path)

    def download(self, post_url: str, platform: str, post_id: str) -> Dict:
        """
        Download video using yt-dlp

        Args:
            post_url: URL of the post/video
            platform: Platform name (instagram, tiktok, youtube)
            post_id: Unique post identifier

        Returns:
            Dictionary with keys: status, file_path, error
            - status: "success" or "error"
            - file_path: Path to downloaded file (if successful)
            - error: Error message (if failed)
        """
        # Create platform-specific directory
        output_dir = self.base_path / platform
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize post_id for filename
        safe_post_id = sanitize_filename(post_id)
        output_template = str(output_dir / f"{safe_post_id}.%(ext)s")

        # Build yt-dlp command
        cmd = [
            "yt-dlp",
            "--format", settings.YTDLP_FORMAT,
            "--output", output_template,
            "--no-playlist",
            "--write-info-json",
            "--max-filesize", settings.YTDLP_MAX_FILESIZE,
            post_url
        ]

        logger.info(
            "Starting video download",
            post_url=post_url,
            platform=platform,
            post_id=post_id
        )

        try:
            # Run yt-dlp command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                # Find the downloaded file
                video_path = self._find_downloaded_file(output_dir, safe_post_id)

                if video_path:
                    logger.info(
                        "Video download successful",
                        post_url=post_url,
                        file_path=str(video_path)
                    )
                    return {
                        "status": "success",
                        "file_path": str(video_path),
                        "error": None
                    }
                else:
                    error_msg = "Download completed but file not found"
                    logger.error(error_msg, post_url=post_url)
                    return {
                        "status": "error",
                        "file_path": None,
                        "error": error_msg
                    }
            else:
                error_msg = result.stderr or "Unknown download error"
                logger.error(
                    "Video download failed",
                    post_url=post_url,
                    error=error_msg
                )
                return {
                    "status": "error",
                    "file_path": None,
                    "error": error_msg
                }

        except subprocess.TimeoutExpired:
            error_msg = "Download timeout (5 minutes)"
            logger.error("Video download timeout", post_url=post_url)
            return {
                "status": "error",
                "file_path": None,
                "error": error_msg
            }
        except FileNotFoundError:
            error_msg = "yt-dlp not found. Please install: pip install yt-dlp"
            logger.error(error_msg)
            return {
                "status": "error",
                "file_path": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(
                "Video download unexpected error",
                post_url=post_url,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "file_path": None,
                "error": error_msg
            }

    def _find_downloaded_file(self, output_dir: Path, post_id: str) -> Optional[Path]:
        """
        Find the downloaded video file

        Args:
            output_dir: Directory where file should be
            post_id: Post identifier used in filename

        Returns:
            Path to video file if found, None otherwise
        """
        # Common video extensions
        video_extensions = [".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv"]

        for ext in video_extensions:
            video_path = output_dir / f"{post_id}{ext}"
            if video_path.exists():
                return video_path

        # If not found with exact post_id, search for files starting with post_id
        for file_path in output_dir.glob(f"{post_id}*"):
            if file_path.suffix in video_extensions:
                return file_path

        return None

    def get_video_info(self, post_url: str) -> Optional[Dict]:
        """
        Get video information without downloading

        Args:
            post_url: URL of the post/video

        Returns:
            Dictionary with video metadata or None if failed
        """
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            post_url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.warning(
                    "Failed to get video info",
                    post_url=post_url,
                    error=result.stderr
                )
                return None

        except Exception as e:
            logger.error(
                "Error getting video info",
                post_url=post_url,
                error=str(e)
            )
            return None

    def verify_file_exists(self, file_path: str) -> bool:
        """
        Verify that a downloaded file exists and is readable

        Args:
            file_path: Path to file

        Returns:
            True if file exists and is readable, False otherwise
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file() and path.stat().st_size > 0
        except Exception:
            return False
