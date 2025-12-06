from typing import List
from agents.base import BaseAgent
from database.models import SocialPost, VideoDownloadJob
from database.repositories import VideoDownloadJobRepository
from services.video_download import VideoDownloadService
from utils.retry import retry
from utils.exceptions import VideoDownloadError
from config.settings import settings
from config.logging_config import get_logger
from datetime import datetime


class VideoDownloaderAgent(BaseAgent[List[SocialPost], List[VideoDownloadJob]]):
    """
    Agent for downloading videos from social posts

    Responsibilities:
    1. Create download jobs for posts
    2. Download videos using VideoDownloadService
    3. Update job status (success/error)
    4. Retry failed downloads
    5. Return list of download jobs
    """

    def __init__(self, db_session, logger=None):
        super().__init__(db_session, logger or get_logger(__name__))
        self.job_repo = VideoDownloadJobRepository(db_session)
        self.download_service = VideoDownloadService(
            download_base_path=settings.DOWNLOAD_BASE_PATH
        )

    def process(self, input_data: List[SocialPost]) -> List[VideoDownloadJob]:
        """
        Download videos from social posts

        Args:
            input_data: List of SocialPost objects

        Returns:
            List of VideoDownloadJob objects
        """
        self.logger.info(
            "Starting video downloads",
            post_count=len(input_data)
        )

        jobs = []

        for post in input_data:
            try:
                # Check if download job already exists
                existing_job = self.job_repo.find_by_post(post.id)

                if existing_job and existing_job.status == "done":
                    self.logger.info(
                        "Video already downloaded",
                        post_url=post.post_url,
                        file_path=existing_job.file_path
                    )
                    jobs.append(existing_job)
                    continue

                # Create new download job
                job = self.job_repo.create({
                    "social_post_id": post.id,
                    "platform": post.platform,
                    "post_url": post.post_url,
                    "status": "pending"
                })

                # Download video with retry
                download_result = self._download_with_retry(
                    post_url=post.post_url,
                    platform=post.platform,
                    post_id=post.external_post_id
                )

                # Update job status
                if download_result["status"] == "success":
                    self.job_repo.update_status(
                        job_id=job.id,
                        status="done",
                        file_path=download_result["file_path"]
                    )
                    self.logger.info(
                        "Video downloaded successfully",
                        post_url=post.post_url,
                        file_path=download_result["file_path"]
                    )
                else:
                    self.job_repo.update_status(
                        job_id=job.id,
                        status="error",
                        error_message=download_result["error"]
                    )
                    self.logger.error(
                        "Video download failed",
                        post_url=post.post_url,
                        error=download_result["error"]
                    )

                # Refresh job to get updated data
                self.db.refresh(job)
                jobs.append(job)

            except Exception as e:
                self.logger.error(
                    "Error processing download",
                    post_url=post.post_url if post else None,
                    error=str(e)
                )
                # Continue with other downloads

        # Commit all changes
        self.db.commit()

        # Calculate statistics
        success_count = sum(1 for j in jobs if j.status == "done")
        error_count = sum(1 for j in jobs if j.status == "error")

        self.logger.info(
            "Video downloads completed",
            total_jobs=len(jobs),
            successful=success_count,
            failed=error_count
        )

        return jobs

    @retry(
        max_attempts=3,
        delay=2.0,
        backoff=2.0,
        exceptions=(VideoDownloadError,)
    )
    def _download_with_retry(self, post_url: str, platform: str, post_id: str) -> dict:
        """
        Download video with retry logic

        Args:
            post_url: URL of the post
            platform: Platform name
            post_id: External post ID

        Returns:
            Download result dictionary
        """
        result = self.download_service.download(
            post_url=post_url,
            platform=platform,
            post_id=post_id
        )

        # If download failed, raise exception to trigger retry
        if result["status"] == "error":
            # Don't retry certain errors
            error_msg = result.get("error", "")
            if "not found" in error_msg.lower() or "yt-dlp not found" in error_msg.lower():
                return result  # Return error without retry

            raise VideoDownloadError(result["error"])

        return result
