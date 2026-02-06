"""
CLI tool for batch importing training data from files.

Supports JSON, CSV, and plain text formats.
"""

import argparse
import json
import csv
from typing import Optional
from datetime import datetime

from ollama_markov.storage.database import Database
from ollama_markov.processing.text_processor import TextProcessor
from ollama_markov.model.markov import MarkovModel


class TrainingDataImporter:
    """Imports training data from various file formats."""

    def __init__(self, db, processor, model):
        """
        Initialize importer.

        Args:
            db: Database instance
            processor: TextProcessor instance
            model: MarkovModel instance
        """
        self.db = db
        self.processor = processor
        self.model = model

    def import_json(
        self, file_path: str, channel_id: str, user_id: str = "seed"
    ) -> int:
        """
        Import from JSON file.

        Expected format: array of {content, timestamp, ...}

        Args:
            file_path: Path to JSON file
            channel_id: Channel identifier
            user_id: User identifier (default: "seed")

        Returns:
            Number of messages imported
        """
        imported = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = [data]

            for item in data:
                content = item.get("content") or item.get("text") or item.get("message")
                if not content:
                    continue

                tokens = self.processor.preprocess(content)
                if tokens:
                    timestamp = item.get("timestamp")
                    self.db.add_message(user_id, channel_id, content, timestamp)
                    self.model.train(tokens)

                    for state, next_tokens in self.model.transitions.items():
                        for next_token, count in next_tokens.items():
                            self.db.add_transition(self.model.order, state, next_token, count)

                    imported += 1

        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            return 0

        return imported

    def import_csv(
        self, file_path: str, channel_id: str, content_column: str = "content"
    ) -> int:
        """
        Import from CSV file.

        Args:
            file_path: Path to CSV file
            channel_id: Channel identifier
            content_column: Column name containing message content

        Returns:
            Number of messages imported
        """
        imported = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if reader.fieldnames and content_column not in reader.fieldnames:
                    print(f"✗ Column '{content_column}' not found in CSV")
                    print(f"  Available columns: {', '.join(reader.fieldnames)}")
                    return 0

                for row in reader:
                    content = row.get(content_column)
                    if not content:
                        continue

                    tokens = self.processor.preprocess(content)
                    if tokens:
                        user_id = row.get("user_id", "csv_import")
                        self.db.add_message(user_id, channel_id, content)
                        self.model.train(tokens)

                        for state, next_tokens in self.model.transitions.items():
                            for next_token, count in next_tokens.items():
                                self.db.add_transition(self.model.order, state, next_token, count)

                        imported += 1

        except Exception as e:
            print(f"✗ Error reading CSV: {e}")
            return 0

        return imported

    def import_text(
        self, file_path: str, channel_id: str, one_per_line: bool = True
    ) -> int:
        """
        Import from plain text file.

        Args:
            file_path: Path to text file
            channel_id: Channel identifier
            one_per_line: If True, treat each line as a message

        Returns:
            Number of messages imported
        """
        imported = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if one_per_line:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        tokens = self.processor.preprocess(line)
                        if tokens:
                            self.db.add_message("text_import", channel_id, line)
                            self.model.train(tokens)

                            for state, next_tokens in self.model.transitions.items():
                                for next_token, count in next_tokens.items():
                                    self.db.add_transition(self.model.order, state, next_token, count)

                            imported += 1
                else:
                    # Treat entire file as one message
                    content = f.read().strip()
                    tokens = self.processor.preprocess(content)
                    if tokens:
                        self.db.add_message("text_import", channel_id, content)
                        self.model.train(tokens)

                        for state, next_tokens in self.model.transitions.items():
                            for next_token, count in next_tokens.items():
                                self.db.add_transition(self.model.order, state, next_token, count)

                        imported = 1

        except Exception as e:
            print(f"✗ Error reading text file: {e}")
            return 0

        return imported


def main():
    """CLI entry point: parse args and run import."""
    parser = argparse.ArgumentParser(
        description="Import training data into Ollama-Markov"
    )
    parser.add_argument("file", help="Path to data file")
    parser.add_argument(
        "--format", choices=["json", "csv", "text"], required=True, help="File format"
    )
    parser.add_argument("--channel", required=True, help="Channel identifier")
    parser.add_argument("--user", default="seed", help="User identifier (for JSON)")
    parser.add_argument("--column", default="content", help="CSV column name (for CSV)")
    parser.add_argument("--db", default="ollama_markov.db", help="Database path")
    parser.add_argument("--order", type=int, default=2, help="Markov order")

    args = parser.parse_args()

    # Initialize components
    db = Database(args.db)
    processor = TextProcessor({"min_message_length": 3})
    model = MarkovModel(args.order)

    # Load existing data
    loaded = model.load_from_database(db)
    if loaded > 0:
        print(f"ℹ Loaded {loaded} existing transitions")

    # Create importer
    importer = TrainingDataImporter(db, processor, model)

    # Run import
    print(f"\nImporting from {args.format} file: {args.file}")
    print(f"Channel: {args.channel}")

    if args.format == "json":
        imported = importer.import_json(args.file, args.channel, args.user)
    elif args.format == "csv":
        imported = importer.import_csv(args.file, args.channel, args.column)
    else:  # text
        imported = importer.import_text(args.file, args.channel)

    # Print results
    if imported > 0:
        print(f"✓ Successfully imported {imported} messages")
        stats = db.stats()
        print(f"\nDatabase stats:")
        print(f"  Messages: {stats['message_count']}")
        print(f"  Transitions: {stats['transition_count']}")
        print(f"  Total transition counts: {stats['total_transitions']}")
    else:
        print("✗ No messages imported")

    db.close()


if __name__ == "__main__":
    main()
