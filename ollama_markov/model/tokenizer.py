"""
Word-level tokenization for text processing.
"""

import re
from typing import List


class Tokenizer:
    """Tokenizes text into word tokens."""

    def __init__(self):
        """Initialize tokenizer."""
        # Pattern to match words, contractions, and separate punctuation
        self.word_pattern = re.compile(r"\b\w+(?:'\w+)?\b|[.!?,;:]")

    def tokenize(self, text: str) -> List[str]:
        """
        Split text into word tokens.

        Preserves punctuation as separate tokens where applicable.

        Args:
            text: Input text string

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Find all words and punctuation
        tokens = self.word_pattern.findall(text)
        return tokens

    def detokenize(self, tokens: List[str]) -> str:
        """
        Join tokens back into text.

        Args:
            tokens: List of tokens

        Returns:
            Reconstructed text
        """
        if not tokens:
            return ""

        result = []
        for i, token in enumerate(tokens):
            if i == 0:
                result.append(token)
            else:
                # Add space before most tokens, but not before punctuation
                if token in ".!?,;:":
                    result.append(token)
                else:
                    result.append(" " + token)

        return "".join(result)
