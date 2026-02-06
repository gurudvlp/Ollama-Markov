"""
Core Markov chain model for text generation.

Maintains n-gram transition counts and provides text generation via weighted random sampling.
"""

from typing import List, Dict, Optional
from collections import defaultdict
import random
import pickle
import math


class MarkovModel:
    """Word-level Markov chain model for text generation."""

    def __init__(self, order: int = 2):
        """
        Initialize Markov model with n-gram order.

        Args:
            order: N-gram order (typically 2-3)
        """
        self.order = order
        self.transitions = defaultdict(lambda: defaultdict(int))

    def train(self, tokens: List[str]) -> None:
        """
        Add a sequence of tokens to the model.

        Updates transition counts for all n-grams of the specified order.

        Args:
            tokens: List of string tokens
        """
        if not tokens:
            return

        # Prepend START tokens and append END token
        full_sequence = ["<START>"] * (self.order - 1) + tokens + ["<END>"]

        # Create n-grams and update transitions
        for i in range(len(full_sequence) - self.order):
            # State is the current n-1 tokens
            state = " ".join(full_sequence[i : i + self.order - 1])
            # Next token is the token after the state
            next_token = full_sequence[i + self.order - 1]

            self.transitions[state][next_token] += 1

    def generate(
        self,
        seed_state: str,
        max_tokens: int,
        temperature: float = 1.0,
        top_k: Optional[int] = None,
    ) -> str:
        """
        Generate text starting from seed_state.

        Args:
            seed_state: Initial state for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0=deterministic, 1=default, >1=random)
            top_k: Restrict sampling to top K tokens (None=all)

        Returns:
            Generated text as string
        """
        if not seed_state:
            seed_state = " ".join(["<START>"] * (self.order - 1))

        generated_tokens = []
        current_state = seed_state

        for _ in range(max_tokens):
            # Get distribution for current state
            distribution = self.get_distribution(current_state)

            if not distribution:
                # No transitions from this state, stop generation
                break

            # Apply temperature and top_k filtering
            next_token = self._sample_token(distribution, temperature, top_k)

            if next_token == "<END>":
                break

            generated_tokens.append(next_token)

            # Update state: remove first token, add next_token
            state_tokens = current_state.split()
            state_tokens = state_tokens[1:] + [next_token]
            current_state = " ".join(state_tokens)

        return " ".join(generated_tokens)

    def get_distribution(self, state: str) -> Dict[str, float]:
        """
        Get next-token probability distribution for a state.

        Args:
            state: Current state (space-separated tokens)

        Returns:
            Dictionary mapping tokens to probabilities
        """
        if state not in self.transitions:
            return {}

        counts = self.transitions[state]
        total = sum(counts.values())

        if total == 0:
            return {}

        return {token: count / total for token, count in counts.items()}

    def _sample_token(
        self, distribution: Dict[str, float], temperature: float = 1.0,
        top_k: Optional[int] = None
    ) -> str:
        """
        Sample a token from a probability distribution.

        Args:
            distribution: Token probability distribution
            temperature: Sampling temperature
            top_k: Restrict to top K tokens

        Returns:
            Sampled token
        """
        if not distribution:
            return "<END>"

        # Apply top_k filtering
        if top_k is not None:
            sorted_tokens = sorted(
                distribution.items(), key=lambda x: x[1], reverse=True
            )
            distribution = dict(sorted_tokens[:top_k])

            # Renormalize
            total = sum(distribution.values())
            distribution = {token: prob / total for token, prob in distribution.items()}

        # Apply temperature
        if temperature <= 0:
            # Deterministic: return highest probability token
            return max(distribution.items(), key=lambda x: x[1])[0]

        if temperature != 1.0:
            # Adjust probabilities by temperature
            adjusted_dist = {}
            total = 0
            for token, prob in distribution.items():
                # Avoid log(0) and negative probabilities
                if prob > 0:
                    adjusted_prob = prob ** (1.0 / temperature)
                    adjusted_dist[token] = adjusted_prob
                    total += adjusted_prob

            if total > 0:
                distribution = {token: prob / total for token, prob in adjusted_dist.items()}

        # Sample using weighted random choice
        tokens = list(distribution.keys())
        probabilities = list(distribution.values())

        return random.choices(tokens, weights=probabilities, k=1)[0]

    def load_from_database(self, db) -> int:
        """
        Load transitions from database into model.

        Useful for continuing training from a previously trained model.

        Args:
            db: Database instance

        Returns:
            Number of transitions loaded
        """
        transitions_loaded = 0
        transitions_data = db.get_all_transitions()

        for order_n, state, next_token, count in transitions_data:
            if order_n == self.order:
                self.transitions[state][next_token] = count
                transitions_loaded += 1

        return transitions_loaded

    def save(self, filepath: str) -> None:
        """
        Serialize model to disk.

        Args:
            filepath: Path to save model file
        """
        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "order": self.order,
                    "transitions": dict(self.transitions),
                },
                f,
            )

    def load(self, filepath: str) -> None:
        """
        Deserialize model from disk.

        Args:
            filepath: Path to load model file from
        """
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            self.order = data["order"]
            self.transitions = defaultdict(lambda: defaultdict(int))
            for state, next_tokens in data["transitions"].items():
                self.transitions[state].update(next_tokens)
