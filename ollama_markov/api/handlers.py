"""
Request and response handlers for Ollama-compatible API endpoints.
"""

from typing import Dict, Tuple
from datetime import datetime


def validate_request(data: Dict, endpoint: str) -> Tuple[bool, str]:
    """
    Validate Ollama-format request.

    Args:
        data: Request JSON data
        endpoint: Endpoint name ('generate' or 'chat')

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return (False, "Request must be JSON object")

    if endpoint == "generate":
        if 'prompt' not in data:
            return (False, "Missing required field: prompt")
        if not isinstance(data['prompt'], str):
            return (False, "Field 'prompt' must be string")

    elif endpoint == "chat":
        if 'messages' not in data:
            return (False, "Missing required field: messages")
        if not isinstance(data['messages'], list):
            return (False, "Field 'messages' must be list")

        for msg in data['messages']:
            if not isinstance(msg, dict):
                return (False, "Each message must be object")
            if 'role' not in msg or 'content' not in msg:
                return (False, "Message missing 'role' or 'content'")

    return (True, "")


def format_response(response_text: str, endpoint: str = "generate", stream: bool = False) -> Dict:
    """
    Format response to Ollama specification.

    Args:
        response_text: Generated or status text
        endpoint: Endpoint name ('generate' or 'chat')
        stream: Whether streaming is enabled (for MVP, always false)

    Returns:
        Ollama-compatible response dictionary
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    if endpoint == "generate":
        return {
            "model": "ollama-markov",
            "created_at": timestamp,
            "response": response_text,
            "done": True
        }

    elif endpoint == "chat":
        return {
            "model": "ollama-markov",
            "created_at": timestamp,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "done": True
        }

    return {}


def handle_error(error: Exception, code: int = 500) -> Tuple[Dict, int]:
    """
    Format error responses.

    Args:
        error: Exception that occurred
        code: HTTP status code

    Returns:
        Tuple of (error_response, status_code)
    """
    return ({"error": str(error)}, code)
