#!/usr/bin/env python3
"""
Background worker for processing higher-order Markov transitions.

This worker runs continuously in the background and processes messages
that haven't been converted to higher-order transitions yet.

The API server trains order-2 immediately (fast), and this worker
processes order-3 and order-4 in the background (slower but thorough).

Usage:
    python scripts/background_worker.py
    python scripts/background_worker.py --db ollama_markov.db --orders 3,4
    python scripts/background_worker.py --interval 5 --batch-size 50
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama_markov.storage.database import Database
from ollama_markov.model.markov import MarkovModel
from ollama_markov.model.tokenizer import Tokenizer
from ollama_markov.processing.text_processor import TextProcessor


class BackgroundWorker:
    """Background worker for processing higher-order transitions."""

    def __init__(self, db_path: str, orders: List[int], batch_size: int = 10):
        """
        Initialize background worker.

        Args:
            db_path: Path to database file
            orders: List of orders to process (e.g., [3, 4])
            batch_size: Number of messages to process per batch
        """
        self.db_path = db_path
        self.orders = sorted(orders)
        self.batch_size = batch_size

        # Initialize components
        self.db = Database(db_path)

        # Create minimal config for TextProcessor
        config = {
            "min_message_length": 3
        }
        self.text_processor = TextProcessor(config)

        # Initialize tokenizer for MarkovModel
        self.tokenizer = Tokenizer()

        # Create a model for each order
        self.models = {
            order: MarkovModel(order=order, tokenizer=self.tokenizer)
            for order in orders
        }

        print(f"Background worker initialized")
        print(f"  Database: {db_path}")
        print(f"  Processing orders: {orders}")
        print(f"  Batch size: {batch_size}")

    def process_batch(self, order: int) -> int:
        """
        Process a batch of unprocessed messages for a specific order.

        Args:
            order: N-gram order to process

        Returns:
            Number of messages processed
        """
        # Get unprocessed messages
        messages = self.db.get_unprocessed_messages(order, limit=self.batch_size)

        if not messages:
            return 0

        model = self.models[order]
        processed_count = 0

        for msg in messages:
            message_id = msg['id']
            content = msg['content']

            # Preprocess and tokenize
            tokens = self.text_processor.preprocess(content)

            if not tokens:
                # Mark as processed even if no tokens (skip next time)
                self.db.mark_message_processed(message_id, order)
                continue

            # Train model (this updates transitions in-memory)
            model.train(tokens)

            # Save transitions to database
            transitions = []
            for state, next_tokens in model.transitions.items():
                for next_token, count in next_tokens.items():
                    transitions.append((order, state, next_token, count))

            if transitions:
                self.db.add_transitions_batch(transitions)

                # Clear in-memory transitions to avoid double-counting
                model.transitions.clear()

            # Mark message as processed
            self.db.mark_message_processed(message_id, order)
            processed_count += 1

        return processed_count

    def run_once(self) -> dict:
        """
        Run one iteration of processing for all orders.

        Returns:
            Dictionary with stats about this iteration
        """
        stats = {}

        for order in self.orders:
            processed = self.process_batch(order)
            stats[f'order_{order}'] = processed

        return stats

    def run_forever(self, interval: int = 10):
        """
        Run worker continuously with sleep interval between batches.

        Args:
            interval: Seconds to sleep between iterations
        """
        print(f"\nStarting continuous processing (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")

        iteration = 0

        try:
            while True:
                iteration += 1
                start_time = time.time()

                # Process one batch for each order
                stats = self.run_once()

                # Calculate elapsed time
                elapsed = time.time() - start_time

                # Print stats
                total_processed = sum(stats.values())

                if total_processed > 0:
                    print(f"[Iteration {iteration}] Processed {total_processed} messages in {elapsed:.2f}s")
                    for order, count in stats.items():
                        if count > 0:
                            print(f"  - {order}: {count} messages")

                    # Show overall progress
                    progress = self.db.get_processing_stats()
                    if progress:
                        print(f"  Overall progress:")
                        for order_n, stats_dict in progress.items():
                            pending = stats_dict['pending']
                            processed = stats_dict['processed']
                            total = stats_dict['total']
                            pct = (processed / total * 100) if total > 0 else 0
                            print(f"    Order {order_n}: {processed}/{total} ({pct:.1f}%) - {pending} pending")
                else:
                    # No work to do, show idle message periodically
                    if iteration % 10 == 0:
                        print(f"[Iteration {iteration}] Idle - no messages to process")

                # Sleep before next iteration
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
            self.db.close()
            print("Background worker stopped.")


def main():
    parser = argparse.ArgumentParser(description='Background worker for higher-order Markov transitions')
    parser.add_argument('--db', type=str, default='ollama_markov.db', help='Database path')
    parser.add_argument(
        '--orders',
        type=str,
        default='3,4',
        help='Comma-separated list of orders to process (e.g., "3,4")'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Seconds between processing iterations'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of messages to process per batch'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (instead of continuous loop)'
    )

    args = parser.parse_args()

    # Parse orders
    try:
        orders = [int(o.strip()) for o in args.orders.split(',')]
    except ValueError:
        print(f"Error: Invalid orders format: {args.orders}")
        print("Example: --orders 3,4")
        sys.exit(1)

    # Validate orders
    for order in orders:
        if order < 2 or order > 10:
            print(f"Error: Order {order} is out of range (2-10)")
            sys.exit(1)

    # Create worker
    worker = BackgroundWorker(args.db, orders, args.batch_size)

    if args.once:
        # Run once and exit
        print("\nRunning single iteration...")
        stats = worker.run_once()
        total_processed = sum(stats.values())
        print(f"\nProcessed {total_processed} messages")
        for order, count in stats.items():
            if count > 0:
                print(f"  - {order}: {count} messages")
        worker.db.close()
    else:
        # Run continuously
        worker.run_forever(interval=args.interval)


if __name__ == '__main__':
    main()
