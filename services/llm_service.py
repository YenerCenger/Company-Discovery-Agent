"""
LLM Service for structured data extraction from HTML

Uses Ollama for local LLM inference.
"""

import json
import requests
from typing import Dict, List, Optional, Any
import structlog
from config.settings import settings

logger = structlog.get_logger(__name__)


class LLMService:
    """Service for interacting with Ollama API"""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = 300
    ):
        """
        Initialize Ollama LLM service
        
        Args:
            base_url: Ollama API base URL (default from settings)
            model: Model name (default from settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout
        
        logger.info(
            "Initialized LLMService (Ollama)",
            base_url=self.base_url,
            model=self.model
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate completion from Ollama
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            logger.debug(
                "Sending request to Ollama",
                model=self.model,
                prompt_length=len(prompt)
            )
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            generated_text = result.get("response", "")
            
            logger.debug(
                "Received response from Ollama",
                response_length=len(generated_text)
            )
            
            return generated_text
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timeout", timeout=self.timeout)
            raise Exception(f"Ollama timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            logger.error(
                "Cannot connect to Ollama",
                base_url=self.base_url,
                hint="Make sure Ollama is running: 'ollama serve'"
            )
            raise Exception(f"Cannot connect to Ollama at {self.base_url}")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}", exc_info=True)
            raise
    
    def extract_json_from_text(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response
        
        Args:
            text: Text containing JSON (may have markdown code blocks)
            
        Returns:
            Parsed JSON dict or None if parsing failed
        """
        try:
            # Remove markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Clean up whitespace
            text = text.strip()
            
            # Parse JSON
            data = json.loads(text)
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}", text_preview=text[:200])
            return None
        except Exception as e:
            logger.error(f"JSON extraction error: {e}", exc_info=True)
            return None
    
    def check_available(self) -> bool:
        """
        Check if Ollama is running and model is available
        
        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            model_available = any(
                self.model in name
                for name in model_names
            )
            
            if model_available:
                logger.info(f"Ollama model {self.model} is available")
            else:
                logger.warning(
                    f"Model {self.model} not found",
                    available_models=model_names,
                    hint=f"Run: ollama pull {self.model}"
                )
            
            return model_available
            
        except Exception as e:
            logger.warning(
                f"Ollama not available: {e}",
                hint="Make sure Ollama is running: 'ollama serve'"
            )
            return False


# Alias for backward compatibility
OllamaLLMService = LLMService


class HTMLCompanyExtractor:
    """Extract structured company data from HTML using LLM"""

    def __init__(self, llm_service=None):
        """
        Initialize HTML company extractor

        Args:
            llm_service: Optional LLM service (will create default if not provided)
        """
        self.llm = llm_service or LLMService()
    
    def extract_companies(
        self,
        html_content: str,
        query_context: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Extract company information from HTML using LLM
        
        Args:
            html_content: Raw HTML content
            query_context: Search context (e.g., "Miami Florida real estate")
            limit: Maximum number of companies to extract
            
        Returns:
            List of company dictionaries with name, website_url, etc.
        """
        try:
            # Clean HTML (remove scripts, styles, keep text)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()
            
            # Get text content with some structure
            text_content = soup.get_text(separator='\n', strip=True)

            # Truncate if too long (Ollama context limit)
            max_chars = 10000  # Leave room for prompt
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "\n... [content truncated]"
            
            logger.info(
                "Extracting companies with LLM",
                query_context=query_context,
                content_length=len(text_content)
            )
            
            # Build prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(text_content, query_context, limit)
            
            # Generate
            response = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1  # Low temperature for structured output
            )
            
            # Extract JSON
            data = self.llm.extract_json_from_text(response)
            
            if not data:
                logger.warning("LLM did not return valid JSON")
                return []
            
            # Extract companies list - handle both dict and list formats
            if isinstance(data, list):
                # LLM returned array directly
                companies = data
            elif isinstance(data, dict):
                # LLM returned {"companies": [...]}
                companies = data.get("companies", [])
            else:
                logger.warning(f"LLM response unexpected type: {type(data)}")
                return []
            
            if not isinstance(companies, list):
                logger.warning("LLM response 'companies' is not a list")
                return []
            
            logger.info(f"LLM extracted {len(companies)} companies")
            return companies[:limit]
            
        except Exception as e:
            logger.error(f"Company extraction error: {e}", exc_info=True)
            return []
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for company extraction"""
        return """You are a data extraction assistant specialized in parsing real estate business information from web pages.

Your task is to extract structured company data from HTML content.

IMPORTANT RULES:
1. Return ONLY valid JSON, no additional text
2. Extract company/agency names, not individual agent names
3. If you find agent names, use their brokerage/company instead
4. Include website URLs when available
5. Skip duplicates
6. Return empty array if no companies found

Output format:
{
  "companies": [
    {
      "name": "Company Name",
      "website_url": "https://example.com",
      "source": "website_name"
    }
  ]
}"""
    
    def _build_user_prompt(
        self,
        text_content: str,
        query_context: str,
        limit: int
    ) -> str:
        """Build user prompt with content"""
        return f"""Extract up to {limit} real estate companies from this web page.

Search context: {query_context}

Web page content:
---
{text_content}
---

Extract companies in JSON format. Return only the JSON, no other text."""
    
    def check_ollama_available(self) -> bool:
        """
        Check if Ollama is running and model is available
        
        Returns:
            True if Ollama is accessible, False otherwise
        """
        return self.llm.check_available()
