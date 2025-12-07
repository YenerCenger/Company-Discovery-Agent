import re
from typing import List
from modules.report_analysis_agent.models.video_model import VideoInput, VideoPreprocessed, VideoData
from collections import Counter


def calculate_viral_score(view_count: int, like_count: int, comment_count: int) -> float:
    """
    Calculate viral score from engagement metrics.
    Simple formula: weighted combination of views, likes, and comments
    """
    if view_count == 0:
        return 0.0
    
    # Normalize metrics (simple approach)
    like_ratio = like_count / max(view_count, 1)
    comment_ratio = comment_count / max(view_count, 1)
    
    # Weighted score (views matter, but engagement ratio is more important)
    # Max score is 1.0
    score = min(1.0, (like_ratio * 0.6 + comment_ratio * 0.4) * 10)
    
    return round(score, 2)


def convert_video_data_to_input(video_data: VideoData) -> VideoInput:
    """
    Convert VideoData (from API) to VideoInput (internal format)
    """
    # Combine all segments' transcripts
    transcript = " ".join([seg.transcript for seg in video_data.segments if seg.transcript])
    
    # Combine all visual objects from segments and all_objects
    all_visual_objects = set()
    for seg in video_data.segments:
        all_visual_objects.update(seg.visual_objects)
    all_visual_objects.update(video_data.all_objects)
    objects = list(all_visual_objects)
    
    # Combine all OCR texts from segments and all_ocr_text
    all_ocr_texts = set()
    for seg in video_data.segments:
        all_ocr_texts.update(seg.ocr_text)
    all_ocr_texts.update(video_data.all_ocr_text)
    ocr_text = " ".join(list(all_ocr_texts)) if all_ocr_texts else None
    
    # Combine all key entities from segments
    all_entities = set()
    for seg in video_data.segments:
        all_entities.update(seg.key_entities)
    key_entities = list(all_entities)
    
    # Calculate viral score from metadata
    viral_score = calculate_viral_score(
        video_data.metadata.view_count,
        video_data.metadata.like_count,
        video_data.metadata.comment_count
    )
    
    # Use dominant_emotion or default to neutral
    emotional_tone = video_data.dominant_emotion or "neutral"
    
    # Generate script from segments (simple approach)
    generated_script = " - ".join([
        f"{seg.start_time:.1f}s-{seg.end_time:.1f}s" 
        for seg in video_data.segments
    ])
    
    return VideoInput(
        id=video_data.id,
        url=video_data.video_url,
        transcript=transcript,
        key_entities=key_entities,
        objects=objects,
        ocr_text=ocr_text,
        emotional_tone=emotional_tone,
        viral_score=viral_score,
        generated_script=generated_script,
        review_timestamp=video_data.processed_at,
        platform=video_data.metadata.platform,
        view_count=video_data.metadata.view_count,
        like_count=video_data.metadata.like_count,
        comment_count=video_data.metadata.comment_count,
        company_name=video_data.company_name
    )


def preprocess_videos(videos: List[VideoInput]) -> List[VideoPreprocessed]:
    """
    Preprocess videos:
    - Drop incomplete videos
    - Text normalization
    - Transcript tokenization
    - Entity frequency extraction
    - Basic cleanup
    """
    preprocessed = []
    
    for video in videos:
        # Check if video is complete (has essential fields)
        is_complete = (
            video.transcript and len(video.transcript.strip()) > 0 and
            video.viral_score is not None and
            len(video.key_entities) > 0 or len(video.objects) > 0
        )
        
        if not is_complete:
            continue
        
        # Text normalization
        normalized_transcript = normalize_text(video.transcript)
        
        # Tokenization (simple word tokenization)
        tokens = tokenize_text(normalized_transcript)
        
        # Entity frequency extraction
        entity_frequency = extract_entity_frequency(video.key_entities, tokens)
        
        # Normalize OCR text if present
        normalized_ocr = normalize_text(video.ocr_text) if video.ocr_text else None
        
        preprocessed_video = VideoPreprocessed(
            id=video.id,
            url=video.url,
            transcript=normalized_transcript,
            transcript_tokens=tokens,
            key_entities=video.key_entities,
            entity_frequency=entity_frequency,
            objects=video.objects,
            ocr_text=normalized_ocr,
            emotional_tone=video.emotional_tone.lower().strip(),
            viral_score=video.viral_score,
            generated_script=video.generated_script,
            review_timestamp=video.review_timestamp,
            is_complete=True,
            platform=video.platform,
            view_count=video.view_count,
            like_count=video.like_count,
            comment_count=video.comment_count,
            company_name=video.company_name
        )
        
        preprocessed.append(preprocessed_video)
    
    return preprocessed


def normalize_text(text: str) -> str:
    """Normalize text: remove extra whitespace, lowercase, clean special chars"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:()\-\']', '', text)
    # Strip
    text = text.strip()
    
    return text


def tokenize_text(text: str) -> List[str]:
    """Simple word tokenization"""
    if not text:
        return []
    
    # Split by whitespace and filter empty strings
    tokens = [token.lower() for token in text.split() if token.strip()]
    return tokens


def extract_entity_frequency(entities: List[str], tokens: List[str]) -> dict:
    """Extract frequency of entities in tokens"""
    entity_freq = {}
    token_counter = Counter(tokens)
    
    for entity in entities:
        entity_lower = entity.lower()
        # Count occurrences in tokens
        count = sum(1 for token in tokens if entity_lower in token or token in entity_lower)
        entity_freq[entity] = count
    
    return entity_freq





