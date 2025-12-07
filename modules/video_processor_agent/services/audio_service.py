"""
Audio transcription service using Faster-Whisper.

This service extracts speech transcripts from video files.
Optimized for RTX 4060 (8GB VRAM).

NOTE: This operation is CPU/GPU intensive, so it's defined as 'def' (synchronous).
FastAPI runs it in a threadpool, preventing event loop blocking.
"""
from pathlib import Path
from typing import Literal
import logging
import torch
from faster_whisper import WhisperModel

from modules.video_processor_agent.core.config import settings
from modules.video_processor_agent.models.models import VideoSegment

logger = logging.getLogger(__name__)


class AudioService:
    """
    Whisper model wrapper for audio transcription.
    
    Manages a global instance using Singleton pattern.
    Model is loaded lazily on first use.
    """
    
    def __init__(self):
        """AudioService constructor. Model is not loaded yet (lazy loading)."""
        self.model: WhisperModel | None = None
        self._device: str | None = None
        self._compute_type: str | None = None
    
    def _load_model(self) -> None:
        """
        Loads the model (lazy loading).
        
        RTX 4060 optimization:
        - device='cuda' (GPU usage)
        - compute_type='float16' (to fit in 8GB VRAM)
        
        Raises:
            RuntimeError: If model cannot be loaded
            OSError: If GPU is not accessible
        """
        if self.model is not None:
            return
        
        try:
            logger.info(f"Loading Whisper model ({settings.WHISPER_MODEL_SIZE})...")
            
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._compute_type = "float16" if self._device == "cuda" else "int8"
            
            if self._device == "cuda":
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
                logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
            
            self.model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=self._device,
                compute_type=self._compute_type,
                download_root=None,
            )
            
            logger.info(
                f"Whisper model loaded. "
                f"Device: {self._device}, Compute: {self._compute_type}"
            )
            
        except OSError as e:
            logger.error(f"GPU/Model access error: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}") from e
        except Exception as e:
            logger.error(f"Model loading error: {e}")
            raise RuntimeError(f"Unexpected model loading error: {e}") from e
    
    def transcribe(
        self,
        video_path: str | Path,
        language: str | None = None,
        auto_detect_language: bool = True,
        min_segment_duration: float = 0.5,
    ) -> list[VideoSegment]:
        """
        Transcribes audio from video and returns a VideoSegment list.
        
        Args:
            video_path: Path to the video file (str or Path)
            language: Language code (e.g., "tr", "en"). None for auto-detection.
            auto_detect_language: Whether to perform automatic language detection
            min_segment_duration: Minimum segment duration (seconds). Shorter segments are filtered.
        
        Returns:
            VideoSegment list (contains start_time, end_time, transcript)
        
        Raises:
            FileNotFoundError: If video file is not found
            ValueError: If video file is invalid
            RuntimeError: If transcription fails
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if not video_path.is_file():
            raise ValueError(f"Invalid file path: {video_path}")
        
        if self.model is None:
            self._load_model()
        
        logger.info(f"Extracting transcript: {video_path.name}")
        
        try:
            segments, info = self.model.transcribe(
                str(video_path),
                beam_size=5,
                language=language if not auto_detect_language else None,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
            )
            
            detected_language = info.language if hasattr(info, 'language') else language or "unknown"
            logger.info(f"Detected language: {detected_language}")
            logger.info(f"Video duration: {info.duration:.2f} seconds")
            
            result: list[VideoSegment] = []
            for segment in segments:
                segment_duration = segment.end - segment.start
                if segment_duration < min_segment_duration:
                    continue
                
                transcript_text = segment.text.strip()
                if not transcript_text:
                    continue
                
                result.append(
                    VideoSegment(
                        start_time=round(segment.start, 2),
                        end_time=round(segment.end, 2),
                        transcript=transcript_text,
                        visual_objects=[],
                        ocr_text=[],
                        sentiment=None,
                        key_entities=[],
                    )
                )
            
            logger.info(
                f"Transcription completed. "
                f"{len(result)} segments found (min {min_segment_duration}s)"
            )
            
            return result
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise RuntimeError(f"Failed to get video transcript: {e}") from e
    
    def get_model_info(self) -> dict[str, str | None]:
        """
        Returns model information.
        
        Returns:
            Model information (device, compute_type, model_size)
        """
        return {
            "model_size": settings.WHISPER_MODEL_SIZE,
            "device": self._device,
            "compute_type": self._compute_type,
            "loaded": self.model is not None,
        }


# ==================== GLOBAL SINGLETON INSTANCE ====================
# Initialize service (lazy loading - loaded on first use)
audio_service = AudioService()
