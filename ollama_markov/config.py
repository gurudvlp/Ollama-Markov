"""
Configuration management for Ollama-Markov.

Loads settings from environment variables or .env file.
"""

import os
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Dictionary with configuration settings.
    """
    config = {
        "mode": os.getenv("MODE", "training"),  # "training" or "live"
        "ollama_port": int(os.getenv("OLLAMA_PORT", "11434")),
        "markov_order": int(os.getenv("MARKOV_ORDER", "2")),
        "compaction_interval": int(os.getenv("COMPACTION_INTERVAL", "1000")),
        "max_tokens": int(os.getenv("MAX_TOKENS", "500")),
        "temperature": float(os.getenv("TEMPERATURE", "0.8")),
        "min_message_length": int(os.getenv("MIN_MESSAGE_LENGTH", "3")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "db_path": os.getenv("DB_PATH", "ollama_markov.db"),
    }
    return config
