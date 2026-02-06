"""
Main entry point for Ollama-Markov server.

Initializes all components and starts the HTTP API server.
"""

from ollama_markov.config import load_config
from ollama_markov.logger import setup_logger


def main():
    """Start the Ollama-Markov server."""
    config = load_config()
    logger = setup_logger(__name__, config["log_level"])

    logger.info(f"Starting Ollama-Markov server in {config['mode']} mode")
    logger.info(f"Database: {config['db_path']}")
    logger.info(f"Markov order: {config['markov_order']}")
    logger.info(f"Server port: {config['ollama_port']}")

    # TODO: Initialize database
    # TODO: Initialize Markov model
    # TODO: Initialize API server
    # TODO: Start Flask app


if __name__ == "__main__":
    main()
