"""
High-level text generation orchestration.

Combines Markov model, safety filters, and API logic.
"""

from typing import List, Dict, Optional


class Generator:
    """Orchestrates text generation for API endpoints."""

    def __init__(self, model, db, safety_filter, text_processor, config: Dict):
        """
        Initialize generator with dependencies.

        Args:
            model: MarkovModel instance
            db: Database instance
            safety_filter: SafetyFilter instance
            text_processor: TextProcessor instance
            config: Configuration dictionary
        """
        self.model = model
        self.db = db
        self.safety_filter = safety_filter
        self.text_processor = text_processor
        self.config = config

    def generate_from_prompt(self, prompt: str, options: Optional[Dict] = None) -> str:
        """
        Ollama /api/generate endpoint logic.

        Tokenizes prompt, selects seed state, generates text, and applies safety filters.

        Args:
            prompt: Input prompt text
            options: Optional generation options (temperature, top_k, num_predict, etc.)

        Returns:
            Generated text
        """
        # Extract options
        temperature = options.get('temperature', self.config['temperature']) if options else self.config['temperature']
        max_tokens = options.get('num_predict', self.config['max_tokens']) if options else self.config['max_tokens']
        top_k = options.get('top_k', None) if options else None

        # Preprocess and train
        tokens = self.text_processor.preprocess(prompt)

        if tokens:
            # Store message
            self.db.add_message("api", "generate", prompt)

            # Train model
            self.model.train(tokens)

            # Store transitions in batch
            transitions = []
            for state, next_tokens in self.model.transitions.items():
                for next_token, count in next_tokens.items():
                    transitions.append((self.model.order, state, next_token, count))

            if transitions:
                self.db.add_transitions_batch(transitions)

        # Check if should generate
        if not self._should_generate(self.config['mode']):
            return "Trained"

        # Generate response
        seed_state = self._select_seed_state(prompt)
        generated = self.model.generate(seed_state, max_tokens, temperature, top_k)

        if not generated:
            return "I don't have enough training data yet."

        # Apply safety
        safe_text = self._apply_safety(generated)

        return safe_text

    def generate_from_messages(
        self, messages: List[Dict], options: Optional[Dict] = None
    ) -> str:
        """
        Ollama /api/chat endpoint logic.

        Flattens message history, extracts seed state, generates response,
        and applies safety filters.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            options: Optional generation options

        Returns:
            Generated response text
        """
        # Extract user messages
        user_messages = [msg['content'] for msg in messages if msg.get('role') == 'user']

        if not user_messages:
            return "I don't have enough training data yet."

        # Train on each user message
        for msg_content in user_messages:
            tokens = self.text_processor.preprocess(msg_content)

            if tokens:
                self.db.add_message("api", "chat", msg_content)
                self.model.train(tokens)

                # Store transitions
                transitions = []
                for state, next_tokens in self.model.transitions.items():
                    for next_token, count in next_tokens.items():
                        transitions.append((self.model.order, state, next_token, count))

                if transitions:
                    self.db.add_transitions_batch(transitions)

        # Check if should generate
        if not self._should_generate(self.config['mode']):
            return "Trained"

        # Use last user message as context
        context = user_messages[-1]

        # Extract options and generate
        temperature = options.get('temperature', self.config['temperature']) if options else self.config['temperature']
        max_tokens = options.get('num_predict', self.config['max_tokens']) if options else self.config['max_tokens']
        top_k = options.get('top_k', None) if options else None

        seed_state = self._select_seed_state(context)
        generated = self.model.generate(seed_state, max_tokens, temperature, top_k)

        if not generated:
            return "I don't have enough training data yet."

        safe_text = self._apply_safety(generated)
        return safe_text

    def _select_seed_state(self, context: str) -> str:
        """
        Choose initial state for generation.

        Uses last N tokens from context, falls back to <START>.

        Args:
            context: Context text or prompt

        Returns:
            Seed state string
        """
        tokens = self.text_processor.tokenize(context)

        if not tokens:
            return ' '.join(['<START>'] * (self.model.order - 1))

        # Take last N tokens where N = order - 1
        seed_tokens = tokens[-(self.model.order - 1):] if len(tokens) >= self.model.order - 1 else tokens

        # Pad with <START> if needed
        while len(seed_tokens) < self.model.order - 1:
            seed_tokens.insert(0, '<START>')

        seed_state = ' '.join(seed_tokens)

        # Check if state exists in model
        if seed_state in self.model.transitions:
            return seed_state

        # Fall back to <START>
        return ' '.join(['<START>'] * (self.model.order - 1))

    def _apply_safety(self, text: str) -> str:
        """
        Apply post-generation safety filtering.

        Args:
            text: Generated text

        Returns:
            Sanitized text
        """
        is_safe, violations = self.safety_filter.check(text)

        if not is_safe:
            text = self.safety_filter.apply_fixes(text)

        return text

    def _should_generate(self, mode: str) -> bool:
        """
        Check if generation is allowed based on mode.

        Args:
            mode: Operating mode ('training' or 'live')

        Returns:
            True if generation should proceed
        """
        return mode == "live"
