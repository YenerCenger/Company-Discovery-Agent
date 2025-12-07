import json
import logging
from typing import Dict, Any, List
from modules.report_analysis_agent.models.video_model import VideoPreprocessed
from modules.report_analysis_agent.services.llm_service import run_ollama_json, check_model_available, repair_interpretation_json, get_available_model

logger = logging.getLogger(__name__)


def llm_interpretation(stats: Dict[str, Any], videos: List[VideoPreprocessed]) -> Dict[str, Any]:
    """
    LLM Layer 1 - Interpretation using DeepSeek R1
    
    Analyzes:
    - Common patterns in winning videos
    - Hook/pattern extraction
    - CTA structure analysis
    - Target audience content structure
    - Visual structure analysis
    """
    # Use any available LLM model (gemma, deepseek, qwen, llama)
    model = None
    fallback = None
    
    if check_model_available("gemma"):
        model = get_available_model("gemma")
        logger.info(f"Using {model} (gemma)")
    elif check_model_available("deepseek-r1"):
        model = get_available_model("deepseek-r1")
        logger.info(f"Using {model} (deepseek)")
    elif check_model_available("qwen2.5"):
        model = get_available_model("qwen2.5")
        logger.info(f"Using {model} (qwen)")
    elif check_model_available("llama"):
        model = get_available_model("llama")
        logger.info(f"Using {model} (llama)")
    else:
        raise Exception("No suitable model available. Install via: ollama pull gemma:7b")
    
    # Prepare context for LLM - TÜM VERİYİ KULLAN
    context = prepare_interpretation_context(stats, videos)
    
    # Detailed prompt with all data - strict JSON, English-only content
    prompt = f"""Analyze these successful real estate videos and extract patterns:

{json.dumps(context, ensure_ascii=False, indent=2)}

Analyze:
1. What hooks work best (first 3 seconds)?
2. What emotional triggers drive engagement?
3. What content structure is most effective?
4. What visual elements appear in top videos?
5. What CTA types and language work best?

Return ONLY valid JSON (no explanations, no markdown). The entire JSON content MUST be in English.
Use STRICT JSON syntax:
- All property names MUST be in double quotes.
- All string values MUST be in double quotes.
- No comments.
- No trailing commas.
- Arrays MUST contain ONLY values (strings/objects), NEVER key names.
- Do NOT include example code fences such as ```json.
Do NOT add any extra fields beyond this schema:
{{
  "winning_patterns": {{
    "common_hooks": ["specific hook 1", "specific hook 2"],
    "emotional_triggers": ["trigger 1", "trigger 2"],
    "content_structure": "description of structure",
    "visual_elements": "description of visuals"
  }},
  "cta_analysis": {{
    "effective_cta_types": ["CTA type 1", "CTA type 2"],
    "cta_placement": "where CTAs work best",
    "cta_language": "effective CTA language patterns"
  }},
  "target_audience_insights": {{
    "content_preferences": "what audience prefers",
    "optimal_length": "best video length",
    "tone_preferences": "preferred tone"
  }},
  "key_findings": ["finding 1", "finding 2", "finding 3"]
}}"""

    try:
        result = run_ollama_json(
            model,
            prompt,
            fallback_model=fallback,
            max_retries=0,  # No retries - just use fallback
            timeout=180,  # 180s timeout - increased for full data processing
            num_predict=2000,  # 2000 tokens - enough for full JSON response
        )

        # If parse error, try JSON repair step
        if "error" in result and result.get("parse_error"):
            logger.error(f"LLM interpretation parse error, attempting repair: {result.get('error')}")
            raw_text = result.get("raw_response", "")
            if raw_text:
                repaired = repair_interpretation_json(raw_text)
                if "error" in repaired and repaired.get("parse_error"):
                    logger.error(f"JSON repair (interpretation) also failed: {repaired.get('error')}")
                    return result
                logger.info("✅ JSON repair successful for interpretation")
                return repaired
            return result

        return result
    except Exception as e:
        logger.error(f"LLM interpretation failed: {str(e)}", exc_info=True)
        # Return error in structured format - NO defaults
        return {
            "error": str(e),
            "winning_patterns": {},
            "cta_analysis": {},
            "target_audience_insights": {},
            "key_findings": []
        }


def prepare_interpretation_context(stats: Dict[str, Any], videos: List[VideoPreprocessed]) -> Dict[str, Any]:
    """
    Prepare context with ALL data for meaningful analysis
    """
    # Top 5 videos for analysis - TÜM VERİYİ KULLAN
    sorted_videos = sorted(videos, key=lambda x: x.viral_score, reverse=True)[:5]
    
    # Full video data - TÜM ALANLARI KULLAN
    compact_videos = [
        {
            "id": v.id,
            "viral_score": v.viral_score,
            "transcript": v.transcript,  # TÜM TRANSCRIPT
            "entities": v.key_entities,  # TÜM ENTITIES
            "objects": v.objects,         # TÜM OBJECTS
            "tone": v.emotional_tone,
            "platform": v.platform,
            "engagement": {
                "views": v.view_count,
                "likes": v.like_count,
                "comments": v.comment_count
            }
        }
        for v in sorted_videos
    ]
    
    return {
        "total_videos": stats.get("total_videos", 0),
        "avg_viral_score": round(stats.get("viral_score_stats", {}).get("mean", 0), 2),
        "top_viral_score": round(stats.get("viral_score_stats", {}).get("max", 0), 2),
        "tone_distribution": stats.get("emotional_tone_distribution", {}),
        "top_videos": compact_videos
    }
