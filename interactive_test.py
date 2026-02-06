#!/usr/bin/env python3
"""
Interactive test script for Markov model.

Allows you to:
1. Add training data interactively
2. Generate text
3. View statistics
"""

import sys
import os
from pathlib import Path

from ollama_markov.config import load_config
from ollama_markov.model.markov import MarkovModel
from ollama_markov.model.tokenizer import Tokenizer
from ollama_markov.processing.text_processor import TextProcessor
from ollama_markov.storage.database import Database


def show_menu():
    """Display main menu."""
    print("\n" + "=" * 60)
    print("Ollama-Markov Interactive Test")
    print("=" * 60)
    print("1. Add training text")
    print("2. Generate text")
    print("3. Show stats")
    print("4. Clear database")
    print("5. Exit")
    print("=" * 60)


def add_training_text(model, db, processor, tokenizer):
    """Add training text interactively."""
    print("\nEnter training text (or 'cancel' to return to menu):")
    text = input("> ").strip()

    if text.lower() == "cancel":
        return

    if not text:
        print("Empty text, skipping.")
        return

    # Process text
    tokens = processor.preprocess(text)

    if not tokens:
        print("✗ Text did not pass preprocessing filters.")
        return

    # Store in database
    msg_id = db.add_message("interactive", "test", text)

    # Train model
    model.train(tokens)

    # Store transitions
    for state, next_tokens in model.transitions.items():
        for next_token, count in next_tokens.items():
            db.add_transition(model.order, state, next_token, count)

    print(f"✓ Trained on {len(tokens)} tokens")
    print(f"  Tokens: {' '.join(tokens[:10])}{'...' if len(tokens) > 10 else ''}")


def generate_text(model, db, processor, tokenizer):
    """Generate text interactively."""
    print("\nGenerate text options:")
    print("  1. From random state")
    print("  2. From specific seed")
    print("  3. Back to menu")

    choice = input("Choice [1-3]: ").strip()

    if choice == "3":
        return

    temperature = 1.0
    try:
        temp_input = input("Temperature (0-2, default 1.0): ").strip()
        if temp_input:
            temperature = float(temp_input)
    except ValueError:
        print("Invalid temperature, using default 1.0")

    if choice == "1":
        # Random state
        if not model.transitions:
            print("✗ No training data yet.")
            return

        seed_state = ""
    elif choice == "2":
        # Specific seed
        seed_state = input("Seed state (or leave empty for random): ").strip()
    else:
        print("Invalid choice")
        return

    try:
        max_tokens = 20
        generated = model.generate(seed_state, max_tokens=max_tokens, temperature=temperature)

        if generated:
            text = tokenizer.detokenize(generated.split())
            print(f"\n✓ Generated: {text}")
        else:
            print("✗ Could not generate text (seed state not found or no transitions)")
    except Exception as e:
        print(f"✗ Error during generation: {e}")


def show_stats(db):
    """Show database statistics."""
    stats = db.stats()

    print("\nDatabase Statistics:")
    print(f"  Messages: {stats['message_count']}")
    print(f"  Transitions: {stats['transition_count']}")
    print(f"  States (compacted): {stats['state_count']}")
    print(f"  Total transitions: {stats['total_transitions']}")

    if stats["message_count"] > 0:
        avg_transitions = stats["total_transitions"] / max(stats["transition_count"], 1)
        print(f"  Avg transitions per state: {avg_transitions:.1f}")


def clear_database(db):
    """Clear database after confirmation."""
    confirm = input("\nAre you sure? Type 'yes' to confirm: ").strip().lower()

    if confirm == "yes":
        os.remove(db.db_path)
        print("✓ Database cleared")
    else:
        print("Cancelled")


def load_training_data_from_file(model, db, processor, tokenizer):
    """Load training data from a file."""
    filepath = input("\nEnter file path: ").strip()

    if not Path(filepath).exists():
        print(f"✗ File not found: {filepath}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        trained = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue

            tokens = processor.preprocess(line)
            if tokens:
                db.add_message("file_import", "test", line)
                model.train(tokens)

                for state, next_tokens in model.transitions.items():
                    for next_token, count in next_tokens.items():
                        db.add_transition(model.order, state, next_token, count)

                trained += 1

        print(f"✓ Trained on {trained}/{len(lines)} lines from file")
    except Exception as e:
        print(f"✗ Error reading file: {e}")


def main():
    """Main interactive loop."""
    config = load_config()

    # Initialize components
    tokenizer = Tokenizer()
    processor = TextProcessor(config)
    model = MarkovModel(config["markov_order"])
    db = Database(config["db_path"])

    print(f"\nInitialized with order-{config['markov_order']} Markov model")
    print(f"Database: {config['db_path']}")

    # Load existing transitions from database
    transitions_loaded = model.load_from_database(db)
    if transitions_loaded > 0:
        print(f"✓ Loaded {transitions_loaded} transitions from database")
    else:
        print("ℹ No previous training data found. Start by adding training text!")

    while True:
        show_menu()
        choice = input("Enter choice [1-5]: ").strip()

        if choice == "1":
            add_training_text(model, db, processor, tokenizer)
        elif choice == "2":
            generate_text(model, db, processor, tokenizer)
        elif choice == "3":
            show_stats(db)
        elif choice == "4":
            clear_database(db)
            db = Database(config["db_path"])
            model = MarkovModel(config["markov_order"])
        elif choice == "5":
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice, try again.")

    db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
