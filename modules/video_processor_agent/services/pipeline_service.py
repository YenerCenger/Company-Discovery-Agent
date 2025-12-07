"""
Pipeline service - Orchestrates video analysis workflow.

This service coordinates audio transcription, vision analysis, and
combines results into structured AnalysisResult objects.

Flow:
1. Audio transcription (Whisper) → VideoSegment list
2. Vision analysis (YOLO + OCR) → Update segments
3. Aggregate fields calculation
4. Package into AnalysisResult
"""
import logging
from pathlib import Path
from typing import Literal
from bson import ObjectId

try:
    import cv2
except ImportError:
    cv2 = None

from modules.video_processor_agent.services.audio_service import audio_service
from modules.video_processor_agent.services.vision_service import vision_service
from modules.video_processor_agent.models.models import AnalysisResult, VideoSegment, VideoMetadata

# Logger setup (no global basicConfig)
logger = logging.getLogger(__name__)

if cv2 is None:
    logger.warning("cv2 (opencv-python) not installed. Video duration detection will be limited.")


class PipelineService:
    """
    Video analysis pipeline orchestrator.
    
    Coordinates multiple AI services to produce complete video analysis.
    """
    
    def process_video(
        self,
        video_path: str | Path,
        company_name: str,
        company_id: str | ObjectId | None = None,
        video_url: str | None = None,
        num_vision_samples: int | None = None,
        yolo_confidence: float = 0.25,
        ocr_confidence: float = 0.5,
    ) -> AnalysisResult:
        """
        Orchestrates the full analysis pipeline for a single video.
        
        Flow:
        1. Extract Audio → Transcribe & Segment (Master Timeline)
        2. For each segment → Extract Frame → YOLO & OCR (Visual Context)
        3. Calculate aggregate fields
        4. Combine into structured AnalysisResult
        
        Args:
            video_path: Path to the video file
            company_name: Name of the company/folder
            company_id: Company ID (ObjectId string or ObjectId) - required for AnalysisResult
            video_url: Original video URL (optional)
            num_vision_samples: Number of frames to analyze per segment. If None, automatically
                                calculates based on segment duration (1 frame per 2 seconds, 
                                minimum 1, maximum 5 per segment).
            yolo_confidence: YOLO minimum confidence threshold
            ocr_confidence: OCR minimum confidence threshold
        
        Returns:
            AnalysisResult: Pydantic model containing full analysis
        
        Raises:
            FileNotFoundError: Video file not found
            ValueError: Invalid parameters
            RuntimeError: Processing failed
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if not video_path.is_file():
            raise ValueError(f"Path is not a file: {video_path}")
        
        # Convert company_id to ObjectId if string
        if company_id is None:
            raise ValueError("company_id is required for AnalysisResult")
        
        if isinstance(company_id, str):
            try:
                company_id = ObjectId(company_id)
            except Exception as e:
                raise ValueError(f"Invalid company_id format: {company_id}") from e
        
        logger.info(f"Pipeline started for video: {video_path.name}")
        
        # 1. Audio Processing (The Master Timeline)
        # We use audio segments to define 'when' to look at the video.
        # If no audio, create time-based segments for visual-only analysis
        segments: list[VideoSegment] = []
        has_audio = False
        
        try:
            segments = audio_service.transcribe(
                video_path,
                auto_detect_language=True,
                min_segment_duration=0.5,
            )
            
            if segments:
                has_audio = True
                logger.info(f"Audio transcription completed: {len(segments)} segments")
            else:
                logger.warning(f"No audio segments found in video: {video_path.name}. Will use visual-only analysis.")
                # For videos without audio, create time-based segments
                # Get video duration and create segments every 5 seconds
                try:
                    if cv2 is None:
                        raise ImportError("cv2 not available")
                    
                    cap = cv2.VideoCapture(str(video_path))
                    if not cap.isOpened():
                        raise ValueError("Could not open video file")
                    
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    duration = frame_count / fps if fps > 0 else 0
                    cap.release()
                    
                    if duration > 0:
                        # Create segments every 5 seconds
                        segment_duration = 5.0
                        num_segments = int(duration / segment_duration) + 1
                        
                        for i in range(num_segments):
                            start_time = i * segment_duration
                            end_time = min((i + 1) * segment_duration, duration)
                            if end_time > start_time:
                                segments.append(VideoSegment(
                                    start_time=start_time,
                                    end_time=end_time,
                                    transcript="",  # No audio
                                ))
                        logger.info(f"Created {len(segments)} time-based segments for visual-only analysis")
                    else:
                        logger.warning("Could not determine video duration. Using default 10-second segment.")
                        segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
                except Exception as e:
                    logger.warning(f"Could not create time-based segments: {e}. Using default segment.")
                    segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}. Will use visual-only analysis.", exc_info=True)
            # Try to create time-based segments even if audio processing fails
            try:
                if cv2 is not None:
                    cap = cv2.VideoCapture(str(video_path))
                    if cap.isOpened():
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        duration = frame_count / fps if fps > 0 else 0
                        cap.release()
                        
                        if duration > 0:
                            segment_duration = 5.0
                            num_segments = int(duration / segment_duration) + 1
                            for i in range(num_segments):
                                start_time = i * segment_duration
                                end_time = min((i + 1) * segment_duration, duration)
                                if end_time > start_time:
                                    segments.append(VideoSegment(
                                        start_time=start_time,
                                        end_time=end_time,
                                        transcript="",
                                    ))
                        else:
                            segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
                    else:
                        segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
                else:
                    segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
            except Exception as seg_error:
                logger.warning(f"Could not create time-based segments: {seg_error}")
                segments = [VideoSegment(start_time=0.0, end_time=10.0, transcript="")]
        
        if not segments:
            # Last resort: return error
            return self._create_empty_result(
                video_path,
                company_name,
                company_id,
                video_url,
                error_message="Could not process video: no audio and could not determine duration"
            )
        
        # 2. Visual Processing (Synced with Audio)
        logger.info(f"Starting visual analysis for {len(segments)} segments...")
        
        processed_count = 0
        failed_count = 0
        
        for i, segment in enumerate(segments):
            try:
                # Analyze the visual content for this specific timeframe
                # This calls YOLO and OCR on frames within the segment
                vision_service.analyze_segment(
                    video_path,
                    segment,
                    num_samples=num_vision_samples,
                    yolo_confidence=yolo_confidence,
                    ocr_confidence=ocr_confidence,
                )
                processed_count += 1
                
                # Log progress every 10 segments
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"Visual analysis progress: {i + 1}/{len(segments)} segments processed"
                    )
                    
            except Exception as e:
                logger.warning(
                    f"Visual analysis failed for segment {i + 1} "
                    f"({segment.start_time:.2f}s - {segment.end_time:.2f}s): {e}"
                )
                failed_count += 1
                # Continue processing other segments even if one fails
                continue
        
        logger.info(
            f"Visual analysis completed: {processed_count} succeeded, {failed_count} failed"
        )
        
        # 3. Calculate Aggregate Fields
        all_objects: set[str] = set()
        all_ocr_texts: set[str] = set()
        sentiment_counts: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}
        
        for segment in segments:
            all_objects.update(segment.visual_objects)
            all_ocr_texts.update(segment.ocr_text)
            
            if segment.sentiment:
                sentiment_counts[segment.sentiment] = sentiment_counts.get(
                    segment.sentiment, 0
                ) + 1
        
        # Determine dominant emotion
        dominant_emotion: Literal["positive", "negative", "neutral"] | None = None
        if any(sentiment_counts.values()):
            dominant_emotion = max(sentiment_counts, key=sentiment_counts.get)  # type: ignore
        
        # 4. Final Packaging
        # Create the top-level result object
        result = AnalysisResult(
            company_id=company_id,
            company_name=company_name,
            video_filename=video_path.name,
            video_url=video_url,
            metadata=VideoMetadata(
                platform="instagram",  # Default assumption (Agent 1 would provide this)
                view_count=0,  # Placeholder
                like_count=0,  # Placeholder
                comment_count=0,  # Placeholder
            ),
            segments=segments,
            all_objects=sorted(list(all_objects)),
            all_ocr_text=sorted(list(all_ocr_texts)),
            dominant_emotion=dominant_emotion,
            status="completed",
        )
        
        logger.info(
            f"Pipeline finished for {video_path.name}. "
            f"Total segments: {len(segments)}, "
            f"Objects: {len(all_objects)}, "
            f"OCR texts: {len(all_ocr_texts)}"
        )
        
        return result
    
    def _create_empty_result(
        self,
        video_path: Path,
        company_name: str,
        company_id: ObjectId,
        video_url: str | None,
        error_message: str,
    ) -> AnalysisResult:
        """
        Create an empty AnalysisResult with error status.
        
        Used when processing fails at an early stage.
        """
        return AnalysisResult(
            company_id=company_id,
            company_name=company_name,
            video_filename=video_path.name,
            video_url=video_url,
            metadata=VideoMetadata(),
            segments=[],
            all_objects=[],
            all_ocr_text=[],
            dominant_emotion=None,
            status="failed",
            error_message=error_message,
        )


# ==================== GLOBAL SINGLETON INSTANCE ====================
# Singleton pattern: Tüm uygulama boyunca tek bir pipeline instance
pipeline_service = PipelineService()
