#!/usr/bin/env python3
"""
Simple test script for Markov model training and generation.

This allows you to:
1. Train the model with sample text
2. Generate new text
3. Check database stats
"""

import sys
import json
from pathlib import Path

from ollama_markov.config import load_config
from ollama_markov.model.markov import MarkovModel
from ollama_markov.model.tokenizer import Tokenizer
from ollama_markov.processing.text_processor import TextProcessor
from ollama_markov.storage.database import Database


def train_from_text(model, db, processor, text: str, channel_id: str = "test", user_id: str = "test_user"):
    """Train model from raw text."""
    # Process the text
    tokens = processor.preprocess(text)

    if not tokens:
        print("Text did not pass preprocessing filters.")
        return False

    # Store in database
    db.add_message(user_id, channel_id, text)

    # Train model
    model.train(tokens)

    # Store transitions in database
    for state, next_tokens in model.transitions.items():
        for next_token, count in next_tokens.items():
            db.add_transition(model.order, state, next_token, count)

    return True


def main():
    """Main test function."""
    config = load_config()

    # Initialize components
    tokenizer = Tokenizer()
    processor = TextProcessor(config)
    model = MarkovModel(config["markov_order"])
    db = Database(config["db_path"])

    print("=" * 60)
    print("Ollama-Markov Test Script")
    print("=" * 60)
    print(f"Database: {config['db_path']}")
    print(f"Markov Order: {config['markov_order']}")
    print()

    # Sample training data
    training_samples = [
        "The quick brown fox jumps over the lazy dog.",
        "Python is a great programming language for beginners.",
        "Machine learning is an exciting field of computer science.",
        "Natural language processing enables computers to understand human language.",
        "Markov chains are used for text generation and prediction.",
        "The weather today is sunny and warm.",
        "I love reading books about science and history.",
        "Coffee is the most popular beverage in the morning.",
        "Technology continues to evolve at a rapid pace.",
        "Learning new skills takes time and dedication.",
    ]

    print("Training model with sample data...")
    trained_count = 0
    for sample in training_samples:
        if train_from_text(model, db, processor, sample):
            trained_count += 1
            print(f"  ✓ Trained: {sample[:50]}...")

    print(f"\nSuccessfully trained on {trained_count}/{len(training_samples)} samples")
    print()

    # Show database stats
    stats = db.stats()
    print("Database Statistics:")
    print(f"  Messages: {stats['message_count']}")
    print(f"  Transitions: {stats['transition_count']}")
    print(f"  States: {stats['state_count']}")
    print(f"  Total transitions: {stats['total_transitions']}")
    print()

    # Test generation
    print("Generating text samples:")
    print("-" * 60)

    # Try different seed states and temperatures
    test_cases = [
        ("the", 1.0, "Seed: 'the', Temperature: 1.0"),
        ("the", 0.5, "Seed: 'the', Temperature: 0.5 (more deterministic)"),
        ("python", 1.0, "Seed: 'python', Temperature: 1.0"),
    ]

    for seed_state, temperature, description in test_cases:
        print(f"\n{description}")
        try:
            generated = model.generate(seed_state, max_tokens=15, temperature=temperature)
            if generated:
                reconstructed = tokenizer.detokenize(generated.split())
                print(f"  Generated: {reconstructed}")
            else:
                print("  (No generation - seed state not in model)")
        except Exception as e:
            print(f"  Error: {e}")

    print()
    print("-" * 60)
    print("Test complete!")
    print()

    # Cleanup
    db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
