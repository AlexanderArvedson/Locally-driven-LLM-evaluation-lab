"""
LLM integration module for calling Ollama.
"""

import httpx
import json
import logging
from typing import Optional

from core.config import CoreConfig
from core.router import resolve_model_name

logger = logging.getLogger(__name__)

# Timeout for Ollama calls: 10 minutes (600 seconds)
OLLAMA_TIMEOUT = 600.0


async def call_ollama(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Call Ollama API to generate text.

    Args:
        prompt: The input prompt to send to the model.
        model: The model name to use. If None, uses resolve_model_name() to select.
        temperature: Sampling temperature (0.0 to 1.0).
        max_tokens: Maximum tokens to generate.

    Returns:
        The generated text response from the model.

    Raises:
        RuntimeError: If the API call fails or times out.
    """
    config = CoreConfig()
    
    # Resolve model name
    if model is None:
        model = resolve_model_name()
    
    endpoint = config.model_endpoint
    
    logger.debug(f"Calling Ollama: model={model}, endpoint={endpoint}")
    
    # Prepare payload for Ollama API
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "num_predict": max_tokens,
        "stream": False,  # Get full response at once
    }
    
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                endpoint,
                json=payload,
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            generated_text = data.get("response", "")
            
            logger.debug(f"Ollama response received: {len(generated_text)} chars")
            
            return generated_text
            
    except httpx.TimeoutException as e:
        error_msg = f"Ollama request timed out after {OLLAMA_TIMEOUT}s"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except httpx.HTTPError as e:
        error_msg = f"Ollama API error: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Ollama response: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error calling Ollama: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
