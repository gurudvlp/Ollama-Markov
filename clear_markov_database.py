#!/usr/bin/env python3
"""
Clear the Markov training database.

WARNING: This deletes all trained messages, transitions, and states.

Usage:
    python clear_markov_database.py [--db ollama_markov.db]
"""

import argparse
import sys
from ollama_markov.storage.database import Database


def main():
    parser = argparse.ArgumentParser(
        description="Clear Markov training database"
    )
    parser.add_argument(
        "--db",
        default="ollama_markov.db",
        help="Database path (default: ollama_markov.db)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("MARKOV DATABASE CLEAR")
    print("=" * 60)
    print(f"\nDatabase: {args.db}")
    print("\nThis will DELETE:")
    print("  ✗ All training messages")
    print("  ✗ All Markov transitions")
    print("  ✗ All compacted states")
    print("\n(Note: External tools may have their own tracking databases)")
    print("=" * 60)

    if not args.confirm:
        response = input("\nAre you sure? Type 'yes' to confirm: ").strip().lower()
        if response != "yes":
            print("Cancelled.")
            return 0

    try:
        db = Database(args.db)

        # Show stats before
        stats_before = db.stats()

        print(f"\nBefore clearing:")
        print(f"  Messages: {stats_before['message_count']}")
        print(f"  Transitions: {stats_before['transition_count']}")
        print(f"  States: {stats_before['state_count']}")
        print(f"  Total transition counts: {stats_before['total_transitions']}")

        # Clear
        db.clear_training_data()
        print("\n✓ Cleared training data...")

        # Show stats after
        stats_after = db.stats()
        print(f"\nAfter clearing:")
        print(f"  Messages: {stats_after['message_count']}")
        print(f"  Transitions: {stats_after['transition_count']}")
        print(f"  States: {stats_after['state_count']}")

        db.close()
        print("\n✓ Database cleared successfully")
        print("\nYou can now start fresh with new training data!")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
