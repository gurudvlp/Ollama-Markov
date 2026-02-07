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


def validate_openai_request(data: Dict) -> Tuple[bool, str]:
    """
    Validate OpenAI-format request.

    Args:
        data: Request JSON data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return (False, "Request must be JSON object")

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


def format_ollama_tags() -> Dict:
    """
    Format Ollama /api/tags response.

    Returns:
        Ollama-compatible tags/models list response
    """
    import time

    timestamp = datetime.utcnow().isoformat() + "Z"

    return {
        "models": [
            {
                "name": "ollama-markov:latest",
                "model": "ollama-markov:latest",
                "modified_at": timestamp,
                "size": 0,
                "digest": "markov-model",
                "details": {
                    "parent_model": "",
                    "format": "markov",
                    "family": "markov",
                    "families": ["markov"],
                    "parameter_size": "0",
                    "quantization_level": "N/A"
                }
            }
        ]
    }


def format_openai_models() -> Dict:
    """
    Format OpenAI /v1/models response.

    Returns:
        OpenAI-compatible models list response
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "ollama-markov",
                "object": "model",
                "created": 1706745600,
                "owned_by": "ollama-markov"
            }
        ]
    }


def format_openai_response(response_text: str, model: str = "ollama-markov") -> Dict:
    """
    Format OpenAI /v1/chat/completions response.

    Args:
        response_text: Generated response text
        model: Model name

    Returns:
        OpenAI-compatible chat completion response
    """
    import time

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "fp_ollama",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }


def format_openai_stream(response_text: str, model: str = "ollama-markov") -> str:
    """
    Format OpenAI streaming response (newline-delimited JSON).

    Sends word-sized chunks in Ollama-compatible format.

    Args:
        response_text: Generated response text
        model: Model name

    Returns:
        Newline-delimited JSON string for streaming
    """
    import json
    import re
    import time

    lines = []
    creation_time = int(time.time())

    # Split text into chunks by words (spaces + surrounding text)
    # This creates word-sized chunks like "word ", "another ", etc.
    chunks = re.findall(r'\S+\s*', response_text)
    if response_text and not response_text[-1].isspace() and chunks:
        # Handle case where last chunk doesn't have trailing space
        chunks[-1] = chunks[-1].rstrip() + response_text[len(''.join(chunks)):]

    if not chunks and response_text:
        # If no spaces found, just use the whole text
        chunks = [response_text]

    # First chunk includes role
    if chunks:
        first_chunk = {
            "id": f"chatcmpl-{creation_time}",
            "object": "chat.completion.chunk",
            "created": creation_time,
            "model": model,
            "system_fingerprint": "fp_ollama",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": chunks[0]
                    },
                    "finish_reason": None
                }
            ]
        }
        lines.append(f"data: {json.dumps(first_chunk)}")

        # Remaining chunks - include role in every chunk like real Ollama
        for chunk in chunks[1:]:
            chunk_obj = {
                "id": f"chatcmpl-{creation_time}",
                "object": "chat.completion.chunk",
                "created": creation_time,
                "model": model,
                "system_fingerprint": "fp_ollama",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": chunk
                        },
                        "finish_reason": None
                    }
                ]
            }
            lines.append(f"data: {json.dumps(chunk_obj)}")
    else:
        # Empty response
        first_chunk = {
            "id": f"chatcmpl-{creation_time}",
            "object": "chat.completion.chunk",
            "created": creation_time,
            "model": model,
            "system_fingerprint": "fp_ollama",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": None
                }
            ]
        }
        lines.append(f"data: {json.dumps(first_chunk)}")

    # Final chunk with finish_reason
    final_chunk = {
        "id": f"chatcmpl-{creation_time}",
        "object": "chat.completion.chunk",
        "created": creation_time,
        "model": model,
        "system_fingerprint": "fp_ollama",
        "choices": [
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": "stop"
            }
        ]
    }
    lines.append(f"data: {json.dumps(final_chunk)}")

    # Send completion signal
    lines.append("data: [DONE]")

    return "\n".join(lines)
