"""
Configuration management for Ollama-Markov.

Loads settings from environment variables or .env file.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Dictionary with configuration settings.
    """
    # Load .env file if it exists
    load_dotenv()

    config = {
        "mode": os.getenv("MODE", "training"),  # "training" or "live"
        "ollama_port": int(os.getenv("OLLAMA_PORT", "11434")),
        "markov_order": int(os.getenv("MARKOV_ORDER", "2")),
        "compaction_interval": int(os.getenv("COMPACTION_INTERVAL", "1000")),
        "recommended_tokens": int(os.getenv("RECOMMENDED_TOKENS", "50")),
        "max_tokens": int(os.getenv("MAX_TOKENS", "500")),
        "complete_sentences": os.getenv("COMPLETE_SENTENCES", "true").lower() == "true",
        "temperature": float(os.getenv("TEMPERATURE", "0.8")),
        "min_message_length": int(os.getenv("MIN_MESSAGE_LENGTH", "3")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "db_path": os.getenv("DB_PATH", "ollama_markov.db"),
        "ssl_enabled": os.getenv("SSL_ENABLED", "false").lower() == "true",
        "ssl_cert": os.getenv("SSL_CERT", None),
        "ssl_key": os.getenv("SSL_KEY", None),
    }
    return config
