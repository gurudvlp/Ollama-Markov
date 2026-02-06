"""
Output-time safety filtering.
"""

import re
import math
from typing import List, Dict, Tuple


class SafetyFilter:
    """Filters generated text for safety violations."""

    def __init__(self, config: Dict):
        """
        Initialize with mention patterns and thresholds.

        Args:
            config: Configuration dictionary with safety settings
        """
        self.config = config
        # Pattern matches @everyone, @here, <@digits>, @word
        self.mention_pattern = re.compile(r'@everyone|@here|<@\d+>|@\w+')
        self.loop_threshold = config.get('loop_threshold', 3)
        self.min_entropy = config.get('min_entropy', 0.5)

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check text for safety violations.

        Checks for:
        - Mentions (@everyone, @here, user mentions)
        - Repetitive loops (3+ consecutive repeated tokens)

        Args:
            text: Text to check

        Returns:
            Tuple of (is_safe, [violations_found])
        """
        violations = []

        if self.has_mention(text):
            violations.append("mention")

        if self.has_loop(text):
            violations.append("loop")

        is_safe = len(violations) == 0
        return (is_safe, violations)

    def apply_fixes(self, text: str) -> str:
        """
        Fix unsafe content.

        - Remove mentions (@everyone, user IDs, etc.)
        - Clean up extra whitespace

        Args:
            text: Text to fix

        Returns:
            Sanitized text
        """
        # Remove mentions
        fixed = self.mention_pattern.sub('', text)

        # Clean up extra whitespace
        fixed = ' '.join(fixed.split())

        return fixed

    def has_mention(self, text: str) -> bool:
        """
        Detect @mentions, @everyone, @here, etc.

        Args:
            text: Text to check

        Returns:
            True if mentions found
        """
        return bool(self.mention_pattern.search(text))

    def has_loop(self, text: str, prev_tokens: List[str] = None) -> bool:
        """
        Detect repetitive token sequences.

        Looks for 3+ consecutive identical tokens.

        Args:
            text: Generated text
            prev_tokens: Previously generated tokens (unused in MVP)

        Returns:
            True if repetition detected
        """
        tokens = text.split()

        if len(tokens) < 3:
            return False

        # Check for consecutive repeated tokens
        for i in range(len(tokens) - 2):
            if tokens[i] == tokens[i + 1] == tokens[i + 2]:
                return True

        return False

    def get_entropy(self, state: str, distribution: Dict) -> float:
        """
        Calculate Shannon entropy of distribution.

        Low entropy = repetitive/deterministic output.
        High entropy = diverse/varied output.

        Args:
            state: Current state
            distribution: Token probability distribution {token: probability}

        Returns:
            Normalized entropy value (0-1)
        """
        if not distribution:
            return 0.0

        entropy = 0.0
        for prob in distribution.values():
            if prob > 0:
                entropy -= prob * math.log2(prob)

        # Normalize by max possible entropy (uniform distribution)
        max_entropy = math.log2(len(distribution)) if len(distribution) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0
