"""
Database utilities for compaction, reset, and model rebuilding.
"""

import argparse


def compact_database(db_path: str) -> None:
    """
    Compact transitions into states for faster generation.

    Args:
        db_path: Path to database file
    """
    pass  # TODO: Implement


def reset_database(db_path: str) -> None:
    """
    Clear all data from database.

    Args:
        db_path: Path to database file
    """
    pass  # TODO: Implement


def rebuild_model(db_path: str, order_n: int) -> None:
    """
    Rebuild Markov model from raw corpus.

    Args:
        db_path: Path to database file
        order_n: N-gram order
    """
    pass  # TODO: Implement


def show_stats(db_path: str) -> None:
    """
    Display database statistics.

    Args:
        db_path: Path to database file
    """
    pass  # TODO: Implement


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage Ollama-Markov database")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("compact", help="Compact transitions into states")
    subparsers.add_parser("reset", help="Clear all data from database")

    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild model from corpus")
    rebuild_parser.add_argument("--order", type=int, default=2, help="N-gram order")

    subparsers.add_parser("stats", help="Show database statistics")

    parser.add_argument("--db", default="ollama_markov.db", help="Database path")

    args = parser.parse_args()

    # TODO: Parse arguments and call appropriate function


if __name__ == "__main__":
    main()
