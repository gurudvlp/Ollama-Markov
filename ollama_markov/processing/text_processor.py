"""
Training-time text filtering and normalization.
"""

import re
from typing import List, Optional, Dict, Set


class TextProcessor:
    """Handles text normalization, filtering, and tokenization."""

    def __init__(self, config: Dict):
        """
        Initialize with configuration.

        Args:
            config: Configuration dictionary (min_length, skip_patterns, etc.)
        """
        self.config = config
        self.min_length = config.get("min_message_length", 3)
        self.seen_messages: Set[str] = set()  # For deduplication

        # Patterns for normalization
        self.url_pattern = re.compile(
            r"https?://\S+|www\.\S+", re.IGNORECASE
        )
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self.mention_pattern = re.compile(r"<@\d+>|@\w+|@everyone|@here")
        self.phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
        self.code_pattern = re.compile(r"```|```\w+|^    |^\t|Traceback|File \"|Error:|Exception:|raise ")

        # Tokenizer pattern
        self.word_pattern = re.compile(r"\b\w+(?:'\w+)?\b|[.!?,;:]")

    def should_train(self, text: str, user_id: Optional[str] = None) -> bool:
        """
        Decide if text should be added to training corpus.

        Checks: length, user rate limit, deduplication, etc.

        Args:
            text: Text to check
            user_id: Optional user identifier for rate limiting

        Returns:
            True if text passes all filters
        """
        # Check if too short
        if self.is_short(text):
            return False

        # Check if code block
        if self.is_code_block(text):
            return False

        # Check for deduplication
        if text in self.seen_messages:
            return False

        self.seen_messages.add(text)
        return True

    def normalize(self, text: str) -> str:
        """
        Replace sensitive/structural elements with tokens.

        - URLs → <URL>
        - User mentions → <USER>
        - Emails → <EMAIL>
        - Phone numbers → <PHONE>

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not isinstance(text, str):
            raise TypeError(f"Expected string, got {type(text).__name__}")

        if not text:
            return text

        # Replace URLs
        text = self.url_pattern.sub("<URL>", text)

        # Replace emails
        text = self.email_pattern.sub("<EMAIL>", text)

        # Replace mentions
        text = self.mention_pattern.sub("<USER>", text)

        # Replace phone numbers
        text = self.phone_pattern.sub("<PHONE>", text)

        return text

    def tokenize(self, text: str) -> List[str]:
        """
        Split text into word tokens.

        Preserves punctuation as separate tokens where applicable.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        if not isinstance(text, str):
            raise TypeError(f"Expected string, got {type(text).__name__}")

        if not text:
            return []

        tokens = self.word_pattern.findall(text)
        return tokens

    def preprocess(self, text: str) -> Optional[List[str]]:
        """
        Full pipeline: normalize → tokenize → check training eligibility.

        Args:
            text: Input text

        Returns:
            List of tokens or None if should not train
        """
        # Ensure input is a string
        if not isinstance(text, str):
            raise TypeError(f"Expected string, got {type(text).__name__}")

        if not self.should_train(text):
            return None

        normalized = self.normalize(text)
        tokens = self.tokenize(normalized)

        return tokens if tokens else None

    def is_code_block(self, text: str) -> bool:
        """
        Detect code blocks, stack traces, etc.

        Args:
            text: Text to check

        Returns:
            True if text appears to be code or a stack trace
        """
        if not text:
            return False

        return bool(self.code_pattern.search(text))

    def is_short(self, text: str) -> bool:
        """
        Check if text is below minimum length.

        Args:
            text: Text to check

        Returns:
            True if text is shorter than minimum
        """
        if not text:
            return True

        # Count tokens
        tokens = self.tokenize(text)
        return len(tokens) < self.min_length
