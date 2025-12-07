"""
Analysis router - Video processing endpoints.

This router starts and manages the video analysis pipeline.
Uses background tasks to run heavy operations asynchronously.

Two modes of operation:
1. PostgreSQL-based: Process videos from VideoDownloadJob table (Company Discovery Agent)
2. Folder-based: Process videos from local folders (legacy support)
"""
from pathlib import Path
import logging
import asyncio
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from bson import ObjectId

from modules.video_processor_agent.core.config import settings
from modules.video_processor_agent.core.database import (
    get_analysis_collection,
    get_video_collection,
    get_completed_video_jobs,
    get_video_job_by_id,
    get_video_jobs_by_company,
    get_unprocessed_video_jobs,
    VideoJobResult,
)
from modules.video_processor_agent.models.models import (
    AnalysisRequest,
    AnalysisStatusResponse,
    AnalysisResult,
    VideoMetadata,
)
from modules.video_processor_agent.services.pipeline_service import pipeline_service

# Setup router and logger
router = APIRouter()
logger = logging.getLogger(__name__)

# Supported video formats
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".webm"]


# ==================== REQUEST/RESPONSE MODELS ====================

class ProcessJobsRequest(BaseModel):
    """Request model for processing multiple video jobs."""
    limit: int = 10


class ProcessJobResponse(BaseModel):
    """Response model for video job processing."""
    job_id: str
    status: str
    message: str
    analysis_id: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """Response model for batch processing."""
    status: str
    total_jobs: int
    message: str


# ==================== POSTGRESQL-BASED VIDEO PROCESSING ====================

async def process_video_job_task(video_job: VideoJobResult) -> Optional[str]:
    """
    Background task to process a single video from PostgreSQL VideoDownloadJob.
    
    Args:
        video_job: VideoJobResult containing video info from PostgreSQL
    
    Returns:
        MongoDB ObjectId string if successful, None if failed
    """
    logger.info(f"Processing video job: {video_job.job_id}, file: {video_job.file_path}")
    
    video_path = Path(video_job.file_path)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return None
    
    collection = get_analysis_collection()
    
    try:
        # Check if already processed (by file path)
        existing = await collection.find_one({
            "video_filename": video_path.name,
            "company_name": video_job.company_name
        })
        
        if existing:
            logger.info(f"Video already processed: {video_path.name}")
            return str(existing.get("_id"))
        
        # Convert company_id (UUID) to MongoDB ObjectId-like string
        # Using first 24 chars of UUID hex representation
        company_id_str = str(video_job.company_id).replace("-", "")[:24]
        
        # Run pipeline in executor (CPU/GPU bound operations)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            pipeline_service.process_video,
            str(video_path),
            video_job.company_name,
            company_id_str,
            video_job.video_url,
            None,  # num_vision_samples (auto)
            0.25,  # yolo_confidence
            0.5,   # ocr_confidence
        )
        
        # Update metadata with PostgreSQL data
        result.metadata.platform = video_job.platform
        result.metadata.view_count = video_job.view_count
        result.metadata.like_count = video_job.like_count
        result.metadata.comment_count = video_job.comment_count
        result.metadata.video_url = video_job.video_url
        
        # Save to MongoDB
        result_dict = result.model_dump(by_alias=True, exclude={'id'})
        
        # Add PostgreSQL reference IDs for traceability
        result_dict["postgresql_job_id"] = str(video_job.job_id)
        result_dict["postgresql_company_id"] = str(video_job.company_id)
        
        insert_result = await collection.insert_one(result_dict)
        logger.info(f"Saved analysis for: {video_path.name}, ID: {insert_result.inserted_id}")
        
        return str(insert_result.inserted_id)
        
    except Exception as e:
        logger.error(f"Failed to process video {video_path.name}: {e}", exc_info=True)
        
        # Save error result
        try:
            company_id_str = str(video_job.company_id).replace("-", "")[:24]
            error_result = AnalysisResult(
                company_id=ObjectId(company_id_str),
                company_name=video_job.company_name,
                video_filename=video_path.name,
                video_url=video_job.video_url,
                metadata=VideoMetadata(
                    platform=video_job.platform,
                    view_count=video_job.view_count,
                    like_count=video_job.like_count,
                    comment_count=video_job.comment_count,
                ),
                segments=[],
                all_objects=[],
                all_ocr_text=[],
                dominant_emotion=None,
                status="failed",
                error_message=f"Processing failed: {str(e)}"
            )
            error_dict = error_result.model_dump(by_alias=True, exclude={'id'})
            error_dict["postgresql_job_id"] = str(video_job.job_id)
            error_dict["postgresql_company_id"] = str(video_job.company_id)
            await collection.insert_one(error_dict)
        except Exception as save_error:
            logger.error(f"Failed to save error result: {save_error}")
        
        return None


async def process_all_pending_jobs_task(limit: int = 10) -> None:
    """
    Background task to process all unprocessed video jobs.
    
    Args:
        limit: Maximum number of videos to process
    """
    logger.info(f"Starting batch processing of up to {limit} video jobs")
    
    collection = get_analysis_collection()
    
    # Get already processed filenames
    processed_cursor = collection.find({}, {"video_filename": 1})
    processed_filenames = []
    async for doc in processed_cursor:
        if "video_filename" in doc:
            processed_filenames.append(doc["video_filename"])
    
    # Get unprocessed jobs from PostgreSQL
    unprocessed_jobs = get_unprocessed_video_jobs(processed_filenames, limit=limit)
    
    if not unprocessed_jobs:
        logger.info("No unprocessed video jobs found")
        return
    
    logger.info(f"Found {len(unprocessed_jobs)} unprocessed video jobs")
    
    processed_count = 0
    failed_count = 0
    
    for job in unprocessed_jobs:
        result_id = await process_video_job_task(job)
        
        if result_id:
            processed_count += 1
        else:
            failed_count += 1
    
    logger.info(
        f"Batch processing completed. Processed: {processed_count}, Failed: {failed_count}"
    )


@router.post("/process-all", response_model=BatchProcessResponse)
async def process_all_pending_videos(
    background_tasks: BackgroundTasks,
    request: ProcessJobsRequest = ProcessJobsRequest(),
) -> BatchProcessResponse:
    """
    Process all pending video jobs from PostgreSQL.
    
    Fetches videos from VideoDownloadJob table (status='done') and
    processes them through the analysis pipeline.
    
    Args:
        background_tasks: FastAPI background tasks
        request: Processing parameters (limit)
    
    Returns:
        Batch processing status
    """
    # Get count of pending jobs
    collection = get_analysis_collection()
    
    # Get already processed filenames
    processed_cursor = collection.find({}, {"video_filename": 1})
    processed_filenames = []
    async for doc in processed_cursor:
        if "video_filename" in doc:
            processed_filenames.append(doc["video_filename"])
    
    # Get unprocessed jobs count
    unprocessed_jobs = get_unprocessed_video_jobs(processed_filenames, limit=request.limit)
    total_jobs = len(unprocessed_jobs)
    
    if total_jobs == 0:
        return BatchProcessResponse(
            status="no_pending",
            total_jobs=0,
            message="No unprocessed video jobs found"
        )
    
    # Start background processing
    background_tasks.add_task(process_all_pending_jobs_task, request.limit)
    
    return BatchProcessResponse(
        status="processing_started",
        total_jobs=total_jobs,
        message=f"Started processing {total_jobs} video jobs in background"
    )


@router.post("/process-job/{job_id}", response_model=ProcessJobResponse)
async def process_single_job(
    job_id: str,
    background_tasks: BackgroundTasks,
) -> ProcessJobResponse:
    """
    Process a single video job from PostgreSQL by job ID.
    
    Args:
        job_id: UUID of the VideoDownloadJob in PostgreSQL
        background_tasks: FastAPI background tasks
    
    Returns:
        Processing status
    
    Raises:
        HTTPException: If job not found or invalid ID
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job_id format: {job_id}"
        )
    
    # Get job from PostgreSQL
    video_job = get_video_job_by_id(job_uuid)
    
    if not video_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video job not found or not completed: {job_id}"
        )
    
    # Check if video file exists
    if not Path(video_job.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found: {video_job.file_path}"
        )
    
    # Check if already processed
    collection = get_analysis_collection()
    existing = await collection.find_one({
        "postgresql_job_id": job_id
    })
    
    if existing:
        return ProcessJobResponse(
            job_id=job_id,
            status="already_processed",
            message="Video has already been processed",
            analysis_id=str(existing.get("_id"))
        )
    
    # Start background processing
    background_tasks.add_task(process_video_job_task, video_job)
    
    return ProcessJobResponse(
        job_id=job_id,
        status="processing_started",
        message=f"Started processing video: {Path(video_job.file_path).name}"
    )


@router.post("/process-company/{company_id}", response_model=BatchProcessResponse)
async def process_company_videos(
    company_id: str,
    background_tasks: BackgroundTasks,
) -> BatchProcessResponse:
    """
    Process all videos for a specific company from PostgreSQL.
    
    Args:
        company_id: UUID of the Company in PostgreSQL
        background_tasks: FastAPI background tasks
    
    Returns:
        Batch processing status
    
    Raises:
        HTTPException: If company not found or invalid ID
    """
    try:
        company_uuid = UUID(company_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company_id format: {company_id}"
        )
    
    # Get all video jobs for this company
    video_jobs = get_video_jobs_by_company(company_uuid)
    
    if not video_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed video jobs found for company: {company_id}"
        )
    
    # Filter out already processed
    collection = get_analysis_collection()
    unprocessed_jobs = []
    
    for job in video_jobs:
        existing = await collection.find_one({
            "postgresql_job_id": str(job.job_id)
        })
        if not existing:
            unprocessed_jobs.append(job)
    
    if not unprocessed_jobs:
        return BatchProcessResponse(
            status="all_processed",
            total_jobs=len(video_jobs),
            message=f"All {len(video_jobs)} videos for this company have already been processed"
        )
    
    # Start background processing for each video
    async def process_company_task():
        for job in unprocessed_jobs:
            await process_video_job_task(job)
    
    background_tasks.add_task(process_company_task)
    
    return BatchProcessResponse(
        status="processing_started",
        total_jobs=len(unprocessed_jobs),
        message=f"Started processing {len(unprocessed_jobs)} videos for company"
    )


@router.get("/pending-jobs")
async def list_pending_jobs(limit: int = 50) -> dict:
    """
    List all pending video jobs that need processing.
    
    Args:
        limit: Maximum number of jobs to return
    
    Returns:
        List of pending video jobs
    """
    collection = get_analysis_collection()
    
    # Get already processed filenames
    processed_cursor = collection.find({}, {"video_filename": 1, "postgresql_job_id": 1})
    processed_job_ids = set()
    async for doc in processed_cursor:
        if "postgresql_job_id" in doc:
            processed_job_ids.add(doc["postgresql_job_id"])
    
    # Get all completed jobs from PostgreSQL
    all_jobs = get_completed_video_jobs(limit=limit * 2)
    
    # Filter unprocessed
    pending_jobs = []
    for job in all_jobs:
        if str(job.job_id) not in processed_job_ids:
            pending_jobs.append({
                "job_id": str(job.job_id),
                "company_id": str(job.company_id),
                "company_name": job.company_name,
                "file_path": job.file_path,
                "platform": job.platform,
                "video_url": job.video_url,
                "view_count": job.view_count,
                "like_count": job.like_count,
            })
            if len(pending_jobs) >= limit:
                break
    
    return {
        "total_pending": len(pending_jobs),
        "jobs": pending_jobs
    }


# ==================== LEGACY FOLDER-BASED ENDPOINTS ====================

async def process_company_videos_task(company_name: str, company_id: str | None = None) -> None:
    """
    Background task to process all videos for a given company sequentially.
    (Legacy - folder-based processing)
    
    1. Scans the directory for video files
    2. Runs the pipeline for each video
    3. Saves results to MongoDB
    
    Args:
        company_name: Company name (for directory lookup)
        company_id: Company ID (ObjectId string) - required for pipeline
    """
    logger.info(f"Starting background task for company: {company_name}")
    
    # Validate company_id (required for AnalysisResult)
    if company_id is None:
        logger.error(f"company_id is required for processing. Skipping company: {company_name}")
        return
    
    try:
        # Validate ObjectId format
        ObjectId(company_id)
    except Exception as e:
        logger.error(f"Invalid company_id format: {company_id}. Error: {e}")
        return
    
    # Define the video directory using Pathlib
    company_video_dir = settings.VIDEO_DIR / company_name
    
    if not company_video_dir.exists():
        logger.error(f"Directory not found: {company_video_dir}")
        return
    
    if not company_video_dir.is_dir():
        logger.error(f"Path is not a directory: {company_video_dir}")
        return
    
    # Find all supported video files
    video_files: list[Path] = []
    for ext in SUPPORTED_VIDEO_FORMATS:
        video_files.extend(company_video_dir.glob(f"*{ext}"))
        video_files.extend(company_video_dir.glob(f"*{ext.upper()}"))
    
    if not video_files:
        logger.warning(f"No video files found in {company_video_dir}")
        return
    
    logger.info(f"Found {len(video_files)} video file(s) to process")
    
    collection = get_analysis_collection()
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    
    for video_path in video_files:
        try:
            # Check if already processed to avoid duplicate work
            existing = await collection.find_one({
                "company_name": company_name,
                "video_filename": video_path.name
            })
            
            if existing:
                logger.info(f"Skipping already processed video: {video_path.name}")
                skipped_count += 1
                continue
            
            # Run the synchronous pipeline in a threadpool
            # YOLO/Whisper CPU/GPU bound operations run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            
            # Process video through pipeline
            result = await loop.run_in_executor(
                None,
                pipeline_service.process_video,
                str(video_path),
                company_name,
                company_id,  # Already validated ObjectId string
                None,  # video_url (optional)
                None,  # num_vision_samples (None = auto: 1 frame per second, no limit)
                0.25,  # yolo_confidence (default)
                0.5,  # ocr_confidence (default)
            )
            
            # Save to MongoDB (Async I/O)
            # Exclude _id field so MongoDB can auto-generate it
            result_dict = result.model_dump(by_alias=True, exclude={'id'})
            insert_result = await collection.insert_one(result_dict)
            logger.info(f"Saved analysis for: {video_path.name}, ID: {insert_result.inserted_id}")
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process {video_path.name}: {e}", exc_info=True)
            failed_count += 1
            
            # Save error result to MongoDB
            try:
                error_result = AnalysisResult(
                    company_id=ObjectId(company_id),
                    company_name=company_name,
                    video_filename=video_path.name,
                    video_url=None,
                    metadata=VideoMetadata(),
                    segments=[],
                    all_objects=[],
                    all_ocr_text=[],
                    dominant_emotion=None,
                    status="failed",
                    error_message=f"Processing failed: {str(e)}"
                )
                # Exclude _id field so MongoDB can auto-generate it
                error_dict = error_result.model_dump(by_alias=True, exclude={'id'})
                await collection.insert_one(error_dict)
                logger.info(f"Saved error result for: {video_path.name}")
            except Exception as save_error:
                logger.error(f"Failed to save error result: {save_error}")
            
            # Continue processing other videos even if one fails
    
    logger.info(
        f"Background task completed for {company_name}. "
        f"Processed: {processed_count}, Skipped: {skipped_count}, Failed: {failed_count}"
    )


async def process_single_video_task(
    video_path: str | Path,
    company_name: str,
    company_id: str,
    video_url: str | None = None,
) -> ObjectId | None:
    """
    Background task to process a single video.
    (Legacy - file path based processing)
    
    Args:
        video_path: Path to the video file
        company_name: Company name
        company_id: Company ID (ObjectId string)
        video_url: Original video URL (optional)
    
    Returns:
        AnalysisResult ID (ObjectId) if successful, None if failed
    """
    logger.info(f"Starting single video processing: {video_path}")
    
    try:
        # Validate company_id
        ObjectId(company_id)
    except Exception as e:
        logger.error(f"Invalid company_id format: {company_id}. Error: {e}")
        return None
    
    video_path_obj = Path(video_path)
    
    if not video_path_obj.exists():
        logger.error(f"Video file not found: {video_path_obj}")
        return None
    
    collection = get_analysis_collection()
    
    try:
        # Check if already processed
        existing = await collection.find_one({
            "company_name": company_name,
            "video_filename": video_path_obj.name
        })
        
        if existing:
            logger.info(f"Video already processed: {video_path_obj.name}")
            return existing.get("_id")
        
        # Run pipeline in executor (CPU/GPU bound)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            pipeline_service.process_video,
            str(video_path_obj),
            company_name,
            company_id,
            video_url,
            None,  # num_vision_samples (None = auto: 1 frame per second, no limit)
            0.25,  # yolo_confidence
            0.5,  # ocr_confidence
        )
        
        # Save to MongoDB
        # Exclude _id field so MongoDB can auto-generate it
        result_dict = result.model_dump(by_alias=True, exclude={'id'})
        insert_result = await collection.insert_one(result_dict)
        logger.info(f"Saved analysis for: {video_path_obj.name}, ID: {insert_result.inserted_id}")
        
        return insert_result.inserted_id
        
    except Exception as e:
        logger.error(f"Failed to process video {video_path_obj.name}: {e}", exc_info=True)
        return None


@router.post("/process/{company_name}", status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    company_name: str,
    background_tasks: BackgroundTasks,
    company_id: str | None = None,
) -> dict[str, str | int]:
    """
    Trigger the analysis pipeline for a specific company folder.
    (Legacy - folder-based processing)
    
    This endpoint returns immediately (202 Accepted) while processing
    happens in the background.
    
    Args:
        company_name: Company name (used for directory lookup)
        background_tasks: FastAPI background tasks
        company_id: Company ID (ObjectId string) - required for processing
    
    Returns:
        Response with status and company info
    
    Raises:
        HTTPException: If company directory not found or company_id invalid
    """
    # Validate company_name (basic sanitization)
    if not company_name or not company_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name cannot be empty"
        )
    
    # Sanitize company_name (remove path traversal attempts)
    company_name = company_name.strip().replace("/", "").replace("\\", "")
    
    # Validate company_id (required)
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_id is required for processing"
        )
    
    try:
        ObjectId(company_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company_id format: {company_id}"
        )
    
    # Quick check if folder exists before accepting task
    target_dir = settings.VIDEO_DIR / company_name
    if not target_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company folder not found: videos/{company_name}"
        )
    
    if not target_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: videos/{company_name}"
        )
    
    # Add to background queue
    background_tasks.add_task(process_company_videos_task, company_name, company_id)
    
    return {
        "status": "Processing started",
        "company_name": company_name,
        "company_id": company_id,
        "message": "Check logs for progress. Videos are being processed in the background."
    }


@router.get("/status/{video_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(video_id: str) -> AnalysisStatusResponse:
    """
    Get the analysis status for a specific video.
    
    Args:
        video_id: Video analysis ID (MongoDB ObjectId)
    
    Returns:
        Analysis status information
    
    Raises:
        HTTPException: If video not found
    """
    try:
        object_id = ObjectId(video_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid video_id format: {video_id}"
        )
    
    collection = get_analysis_collection()
    result = await collection.find_one({"_id": object_id})
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video analysis not found: {video_id}"
        )
    
    # Calculate progress based on status and segments
    progress: float | None = None
    status_value = result.get("status", "unknown")
    
    if status_value == "completed":
        progress = 100.0
    elif status_value == "processing":
        # Estimate progress based on segments (if available)
        segments = result.get("segments", [])
        if segments:
            # Rough estimate: assume processing is ongoing
            progress = 50.0  # Placeholder - could be improved with actual progress tracking
        else:
            progress = 10.0  # Just started
    elif status_value == "failed":
        progress = 0.0
    
    return AnalysisStatusResponse(
        video_id=video_id,
        status=status_value,
        progress=progress,
        error_message=result.get("error_message")
    )


@router.post("/analyze", response_model=AnalysisStatusResponse)
async def analyze_video(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisStatusResponse:
    """
    Start analysis for a single video.
    (Legacy - supports both file path and MongoDB video collection)
    
    Args:
        request: Analysis request with video_id and company info
        background_tasks: FastAPI background tasks
    
    Returns:
        Initial status response with video_id
    
    Raises:
        HTTPException: If company_id invalid or video not found
    """
    # Validate company_id
    try:
        ObjectId(request.company_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company_id format: {request.company_id}"
        )
    
    # Find video file path
    # Option 1: video_id is a file path (relative to VIDEO_DIR)
    # Option 2: video_id is stored in videos collection
    # For now, assume video_id is a filename or relative path
    video_path = settings.VIDEO_DIR / request.video_id
    
    # If not found, try to find in videos collection
    if not video_path.exists():
        video_collection = get_video_collection()
        video_doc = await video_collection.find_one({"_id": ObjectId(request.video_id)})
        
        if video_doc:
            # Extract path from video document
            video_filename = video_doc.get("filename") or video_doc.get("video_filename")
            company_name = video_doc.get("company_name") or request.company_name
            
            if video_filename and company_name:
                video_path = settings.VIDEO_DIR / company_name / video_filename
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Video file not found: {request.video_id}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video not found: {request.video_id}"
            )
    
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found: {video_path}"
        )
    
    # Get company_name from request or extract from path
    company_name = request.company_name or video_path.parent.name
    
    # Add background task
    background_tasks.add_task(
        process_single_video_task,
        str(video_path),
        company_name,
        request.company_id,
        None,  # video_url (can be added to request later)
    )
    
    logger.info(
        f"Video analysis started: video_id={request.video_id}, "
        f"company_id={request.company_id}, path={video_path}"
    )
    
    return AnalysisStatusResponse(
        video_id=request.video_id,
        status="processing",
        progress=0.0,
        error_message=None
    )
