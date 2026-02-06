# Project Structure & Implementation Guide

This document describes the code organization, class structure, and implementation details for Ollama-Markov.

## Directory Layout

```
ollama_markov/
├── __init__.py                          # Package initialization
├── config.py                            # Configuration management
├── logger.py                            # Logging setup
├── main.py                              # Entry point (HTTP server startup)
│
├── model/
│   ├── __init__.py
│   ├── markov.py                        # Core Markov model (training & generation)
│   ├── generator.py                     # High-level generation interface
│   └── tokenizer.py                     # Word-level tokenization
│
├── storage/
│   ├── __init__.py
│   ├── database.py                      # SQLite wrapper & queries
│   └── schema.py                        # Table definitions & migrations
│
├── processing/
│   ├── __init__.py
│   ├── text_processor.py                # Training filters & normalization
│   └── safety.py                        # Output-time safety filters
│
├── api/
│   ├── __init__.py
│   ├── server.py                        # Flask HTTP server
│   └── handlers.py                      # Endpoint handlers (/api/generate, /api/chat)
│
└── scripts/
    ├── __init__.py
    ├── import_training_data.py          # CLI tool for batch data import
    └── manage_database.py               # DB utilities (compact, reset, rebuild)
```

## Core Classes

### `model/markov.py` — MarkovModel

The core Markov chain implementation.

```python
class MarkovModel:
    def __init__(self, order: int = 2):
        """Initialize Markov model with n-gram order."""

    def train(self, tokens: List[str]) -> None:
        """
        Add a sequence of tokens to the model.
        Updates transition counts for all n-grams.
        """

    def generate(self, seed_state: str, max_tokens: int,
                 temperature: float = 1.0, top_k: int = None) -> str:
        """
        Generate text starting from seed_state.
        - temperature: 0 = deterministic, 1 = default, >1 = more random
        - top_k: restrict sampling to top K tokens (or None for all)
        Returns generated text as string.
        """

    def get_distribution(self, state: str) -> Dict[str, float]:
        """
        Get next-token probability distribution for a state.
        Returns {token: probability, ...}
        """

    def save(self, filepath: str) -> None:
        """Serialize model to disk."""

    def load(self, filepath: str) -> None:
        """Deserialize model from disk."""
```

**Responsibilities:**
- Maintain n-gram transition counts
- Weighted random sampling
- Probability calculation

---

### `storage/database.py` — Database

SQLite interface for corpus and transitions.

```python
class Database:
    def __init__(self, db_path: str):
        """Initialize or connect to SQLite database."""

    def add_message(self, user_id: str, channel_id: str,
                    content: str, timestamp: datetime = None) -> int:
        """Store raw message in corpus table. Returns message ID."""

    def add_transition(self, order_n: int, state: str,
                       next_token: str, count: int = 1) -> None:
        """Record or increment n-gram transition count."""

    def get_state(self, order_n: int, state: str) -> Optional[Dict]:
        """
        Retrieve compacted state (from `states` table).
        Returns {dist_blob, total_count, updated_at} or None if not found.
        """

    def get_messages(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Retrieve messages from corpus for inspection/rebuilding."""

    def compact(self) -> int:
        """
        Merge `transitions` table into `states` table.
        Returns number of rows compacted.
        """

    def delete_user_data(self, user_id: str) -> int:
        """Delete all messages from a user. Returns count deleted."""

    def rebuild_model(self, order_n: int, processor: TextProcessor) -> None:
        """
        Rebuild Markov model from raw corpus.
        Useful when changing tokenization or filters.
        """

    def stats(self) -> Dict:
        """Return database statistics (corpus size, transition count, etc.)"""
```

**Responsibilities:**
- CRUD operations for corpus and transitions
- Compaction job
- Data integrity and migrations

---

### `processing/text_processor.py` — TextProcessor

Training-time text filtering and normalization.

```python
class TextProcessor:
    def __init__(self, config: Dict):
        """Initialize with config (min_length, skip_patterns, etc.)"""

    def should_train(self, text: str, user_id: str = None) -> bool:
        """
        Decide if text should be added to training corpus.
        Checks: length, user rate limit, deduplication, etc.
        Returns True if text passes all filters.
        """

    def normalize(self, text: str) -> str:
        """
        Replace sensitive/structural elements with tokens:
        - URLs → <URL>
        - User mentions → <USER>
        - Emails → <EMAIL>
        - Phone numbers → <PHONE>
        Returns normalized text.
        """

    def tokenize(self, text: str) -> List[str]:
        """
        Split text into word tokens.
        Preserves punctuation as separate tokens where applicable.
        Returns list of tokens.
        """

    def preprocess(self, text: str) -> Optional[str]:
        """
        Full pipeline: normalize → tokenize → check training eligibility.
        Returns normalized text or None if should not train.
        """

    def is_code_block(self, text: str) -> bool:
        """Detect code blocks, stack traces, etc."""

    def is_short(self, text: str) -> bool:
        """Check if text is below minimum length."""
```

**Responsibilities:**
- Input validation and filtering
- Text normalization
- Tokenization
- Deduplication and rate limiting

---

### `processing/safety.py` — SafetyFilter

Output-time safety filtering.

```python
class SafetyFilter:
    def __init__(self, config: Dict):
        """Initialize with blocklists, harassment patterns, etc."""

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check text for safety violations.
        Returns (is_safe, [violations_found]).
        """

    def apply_fixes(self, text: str) -> str:
        """
        Fix unsafe content:
        - Replace slurs with neutral tokens
        - Suppress mentions (@everyone, user IDs)
        - Remove harassment phrases
        Returns sanitized text.
        """

    def has_mention(self, text: str) -> bool:
        """Detect @mentions, @everyone, etc."""

    def has_loop(self, text: str, prev_tokens: List[str]) -> bool:
        """Detect repetitive token sequences."""

    def get_entropy(self, state: str, distribution: Dict) -> float:
        """Calculate Shannon entropy of distribution. Low entropy = repetitive."""
```

**Responsibilities:**
- Detect unsafe content (slurs, harassment, loops)
- Apply fixes (replacement, suppression)
- Entropy gating for low-confidence outputs

---

### `model/generator.py` — Generator

High-level text generation orchestration.

```python
class Generator:
    def __init__(self, model: MarkovModel, db: Database,
                 safety_filter: SafetyFilter, text_processor: TextProcessor,
                 config: Dict):
        """Initialize generator with dependencies."""

    def generate_from_prompt(self, prompt: str, options: Dict = None) -> str:
        """
        Ollama /api/generate endpoint logic.
        - Tokenize prompt
        - Select seed state
        - Generate text
        - Apply safety filters
        Returns generated text.
        """

    def generate_from_messages(self, messages: List[Dict],
                               options: Dict = None) -> str:
        """
        Ollama /api/chat endpoint logic.
        - Flatten message history into context
        - Extract seed state
        - Generate response
        - Apply safety filters
        Returns generated text.
        """

    def _select_seed_state(self, context: str) -> str:
        """
        Choose initial state for generation.
        Strategy: use last N tokens from context, fall back to <START>.
        """

    def _apply_safety(self, text: str) -> str:
        """Post-generation safety filtering."""

    def _should_generate(self, mode: str) -> bool:
        """Check if generation is allowed based on mode (training/live)."""
```

**Responsibilities:**
- High-level generation workflow
- API endpoint logic
- Safety filter orchestration

---

### `api/server.py` — OllamaServer

Flask HTTP server.

```python
class OllamaServer:
    def __init__(self, generator: Generator, config: Dict):
        """Initialize Flask app with routes."""

    def start(self, host: str = "0.0.0.0", port: int = 11434) -> None:
        """Start Flask server."""

    @app.route('/api/generate', methods=['POST'])
    def handle_generate(self) -> Response:
        """Handle /api/generate endpoint."""

    @app.route('/api/chat', methods=['POST'])
    def handle_chat(self) -> Response:
        """Handle /api/chat endpoint."""
```

**Responsibilities:**
- HTTP routing
- Request/response formatting
- Error handling and logging

---

### `api/handlers.py` — Request Handlers

```python
def validate_request(data: Dict, endpoint: str) -> Tuple[bool, str]:
    """Validate Ollama-format request."""

def format_response(response_text: str, stream: bool = False) -> Dict:
    """Format response to Ollama specification."""

def handle_error(error: Exception) -> Response:
    """Format error responses."""
```

---

### `scripts/import_training_data.py` — TrainingDataImporter

Batch import tool.

```python
class TrainingDataImporter:
    def __init__(self, db: Database, processor: TextProcessor):
        """Initialize importer."""

    def import_json(self, file_path: str, channel_id: str,
                    user_id: str = "seed") -> int:
        """
        Import from JSON file (array of {content, timestamp, ...}).
        Returns number of messages imported.
        """

    def import_csv(self, file_path: str, channel_id: str,
                   content_column: str = "content") -> int:
        """Import from CSV file."""

    def import_text(self, file_path: str, channel_id: str,
                    one_per_line: bool = True) -> int:
        """Import from plain text (one message per line)."""

def main():
    """CLI entry point: parse args and run import."""
```

---

## Data Flow

### Request → Training → Response

```
Client Request (JSON)
    ↓
[api/server.py] Validate & parse request
    ↓
[api/handlers.py] Extract messages/prompt
    ↓
[processing/text_processor.py] Normalize & tokenize
    ↓
[storage/database.py] Store in corpus
    ↓
[model/markov.py] Update transitions
    ↓
(If MODE=live)
  [model/generator.py] Select seed state
    ↓
  [model/markov.py] Generate text
    ↓
  [processing/safety.py] Filter output
    ↓
(End)
    ↓
[api/server.py] Format & return response
    ↓
Client Response (JSON)
```

### Background: Compaction Job

```
[storage/database.py] Periodic timer/trigger
    ↓
Merge transitions → states
    ↓
Clear transitions table
```

---

## Module Dependencies

```
main.py
  ├─ config.py
  ├─ logger.py
  └─ api/server.py
      ├─ api/handlers.py
      ├─ model/generator.py
      │   ├─ model/markov.py
      │   ├─ storage/database.py
      │   ├─ processing/text_processor.py
      │   └─ processing/safety.py
      ├─ storage/database.py
      │   └─ storage/schema.py
      └─ model/tokenizer.py

scripts/import_training_data.py
  ├─ storage/database.py
  └─ processing/text_processor.py
```

---

## Configuration

Configuration is loaded from `.env` or environment variables:

```python
config = {
    "mode": "training",              # or "live"
    "ollama_port": 11434,
    "markov_order": 2,               # 2-3 recommended
    "compaction_interval": 1000,     # compact after N writes
    "max_tokens": 500,               # max generation length
    "temperature": 0.8,              # sampling temperature
    "min_message_length": 3,         # skip shorter messages
    "log_level": "INFO",
}
```

---

## Testing Strategy

Key test areas:

- **model/test_markov.py**: Training, generation, sampling
- **processing/test_text_processor.py**: Normalization, filtering, tokenization
- **processing/test_safety.py**: Blocklist detection, loop detection
- **storage/test_database.py**: CRUD, compaction, queries
- **api/test_handlers.py**: Request parsing, response formatting
- **integration/test_end_to_end.py**: Full request → response pipeline

---

## Performance Considerations

1. **Compaction**: Periodic merging of transitions → states improves query speed. Tune `COMPACTION_INTERVAL`.
2. **Corpus Size**: Store raw messages for rebuilding, but this increases DB size. Consider archival.
3. **Generation**: Sampling is fast (O(n) where n = vocabulary size). Temperature adjustments impact quality/diversity.
4. **Tokenization**: Word-level is faster than character-level; no need to optimize further.

---

## Implementation Priority

1. **Phase 1 (MVP)**: Core model, storage, API
   - MarkovModel, Database, TextProcessor, OllamaServer
   - Basic /api/chat endpoint (Training mode only)

2. **Phase 2**: Full API & modes
   - Generator, SafetyFilter
   - /api/generate endpoint
   - Live mode support

3. **Phase 3**: Polish & tooling
   - import_training_data.py script
   - manage_database.py utilities
   - Logging, metrics, monitoring
