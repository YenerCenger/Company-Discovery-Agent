import json
import logging
from typing import Dict, Any
from modules.report_analysis_agent.models.video_model import Company, Profile
from modules.report_analysis_agent.services.llm_service import run_ollama_json, check_model_available, repair_recommendation_json, get_available_model

logger = logging.getLogger(__name__)


def llm_recommendation(
    interpretation_output: Dict[str, Any],
    company: Company,
    profiles: list[Profile]
) -> Dict[str, Any]:
    """
    LLM Layer 2 - Recommendation.
    
    Generates:
    - Viral script recommendations
    - CTA variants
    - Pacing & editing recommendations
    - 20-30 sec real estate video format recommendations
    - City-specific content strategy (e.g., İzmir)
    """
    # Use any available LLM model (gemma, llama, qwen, deepseek)
    model = None
    fallback_model = None
    
    if check_model_available("gemma"):
        model = get_available_model("gemma")
        logger.info(f"Using {model} (gemma)")
    elif check_model_available("llama3.2"):
        model = get_available_model("llama3.2")
        logger.info(f"Using {model} (llama3.2)")
    elif check_model_available("qwen2.5"):
        model = get_available_model("qwen2.5")
        logger.info(f"Using {model} (qwen)")
    elif check_model_available("deepseek-r1"):
        model = get_available_model("deepseek-r1")
        logger.info(f"Using {model} (deepseek)")
    elif check_model_available("llama"):
        model = get_available_model("llama")
        logger.info(f"Using {model} (llama)")
    else:
        raise Exception("No suitable model available. Install via: ollama pull gemma:7b")
    
    # Use FULL interpretation context
    context = {
        "company": company.name,
        "hooks": interpretation_output.get("winning_patterns", {}).get("common_hooks", []),
        "triggers": interpretation_output.get("winning_patterns", {}).get("emotional_triggers", []),
        "findings": interpretation_output.get("key_findings", []),
        "cta_analysis": interpretation_output.get("cta_analysis", {}),
        "target_audience": interpretation_output.get("target_audience_insights", {})
    }
    
    # Detailed prompt with all data - strict JSON, English-only content
    prompt = f"""You are an expert real-estate marketing strategist.
Using the analysis below, create marketing recommendations for {company.name}:

{json.dumps(context, ensure_ascii=False, indent=2)}

Return ONLY valid JSON (no text, no markdown). The entire JSON content MUST be in English.
Use STRICT JSON syntax:
- All property names MUST be in double quotes.
- All string values MUST be in double quotes.
- No comments.
- No trailing commas.
- Arrays MUST contain ONLY values (strings/objects), NEVER key names like "local_hooks" or "local_references" inside an array.
- Each field in the schema below MUST appear as a normal JSON property, NOT as part of a string.
Do NOT add any extra top-level fields beyond this schema, and do NOT use placeholders or example pseudo-code inside values:
{{
  "marketing_recommendations": {{
    "tone": {{
      "recommended_tone": "specific tone name",
      "tone_description": "why this tone works for this brand and content",
      "tone_examples": ["short example phrase 1", "short example phrase 2"],
      "tone_avoid": ["tone to avoid 1", "tone to avoid 2"]
    }},
    "voice_style": {{
      "voice_type": "specific voice style",
      "voice_description": "short description of voice characteristics"
    }},
    "camera_angles": {{
      "primary_angles": ["angle 1", "angle 2"],
      "angle_reasoning": "why these angles work for this content"
    }},
    "visual_style": {{
      "color_palette": "specific color palette",
      "lighting_style": "lighting description"
    }},
    "audio_music": {{
      "music_style": "music style",
      "music_tempo": "tempo description"
    }}
  }},
  "viral_scripts": {{
    "hook_formulas": ["hook formula 1", "hook formula 2"],
    "script_templates": [
      {{
        "title": "template title",
        "structure": "structure breakdown",
        "duration": "duration (e.g. 20-30s)",
        "example": "example script text",
        "tone": "tone for this template"
      }}
    ]
  }},
  "cta_variants": [
    {{
      "type": "CTA type",
      "text": "CTA text",
      "placement": "placement (e.g. end, mid-video)",
      "platform": "platform name"
    }}
  ],
  "platform_strategy": {{
    "tiktok": {{
      "format": "format (e.g. vertical)",
      "length": "duration (e.g. 20-30s)",
      "content_type": "content type (e.g. property tour, lifestyle clip)",
      "tone": "tone (e.g. energetic)"
    }},
    "instagram": {{
      "format": "format (e.g. vertical or square)",
      "length": "duration (e.g. 15-30s)",
      "content_type": "content type (e.g. short reel, story)",
      "tone": "tone (e.g. energetic or aspirational)"
    }},
    "youtube": {{
      "format": "format (e.g. landscape)",
      "length": "duration (e.g. 30-60s)",
      "content_type": "content type (e.g. short tour, vlog-style)",
      "tone": "tone (e.g. informative but positive)"
    }}
  }},
  "city_specific_strategy": {{
    "local_hooks": ["local hook 1"],
    "local_references": ["local reference 1"],
    "cultural_notes": "cultural considerations"
  }},
  "action_plan": {{
    "immediate_actions": ["action 1", "action 2"]
  }},
  "key_takeaways": {{
    "top_3_recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
    "why_these_work": "short explanation"
  }}
}}"""

    try:
        result = run_ollama_json(
            model,
            prompt,
            fallback_model=fallback_model,
            max_retries=0,  # No retries - just use fallback
            timeout=240,  # 240s timeout - increased for full data processing
            num_predict=2500,  # 2500 tokens - enough for full JSON response
        )
        
        # If parse error, try JSON repair step
        if "error" in result and result.get("parse_error"):
            logger.error(f"LLM recommendation parse error, attempting repair: {result.get('error')}")
            raw_text = result.get("raw_response", "")
            if raw_text:
                repaired = repair_recommendation_json(raw_text)
                # If repair also failed, fall back to original result
                if "error" in repaired and repaired.get("parse_error"):
                    logger.error(f"JSON repair also failed: {repaired.get('error')}")
                    return result
                logger.info("✅ JSON repair successful for recommendations")
                return repaired
            return result
        
        return result
    except Exception as e:
        logger.error(f"LLM recommendation failed: {str(e)}", exc_info=True)
        # Return error in structured format - NO defaults
        return {
            "error": str(e),
            "marketing_recommendations": {},
            "viral_scripts": {},
            "cta_variants": [],
            "editing_recommendations": {},
            "platform_strategy": {},
            "city_specific_strategy": {},
            "action_plan": {},
            "key_takeaways": {},
        }
