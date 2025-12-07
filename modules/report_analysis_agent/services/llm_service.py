import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def check_model_available(model: str) -> bool:
    """
    Check if a model is available in Ollama.
    Supports prefix matching (e.g., "deepseek-r1" matches "deepseek-r1:8b").
    
    Args:
        model: Model name to check (can be prefix like "deepseek-r1")
    
    Returns:
        True if model is available, False otherwise
    """
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        models_data = response.json()
        available_models = [m.get("name", "") for m in models_data.get("models", [])]
        
        # Exact match first
        if model in available_models:
            return True
        
        # Prefix match (e.g., "deepseek-r1" matches "deepseek-r1:8b", "deepseek-r1:latest")
        model_base = model.split(":")[0]
        for available in available_models:
            if available.startswith(model_base):
                logger.info(f"Found model {available} matching {model}")
                return True
        
        return False
    except Exception as e:
        logger.warning(f"Could not check model availability: {str(e)}")
        return False


def get_available_model(model_prefix: str) -> str:
    """
    Get the actual model name available in Ollama matching the prefix.
    
    Args:
        model_prefix: Model name or prefix (e.g., "deepseek-r1")
    
    Returns:
        Actual model name available in Ollama
    """
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        models_data = response.json()
        available_models = [m.get("name", "") for m in models_data.get("models", [])]
        
        # Exact match first
        if model_prefix in available_models:
            return model_prefix
        
        # Prefix match
        model_base = model_prefix.split(":")[0]
        for available in available_models:
            if available.startswith(model_base):
                return available
        
        return model_prefix  # Return original if no match found
    except Exception as e:
        logger.warning(f"Could not get available model: {str(e)}")
        return model_prefix


def run_ollama(model: str, prompt: str, fallback_model: Optional[str] = None, timeout: Optional[int] = None, num_predict: Optional[int] = None) -> str:
    """
    Run Ollama model with given prompt.
    
    Args:
        model: Model name (e.g., "deepseek-r1:latest")
        prompt: Input prompt text
        fallback_model: Optional fallback model if primary model fails
        timeout: Optional timeout in seconds (default: 300 = 5 minutes)
        num_predict: Optional max tokens to predict (default: 800)
    
    Returns:
        Response text from the model
    """
    url = "http://localhost:11434/api/generate"
    
    # More aggressive timeout strategy
    if timeout is None:
        # Base timeout: 90 seconds (much shorter for faster failure)
        # Add 10 seconds per 10KB of prompt
        prompt_size_kb = len(prompt.encode('utf-8')) / 1024
        timeout = int(90 + (prompt_size_kb / 10) * 10)
        # Cap at 3 minutes maximum
        timeout = min(timeout, 180)
        logger.info(f"Calculated timeout: {timeout} seconds (prompt size: {prompt_size_kb:.1f} KB)")
    
    # Try primary model first
    models_to_try = [model]
    if fallback_model:
        models_to_try.append(fallback_model)
    
    last_error = None
    for model_to_use in models_to_try:
        # ULTRA FAST: Aggressive parameters for speed
        # Use provided num_predict or default to 800
        predict_tokens = num_predict if num_predict is not None else 800
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,   # Very low for speed
                "top_p": 0.5,         # Narrow sampling for speed
                "top_k": 10,          # Very narrow for speed
                "num_predict": predict_tokens,  # Configurable token limit
                "num_ctx": 2048,      # Smaller context for speed
                "repeat_penalty": 1.2,
                "num_thread": 6,     # M2 optimal (was 8)
                # "num_gpu": 1        # Let Ollama auto-detect GPU
            }
        }
        
        import time
        start_time = time.time()
        try:
            # Dynamic timeout based on prompt size
            # Use shorter timeout for first model, if it times out try fallback
            model_timeout = timeout if model_to_use == model else timeout
            # Use tuple for connect and read timeout
            # Connect timeout: 5s, Read timeout: model_timeout
            logger.info(f"🔵 Calling Ollama with model {model_to_use}, timeout: {model_timeout}s")
            logger.info(f"🔵 Prompt length: {len(prompt)} chars")
            response = requests.post(url, json=payload, timeout=(5, model_timeout))
            elapsed = time.time() - start_time
            logger.info(f"✅ Ollama response received in {elapsed:.2f}s")
            response.raise_for_status()
            result = response.json()
            if model_to_use != model:
                logger.info(f"✅ Using fallback model: {model_to_use} instead of {model}")
            response_text = result.get("response", "")
            logger.info(f"✅ Response length: {len(response_text)} chars")
            return response_text
        except requests.exceptions.Timeout as e:
            elapsed = time.time() - start_time
            last_error = Exception(f"Request timeout after {model_timeout} seconds for model {model_to_use} (elapsed: {elapsed:.2f}s)")
            logger.error(f"❌ TIMEOUT for model {model_to_use} after {model_timeout}s (elapsed: {elapsed:.2f}s)")
            logger.error(f"❌ Error details: {str(e)}")
            # Continue to next model (fallback) if available
            if len(models_to_try) > 1 and model_to_use == model:
                logger.info(f"🔄 Switching to fallback model...")
            continue
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.error(f"❌ Request failed for model {model_to_use}: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            continue
        except Exception as e:
            last_error = e
            logger.error(f"❌ Unexpected error for model {model_to_use}: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            continue
    
    raise Exception(f"Ollama API error with all models: {str(last_error)}")


def run_ollama_json(model: str, prompt: str, fallback_model: Optional[str] = None, max_retries: int = 2, timeout: Optional[int] = None, num_predict: Optional[int] = None) -> Dict[str, Any]:
    """
    Run Ollama and parse JSON response with retry mechanism.
    
    Args:
        model: Model name
        prompt: Input prompt text
        fallback_model: Optional fallback model if primary model fails
        max_retries: Maximum number of retries on failure
        timeout: Optional timeout in seconds (default: dynamic based on prompt size)
        num_predict: Optional max tokens to predict (default: 800)
    
    Returns:
        Parsed JSON dictionary
    """
    response_text = None
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt} for model {model}")
            response_text = run_ollama(model, prompt, fallback_model, timeout=timeout, num_predict=num_predict)
            break
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                continue
            else:
                raise Exception(f"All retry attempts failed: {str(last_error)}")
    
    if response_text is None:
        raise Exception("Failed to get response from Ollama")
    
    # Try to extract JSON from response
    try:
        # Remove any leading text before JSON
        json_start = response_text.find("{")
        if json_start == -1:
            # No JSON found
            raise json.JSONDecodeError("No JSON object found", response_text, 0)
        
        # Find the matching closing brace
        brace_count = 0
        json_end = json_start
        for i in range(json_start, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if brace_count != 0:
            # Try to find last }
            json_end = response_text.rfind("}") + 1
        
        json_text = response_text[json_start:json_end].strip()
        
        # Remove markdown code fences if present
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()
        
        # Clean up the JSON text
        json_text = json_text.strip()
        import re
        # Remove any trailing commas before closing braces/brackets (common LLM mistake)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        # Fix common "X or Y" pattern inside arrays: ["stuffy" or "boring"] -> ["stuffy","boring"]
        json_text = re.sub(r'\"([^\"\\]+)\"\s+or\s+\"([^\"\\]+)\"', r'"\1","\2"', json_text)
        # Quote unquoted duration values: "duration": 20-30 seconds -> "duration": "20-30 seconds"
        json_text = re.sub(
            r'("duration"\s*:\s*)([^",}\]\s][^,}\]]*)',
            r'\1"\2"',
            json_text
        )
        # Quote unquoted length values: "length": 20-30 seconds -> "length": "20-30 seconds"
        json_text = re.sub(
            r'("length"\s*:\s*)([^",}\]\s][^,}\]]*)',
            r'\1"\2"',
            json_text
        )
        
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
        # If JSON parsing fails, return as text in a wrapper
        return {"raw_response": response_text, "parse_error": True, "error": str(e)}


def repair_recommendation_json(raw_text: str) -> Dict[str, Any]:
    """
    Use a smaller/faster model to repair invalid recommendation JSON into strict JSON.
    This is a best-effort step used only when the first parse fails.
    """
    schema_hint = """
{
  "marketing_recommendations": {
    "tone": {
      "recommended_tone": "specific tone name",
      "tone_description": "why this tone works for this brand and content",
      "tone_examples": ["short example phrase 1", "short example phrase 2"],
      "tone_avoid": ["tone to avoid 1", "tone to avoid 2"]
    },
    "voice_style": {
      "voice_type": "specific voice style",
      "voice_description": "short description of voice characteristics"
    },
    "camera_angles": {
      "primary_angles": ["angle 1", "angle 2"],
      "angle_reasoning": "why these angles work for this content"
    },
    "visual_style": {
      "color_palette": "specific color palette",
      "lighting_style": "lighting description"
    },
    "audio_music": {
      "music_style": "music style",
      "music_tempo": "tempo description"
    }
  },
  "viral_scripts": {
    "hook_formulas": ["hook formula 1", "hook formula 2"],
    "script_templates": [
      {
        "title": "template title",
        "structure": "structure breakdown",
        "duration": "duration (e.g. 20-30s)",
        "example": "example script text",
        "tone": "tone for this template"
      }
    ]
  },
  "cta_variants": [
    {
      "type": "CTA type",
      "text": "CTA text",
      "placement": "placement (e.g. end, mid-video)",
      "platform": "platform name"
    }
  ],
  "platform_strategy": {
    "tiktok": {
      "format": "format (e.g. vertical)",
      "length": "duration (e.g. 20-30s)",
      "content_type": "content type",
      "tone": "tone"
    },
    "instagram": {
      "format": "format (e.g. vertical or square)",
      "length": "duration (e.g. 15-30s)",
      "content_type": "content type",
      "tone": "tone"
    },
    "youtube": {
      "format": "format (e.g. landscape)",
      "length": "duration (e.g. 30-60s)",
      "content_type": "content type",
      "tone": "tone"
    }
  },
  "city_specific_strategy": {
    "local_hooks": ["local hook 1"],
    "local_references": ["local reference 1"],
    "cultural_notes": "cultural considerations"
  },
  "action_plan": {
    "immediate_actions": ["action 1", "action 2"]
  },
  "key_takeaways": {
    "top_3_recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
    "why_these_work": "short explanation"
  }
}
""".strip()

    repair_prompt = f"""You are a strict JSON repair assistant.

The content below is intended to follow this JSON schema:
{schema_hint}

Your task:
1. Read the INVALID or PARTIALLY VALID JSON-like content.
2. Produce STRICT, VALID JSON that follows the schema above as closely as possible.
3. Drop any fields that do not fit the schema.
4. Do NOT add any new top-level fields beyond the schema.
5. Use ONLY English in all string values.
6. Use ONLY double quotes for strings and property names, no comments, no trailing commas.

Content to repair:
{raw_text}

Return ONLY the repaired JSON (no explanations, no markdown).
"""

    try:
        # Use available model for repair
        repair_model = get_available_model("gemma") if check_model_available("gemma") else \
                       get_available_model("llama3.2") if check_model_available("llama3.2") else \
                       get_available_model("qwen2.5") if check_model_available("qwen2.5") else "gemma:7b"
        repaired = run_ollama_json(
            model=repair_model,
            prompt=repair_prompt,
            fallback_model=None,
            max_retries=0,
            timeout=120,
            num_predict=1800,
        )
        return repaired
    except Exception as e:
        logger.error(f"JSON repair failed: {str(e)}", exc_info=True)
        return {
            "raw_response": raw_text,
            "parse_error": True,
            "error": f"repair_failed: {str(e)}",
        }


def repair_interpretation_json(raw_text: str) -> Dict[str, Any]:
    """
    Use a smaller/faster model to repair invalid interpretation JSON into strict JSON.
    """
    schema_hint = """
{
  "winning_patterns": {
    "common_hooks": ["specific hook 1", "specific hook 2"],
    "emotional_triggers": ["trigger 1", "trigger 2"],
    "content_structure": "description of structure",
    "visual_elements": "description of visuals"
  },
  "cta_analysis": {
    "effective_cta_types": ["CTA type 1", "CTA type 2"],
    "cta_placement": "where CTAs work best",
    "cta_language": "effective CTA language patterns"
  },
  "target_audience_insights": {
    "content_preferences": "what audience prefers",
    "optimal_length": "best video length",
    "tone_preferences": "preferred tone"
  },
  "key_findings": ["finding 1", "finding 2", "finding 3"]
}
""".strip()

    repair_prompt = f"""You are a strict JSON repair assistant.

The content below is intended to follow this JSON schema:
{schema_hint}

Your task:
1. Read the INVALID or PARTIALLY VALID JSON-like content.
2. Produce STRICT, VALID JSON that follows the schema above as closely as possible.
3. Drop any fields that do not fit the schema.
4. Do NOT add any new top-level fields beyond the schema.
5. Use ONLY English in all string values.
6. Use ONLY double quotes for strings and property names, no comments, no trailing commas.

Content to repair:
{raw_text}

Return ONLY the repaired JSON (no explanations, no markdown).
"""

    try:
        # Use available model for repair
        repair_model = get_available_model("gemma") if check_model_available("gemma") else \
                       get_available_model("llama3.2") if check_model_available("llama3.2") else \
                       get_available_model("qwen2.5") if check_model_available("qwen2.5") else "gemma:7b"
        repaired = run_ollama_json(
            model=repair_model,
            prompt=repair_prompt,
            fallback_model=None,
            max_retries=0,
            timeout=90,
            num_predict=1200,
        )
        return repaired
    except Exception as e:
        logger.error(f"JSON repair (interpretation) failed: {str(e)}", exc_info=True)
        return {
            "raw_response": raw_text,
            "parse_error": True,
            "error": f"repair_failed: {str(e)}",
        }













