"""
Vision analysis service using YOLOv8 and EasyOCR.

This service performs visual analysis on video segments:
- Object detection with YOLOv8
- Text extraction with EasyOCR

Optimized for RTX 4060 (8GB VRAM).

NOTE: This operation is CPU/GPU intensive, so it's defined as 'def' (synchronous).
FastAPI runs it in a threadpool, preventing event loop blocking.
"""
from pathlib import Path
from typing import Literal
import logging
import torch
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr

from modules.video_processor_agent.models.models import VideoSegment

logger = logging.getLogger(__name__)


class VisionService:
    """
    YOLO and EasyOCR model wrapper for vision analysis.
    
    Manages a global instance using Singleton pattern.
    Models are loaded lazily on first use.
    """
    
    def __init__(self):
        """VisionService constructor. Models are not loaded yet (lazy loading)."""
        self.yolo_model: YOLO | None = None
        self.ocr_reader: easyocr.Reader | None = None
        self._device: str | None = None
        self._yolo_model_name: str = "yolov8m.pt"
    
    def _load_models(self) -> None:
        """
        Loads YOLO and EasyOCR models (lazy loading).
        
        RTX 4060 optimization:
        - YOLOv8m (medium): Balanced speed and accuracy, fits in 8GB VRAM
        - EasyOCR GPU: CUDA usage
        
        Raises:
            RuntimeError: If models cannot be loaded
            OSError: If GPU is not accessible
        """
        if self.yolo_model is not None and self.ocr_reader is not None:
            return
        
        try:
            logger.info("Loading vision models (YOLO + OCR)...")
            
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            
            if self._device == "cuda":
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
                logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
            
            logger.info(f"Loading YOLO model: {self._yolo_model_name}")
            self.yolo_model = YOLO(self._yolo_model_name)
            self.yolo_model.to(self._device)
            
            logger.info("Loading EasyOCR model (tr, en)...")
            self.ocr_reader = easyocr.Reader(
                ['tr', 'en'],
                gpu=(self._device == 'cuda'),
                verbose=False
            )
            
            logger.info(f"Vision models ready. Device: {self._device}")
            
        except OSError as e:
            logger.error(f"GPU/Model access error: {e}")
            raise RuntimeError(f"Failed to load vision models: {e}") from e
        except Exception as e:
            logger.error(f"Vision model loading error: {e}")
            raise RuntimeError(f"Unexpected model loading error: {e}") from e
    
    def extract_frame(
        self,
        video_path: str | Path,
        timestamp: float,
    ) -> np.ndarray | None:
        """
        Extracts a frame from the video at the specified timestamp.
        
        Args:
            video_path: Path to the video file
            timestamp: Time in seconds to extract the frame
        
        Returns:
            Frame (numpy array) or None (on error)
        
        Raises:
            FileNotFoundError: If video file is not found
            ValueError: If video cannot be opened
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Video cannot be opened: {video_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 1:
                logger.warning(f"Invalid or low FPS value: {fps}. Using default 30 FPS.")
                fps = 30.0
            
            frame_id = int(fps * timestamp)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_id >= total_frames:
                frame_id = total_frames - 1
            if frame_id < 0:
                frame_id = 0
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            
            if not ret or frame is None:
                return None
            
            return frame
            
        finally:
            cap.release()
    
    def detect_objects(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.25,
    ) -> list[str]:
        """
        Detects objects in the frame using YOLO.
        
        Args:
            frame: Frame to analyze (numpy array)
            confidence_threshold: Minimum confidence value (0.0-1.0)
        
        Returns:
            List of detected object names (unique)
        """
        if self.yolo_model is None:
            self._load_models()
        
        yolo_res = self.yolo_model(frame, verbose=False, conf=confidence_threshold)[0]
        
        detected_objects: set[str] = set()
        for box in yolo_res.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            if confidence >= confidence_threshold:
                class_name = self.yolo_model.names[class_id]
                detected_objects.add(class_name)
        
        return sorted(list(detected_objects))
    
    def extract_text(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.5,
    ) -> list[str]:
        """
        Extracts text from the frame using EasyOCR.
        
        Args:
            frame: Frame to analyze (numpy array)
            confidence_threshold: Minimum confidence value (0.0-1.0)
        
        Returns:
            List of detected texts
        """
        if self.ocr_reader is None:
            self._load_models()
        
        ocr_results = self.ocr_reader.readtext(frame, detail=1)
        
        extracted_texts: list[str] = []
        for detection in ocr_results:
            if len(detection) >= 3:
                text = detection[1].strip()
                confidence = detection[2] if len(detection) > 2 else 1.0
                
                if confidence >= confidence_threshold and text:
                    extracted_texts.append(text)
        
        return extracted_texts
    
    def analyze_segment(
        self,
        video_path: str | Path,
        segment: VideoSegment,
        num_samples: int | None = None,
        yolo_confidence: float = 0.25,
        ocr_confidence: float = 0.5,
    ) -> VideoSegment:
        """
        Analyzes a video segment and updates the VideoSegment.
        
        Args:
            video_path: Path to the video file
            segment: VideoSegment to analyze (in-place update)
            num_samples: Number of frames to analyze. If None, automatically calculates
                        based on segment duration (1 frame per second, minimum 1).
            yolo_confidence: YOLO minimum confidence threshold
            ocr_confidence: OCR minimum confidence threshold
        
        Returns:
            Updated VideoSegment (visual_objects and ocr_text filled)
        
        Raises:
            FileNotFoundError: If video file is not found
            ValueError: If segment is invalid
        """
        if segment.start_time >= segment.end_time:
            raise ValueError(
                f"Invalid segment: start_time ({segment.start_time}) >= end_time ({segment.end_time})"
            )
        
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if self.yolo_model is None or self.ocr_reader is None:
            self._load_models()
        
        segment_duration = segment.end_time - segment.start_time
        
        # Auto-calculate num_samples based on segment duration if not provided
        if num_samples is None:
            # Every 2 seconds 1 frame, minimum 1 frame, maximum 5 frames per segment
            # This balances speed and coverage
            calculated = max(1, int(segment_duration / 2))
            num_samples = min(calculated, 5)  # Cap at 5 frames max
            logger.debug(
                f"Auto-calculated {num_samples} frames for segment "
                f"({segment_duration:.2f}s duration, calculated: {calculated})"
            )
        
        if num_samples == 1:
            timestamps = [(segment.start_time + segment.end_time) / 2]
        elif num_samples == 3:
            timestamps = [
                segment.start_time + segment_duration * 0.25,
                segment.start_time + segment_duration * 0.50,
                segment.start_time + segment_duration * 0.75,
            ]
        else:
            # Distribute frames evenly across segment
            timestamps = [
                segment.start_time + (segment_duration * i / (num_samples - 1))
                for i in range(num_samples)
            ]
        
        all_objects: set[str] = set()
        all_ocr_texts: set[str] = set()
        
        for timestamp in timestamps:
            frame = self.extract_frame(video_path, timestamp)
            if frame is None:
                logger.warning(f"Frame could not be read: {video_path.name} @ {timestamp:.2f}s")
                continue
            
            objects = self.detect_objects(frame, confidence_threshold=yolo_confidence)
            all_objects.update(objects)
            
            ocr_texts = self.extract_text(frame, confidence_threshold=ocr_confidence)
            all_ocr_texts.update(ocr_texts)
        
        segment.visual_objects = sorted(list(all_objects))
        segment.ocr_text = sorted(list(all_ocr_texts))
        
        logger.debug(
            f"Segment analysis completed: "
            f"{len(segment.visual_objects)} objects, {len(segment.ocr_text)} OCR texts"
        )
        
        return segment
    
    def analyze_segments(
        self,
        video_path: str | Path,
        segments: list[VideoSegment],
        num_samples: int = 1,
        yolo_confidence: float = 0.25,
        ocr_confidence: float = 0.5,
    ) -> list[VideoSegment]:
        """
        Analyzes multiple segments in batch.
        
        Args:
            video_path: Path to the video file
            segments: List of VideoSegments to analyze
            num_samples: Number of frames to analyze per segment
            yolo_confidence: YOLO minimum confidence threshold
            ocr_confidence: OCR minimum confidence threshold
        
        Returns:
            Updated VideoSegment list
        """
        logger.info(f"Analyzing {len(segments)} segments...")
        
        for i, segment in enumerate(segments, 1):
            try:
                self.analyze_segment(
                    video_path,
                    segment,
                    num_samples=num_samples,
                    yolo_confidence=yolo_confidence,
                    ocr_confidence=ocr_confidence,
                )
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(segments)} segments analyzed")
            except Exception as e:
                logger.error(f"Segment {i} analysis error: {e}")
                continue
        
        logger.info(f"{len(segments)} segment analysis completed")
        return segments
    
    def get_model_info(self) -> dict[str, str | bool | None]:
        """
        Returns model information.
        
        Returns:
            Model information (device, yolo_model, loaded)
        """
        return {
            "yolo_model": self._yolo_model_name,
            "device": self._device,
            "yolo_loaded": self.yolo_model is not None,
            "ocr_loaded": self.ocr_reader is not None,
        }


# ==================== GLOBAL SINGLETON INSTANCE ====================
# Initialize service (lazy loading - loaded on first use)
vision_service = VisionService()
