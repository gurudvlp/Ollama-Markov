#!/usr/bin/env python3
"""
Rebuild Markov transitions from raw corpus at a specified order.

This script reads all messages from the corpus and regenerates the transitions
table with the specified n-gram order. Useful when changing MARKOV_ORDER.

Usage:
    python scripts/rebuild_transitions.py --order 3
    python scripts/rebuild_transitions.py --order 3 --clear
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama_markov.storage.database import Database
from ollama_markov.model.markov import MarkovModel
from ollama_markov.processing.tokenizer import Tokenizer
from ollama_markov.processing.text_processor import TextProcessor


def rebuild_transitions(db_path: str, order: int, clear_existing: bool = False):
    """
    Rebuild transitions from corpus messages.

    Args:
        db_path: Path to database file
        order: N-gram order to build
        clear_existing: If True, clear existing transitions before rebuilding
    """
    print(f"Rebuilding transitions at order {order} from corpus...")
    print(f"Database: {db_path}")

    # Initialize components
    db = Database(db_path)
    tokenizer = Tokenizer()
    text_processor = TextProcessor(tokenizer)
    model = MarkovModel(order=order, tokenizer=tokenizer)

    # Get corpus statistics
    stats = db.stats()
    total_messages = stats['message_count']
    print(f"\nCorpus contains {total_messages} messages")

    if clear_existing:
        print(f"Clearing existing order-{order} transitions...")
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM transitions WHERE order_n = ?", (order,))
        cursor.execute("DELETE FROM states WHERE order_n = ?", (order,))
        db.conn.commit()
        print("Cleared.")

    # Process messages in batches
    batch_size = 100
    offset = 0
    processed = 0
    total_transitions = 0

    print(f"\nProcessing messages (batch size: {batch_size})...")

    while True:
        # Get batch of messages
        messages = db.get_messages(limit=batch_size, offset=offset)

        if not messages:
            break

        # Train on each message
        for msg in messages:
            content = msg['content']
            tokens = text_processor.preprocess(content)

            if tokens:
                # Train model (this updates model.transitions in-memory)
                model.train(tokens)
                processed += 1

        # Save transitions to database in batch
        transitions = []
        for state, next_tokens in model.transitions.items():
            for next_token, count in next_tokens.items():
                transitions.append((order, state, next_token, count))

        if transitions:
            db.add_transitions_batch(transitions)
            total_transitions += len(transitions)

            # Clear in-memory transitions to avoid double-counting
            model.transitions.clear()

        # Progress update
        offset += batch_size
        print(f"  Processed {processed}/{total_messages} messages, {total_transitions} transitions created", end='\r')

    print(f"\n\nRebuild complete!")
    print(f"  Messages processed: {processed}")
    print(f"  Transitions created: {total_transitions}")

    # Show updated stats
    stats = db.stats()
    print(f"\nDatabase statistics:")
    print(f"  Total messages: {stats['message_count']}")
    print(f"  Total transitions (all orders): {stats['transition_count']}")
    print(f"  Total states (compacted): {stats['state_count']}")

    db.close()


def main():
    parser = argparse.ArgumentParser(description='Rebuild Markov transitions from corpus')
    parser.add_argument('--order', type=int, required=True, help='N-gram order (e.g., 2, 3, 4)')
    parser.add_argument('--db', type=str, default='ollama_markov.db', help='Database path')
    parser.add_argument('--clear', action='store_true', help='Clear existing transitions for this order first')

    args = parser.parse_args()

    if args.order < 1 or args.order > 10:
        print("Error: Order must be between 1 and 10")
        sys.exit(1)

    rebuild_transitions(args.db, args.order, args.clear)


if __name__ == '__main__':
    main()
