# Ollama-Markov

A low-power, general-purpose Markov chain text generator with an Ollama-compatible API. Train on any text corpus and generate coherent text through word-level Markov models.

**Not an LLM.** Lightweight, transparent, and predictably limited.

## Overview

Ollama-Markov provides:

- **Word-level Markov generation** (orders 2–3, scalable to 4–5)
- **Ollama-compatible API** — drop-in replacement for Ollama models
- **Incremental training** — accepts messages via HTTP API or batch imports
- **Dual modes**: Training mode (silent learning) or Live mode (learn + respond)
- **Safety filters** — PII scrubbing, blocklists, harassment detection, loop prevention
- **Transparent storage** — raw corpus and transitions stored for inspection and rebuilding

## How It Works

### Architecture

```
External Clients (Discord bot, etc.)
    ↓ (HTTP requests)
Ollama-Compatible API Server
    ├─ Training Pipeline (filters, tokenization)
    ├─ Text Generator (Markov sampling)
    └─ Safety Filters
    ↓
SQLite Storage (corpus + transitions)
```

### Modes

**Training Mode:**
- Receives messages via API
- Adds to training corpus
- Returns minimal acknowledgment (no generation)
- Bootstrapping phase: build model from chat or imported data

**Live Mode:**
- Receives messages via API
- Adds to training corpus
- Generates and returns text response
- Running with active users

### Generation Pipeline

1. **Message received** via `/api/chat` or `/api/generate`
2. **Text processing** — normalize, tokenize, apply filters
3. **Model training** — update Markov transitions
4. **Response generation** (if Live mode):
   - Seed state selection from prompt/context
   - Weighted random sampling from transition distributions
   - Safety filtering (slur replacement, loop detection, etc.)
   - Return response

## Features

### Model & Training
- Single word-level Markov model (orders 2–3)
- Incremental learning from incoming messages
- Dual-phase storage: normalized writes → compacted reads for fast sampling
- Corpus size: ~20k–500k words for quality output
- Batch import from files (JSON, CSV, text) via `scripts/import_training_data.py`

### Safety Filters

**Training-time:**
- PII scrubbing (emails, phone numbers)
- Link normalization (URLs → `<URL>`)
- Mention masking (user mentions → `<USER>`)
- Skip code blocks, quotes, logs, long pastes
- Configurable minimum message length

**Generation-time:**
- Blocklist/slur detection and replacement
- Harassment phrase detection
- Mention suppression (`@everyone`, `@here`, raw mentions)
- Loop detection (abort on repetition)
- Entropy gating (low-entropy backoff)

## API

Ollama-compatible HTTP endpoints:

```bash
# List available models
curl http://localhost:11434/api/tags

# Generate from a prompt
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-markov",
    "prompt": "The answer is",
    "stream": false
  }'

# Chat interface (also trains on messages)
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-markov",
    "messages": [
      {"role": "user", "content": "Hello there"}
    ]
  }'
```

For HTTPS (if SSL_ENABLED=true), use `https://` instead of `http://`

Both endpoints:
- **Accept** the Ollama request format
- **Train** on user messages (when allowed)
- **Generate** response (in Live mode) or return status (in Training mode)
- **Return** Ollama-compatible response format

### OpenAI-Compatible Endpoints

For web interfaces and OpenAI-compatible clients:

```bash
# List available models
curl http://localhost:11434/v1/models

# Chat completion (OpenAI format)
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-markov",
    "messages": [
      {"role": "user", "content": "Hello there"}
    ],
    "temperature": 0.8,
    "max_tokens": 500
  }'
```

These endpoints:
- **Accept** OpenAI-format requests
- **Train** on user messages (same as Ollama endpoints)
- **Generate** responses in Live mode
- **Return** OpenAI-compatible response format

## Getting Started

### Requirements
- Python 3.9+
- SQLite (included with Python)
- Flask (HTTP server)

### Installation

```bash
git clone https://github.com/yourusername/Ollama-Markov.git
cd Ollama-Markov
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Fetch Reddit Data (Optional Tool - Separate Directory)

The Reddit scraper tool is located in a separate `reddit_tools/` directory to keep it completely independent from the core project.

**The core Ollama-Markov server has zero dependencies on Reddit or any scraping functionality.**

To bootstrap the model with Reddit posts and comments:

```bash
# Fetch 25 posts + 100 comments per post from r/sysadmin
python reddit_tools/fetch_reddit_training_data.py sysadmin --posts 25 --comments 100

# This trains the model directly via the Markov database
# (no intermediate JSON file needed)
```

**Scraper features:**
- Automatic rate limiting (respects Reddit's 2+ second guideline)
- Crawls posts and comments recursively
- Filters deleted/removed content
- Real-time Markov model training
- Separate deduplication tracking (doesn't pollute core database)

**For complete usage guide, see [design-spec.md](design-spec.md#reddit-scraper-optional-tool).**

### Quick Test (No API)

Try the built-in test scripts to verify the Markov model is working:

**Option 1: Automated Test**
```bash
python test_markov.py
```
This trains on 10 sample sentences and shows generation examples.

**Option 2: Interactive Test**
```bash
python interactive_test.py
```
Fully interactive menu to:
- Add training text
- Generate text
- View statistics
- Clear and reset

### Configuration

Create a `.env` file:
```
OLLAMA_PORT=11434
MODE=training
LOG_LEVEL=INFO
SSL_ENABLED=false
SSL_CERT=
SSL_KEY=
```

**MODE options:**
- `training` — accept messages, update model, return status (no responses)
- `live` — accept messages, update model, generate and return responses

**SSL/HTTPS options:**
- `SSL_ENABLED` — set to `true` to enable HTTPS (default: `false`)
- `SSL_CERT` — path to SSL certificate file (required if SSL_ENABLED=true)
- `SSL_KEY` — path to SSL private key file (required if SSL_ENABLED=true)

#### Enabling HTTPS

For development/testing with self-signed certificates:

```bash
# Install SSL support
pip install pyOpenSSL

# Generate self-signed certificate
python scripts/generate_ssl_cert.py

# Enable HTTPS in .env
SSL_ENABLED=true
SSL_CERT=/path/to/cert.pem
SSL_KEY=/path/to/key.pem
```

For production, use proper CA-signed certificates (Let's Encrypt, etc.).

### Running the Server

```bash
# Start the server
python -m ollama_markov.main

# In another terminal, import bootstrap data
python -m ollama_markov.scripts.import_training_data data.json --format json

# Or send messages via the API (external Discord bot, etc.)
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "ollama-markov", "messages": [{"role": "user", "content": "test message"}]}'
```

## Workflow

1. **Bootstrap** (optional): Import training data from files or Reddit

   **Option A: From local files**
   ```bash
   python -m ollama_markov.scripts.import_training_data \
       chat_history.csv --format csv --channel training
   ```

   **Option B: From Reddit (using optional tool)**
   ```bash
   python reddit_tools/fetch_reddit_training_data.py sysadmin --posts 50
   # Model is trained directly; no intermediate files needed
   ```

2. **Training phase**: Run in `MODE=training`, point external Discord bot at server
   - Discord bot listens to channels, sends messages to `/api/chat`
   - Ollama-Markov stores messages, returns acknowledgment
   - Build model from real-world usage

3. **Go Live**: Switch to `MODE=live`
   - Same API, now generates responses
   - Continues learning as messages arrive
   - External bot posts generated replies

## Design Principles

- **Transparent**: All transitions inspectable; no black-box learning
- **Rebuildable**: Raw corpus stored; models can be rebuilt with new tokenization
- **Lightweight**: Markov chains are simple, fast, compute-efficient
- **Focused**: General-purpose generator, not domain-specific
- **Safe**: Multiple filtering layers for harmful output

See [design-spec.md](design-spec.md) for complete technical details.

## Non-Goals

- Not a language model (no semantic understanding)
- No factual accuracy
- No long-term memory or reasoning
- No impersonation detection
- Not for critical systems

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Add license here]
