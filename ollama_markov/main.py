"""
Main entry point for Ollama-Markov server.

Initializes all components and starts the HTTP API server.
"""

from ollama_markov.config import load_config
from ollama_markov.logger import setup_logger


def main():
    """Start the Ollama-Markov server."""
    from ollama_markov.storage.database import Database
    from ollama_markov.model.markov import MarkovModel
    from ollama_markov.model.tokenizer import Tokenizer
    from ollama_markov.processing.text_processor import TextProcessor
    from ollama_markov.processing.safety import SafetyFilter
    from ollama_markov.model.generator import Generator
    from ollama_markov.api.server import OllamaServer

    config = load_config()
    logger = setup_logger(__name__, config["log_level"])

    logger.info(f"Starting Ollama-Markov server in {config['mode']} mode")
    logger.info(f"Database: {config['db_path']}")
    logger.info(f"Markov order: {config['markov_order']}")
    logger.info(f"Server port: {config['ollama_port']}")

    try:
        # Initialize database
        logger.info("Initializing database...")
        db = Database(config['db_path'])

        # Initialize Markov model
        logger.info("Initializing Markov model...")
        model = MarkovModel(config['markov_order'])

        # Load existing transitions from database
        logger.info("Loading existing transitions...")
        transitions_loaded = model.load_from_database(db)
        logger.info(f"Loaded {transitions_loaded} transitions from database")

        # Initialize tokenizer and text processor
        logger.info("Initializing text processor...")
        tokenizer = Tokenizer()
        text_processor = TextProcessor(config)

        # Initialize safety filter
        logger.info("Initializing safety filter...")
        safety_filter = SafetyFilter(config)

        # Initialize generator
        logger.info("Initializing generator...")
        generator = Generator(model, db, safety_filter, text_processor, config)

        # Initialize API server
        logger.info("Initializing API server...")
        server = OllamaServer(generator, config)

        # Start server
        logger.info(f"Starting HTTP server on port {config['ollama_port']}...")
        server.start(host="0.0.0.0", port=config['ollama_port'])

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        if 'db' in locals():
            db.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
