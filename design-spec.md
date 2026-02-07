# Ollama-Markov (Design Spec)

## Overview
Ollama-Markov is a general-purpose Markov-chain–based text generation server. It accepts messages via an Ollama-compatible HTTP API, trains incrementally on incoming data, and generates coherent text using word-level Markov models.

Designed to be a lightweight, transparent, and inspectable text generator—not an LLM, not a general conversational AI. It provides a drop-in API replacement for Ollama models, making it suitable as a backend for external applications (Discord bots, chatbots, etc.).

---

## Operational Modes

### Training Mode
- Accepts incoming messages via HTTP API
- Adds messages to training corpus and updates Markov transitions
- Returns minimal acknowledgment (status: "trained")
- No text generation
- Used for bootstrapping the model before going live

### Live Mode
- Accepts incoming messages via HTTP API
- Adds messages to training corpus and updates Markov transitions
- Generates and returns text response
- Response behavior configurable (sampling temperature, max length, etc.)
- Model continues learning as it receives new messages

---

## High-Level Architecture

### Core Components

The Ollama-Markov server is a **self-contained, general-purpose text generator** with zero external dependencies:

- **HTTP API Server (Python)**
  - Ollama-compatible endpoints (`/api/generate`, `/api/chat`)
  - Accepts messages for training and/or generation
  - Applies text processing and safety filters
  - Returns Ollama-compatible responses

- **Markov Model**
  - Maintains n-gram transition data (word-level)
  - Compacts transitions into probability distributions for fast sampling
  - Generates text via weighted random selection

- **Storage Backend**
  - SQLite database
  - Raw message corpus (for rebuilding, auditing, deletion)
  - Normalized transitions (write-optimized)
  - Compacted states (read-optimized)

- **Text Processing Pipeline**
  - Training-time filters and normalization
  - Tokenization (word-level)
  - PII scrubbing, link/mention replacement

- **Safety Filters**
  - Generation-time filtering (blocklists, harassment detection, loop prevention)
  - Configurable replacement strategies

### Optional Tools (Separate)

External tools like the **Reddit scraper** are kept in a separate `reddit_tools/` directory:
- Completely decoupled from the core project
- Maintain their own tracking databases
- Use only public API methods from the core database
- Can be extended, replaced, or removed without affecting the server

**The core server has ZERO knowledge of or dependencies on Reddit, scrapers, or external data sources.**

**For implementation details, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) which describes class definitions, module organization, and code structure.**

---

## Markov Model

### Tokenization
A single word-level model is trained and maintained:

- **Tokens**: words + punctuation
- **Orders**: 2–3 initially, configurable up to 4–5 with sufficient data
- **Strengths**: structural coherence, phrase-level patterns, semantic flow, predictable output
- **Data requirement**: ~20k–100k words for order-2; scales up with higher orders

### Output Characteristics
Output voice and style are determined by:
- **Corpus choice**: trained text naturally shapes generation style
- **Sampling temperature**: higher = more randomness, lower = more predictable
- **Transition probabilities**: reflect phrase patterns from training data
- Optional output conditioning: prefix/suffix injection (configurable)

---

## Training / Ingestion Pipeline

### Input Sources
- Messages via HTTP API (`/api/generate`, `/api/chat`)
- Batch imports from files (JSON, CSV, text) via `scripts/import_training_data.py`
- Reddit posts and comments via `fetch_reddit_training_data.py` (bootstrapping)
- Any external client (Discord bot, chatbot, etc.)

### Reddit Scraper (Optional Tool)

The Reddit scraper is an **optional, separate tool** located in the `reddit_tools/` directory. It is completely decoupled from the core Ollama-Markov project.

**Note:** This tool is not part of the core project. The Ollama-Markov server has zero dependencies on Reddit or any scraping functionality.

#### Architecture

The Reddit scraper maintains two separate databases:

1. **Reddit Scraper Database** (`reddit_scraper.db`) - Tracks which Reddit posts/comments have been seen
   - Maintained by `reddit_tools/scraper_db.py`
   - Only used by the Reddit scraper
   - Separate from the core Markov database

2. **Markov Database** (`ollama_markov.db`) - Core training data
   - Used by the server and all clients
   - The scraper adds messages here using public API methods only
   - No Reddit-specific knowledge in the core database

#### Usage

```bash
python reddit_tools/fetch_reddit_training_data.py <subreddit> [options]
python reddit_tools/fetch_reddit_training_data.py sysadmin --posts 50 --comments 100
python reddit_tools/fetch_reddit_training_data.py <subreddit1> [subreddit2] [subreddit3] ... [options]
python reddit_tools/fetch_reddit_training_data.py sysadmin programming devops --posts 30
```

**Multiple Subreddits:**
You can specify multiple subreddits (space-separated) to scrape them all in a single command:

**Features:**
- Fetches hot posts from public subreddits
- Crawls comment threads recursively (includes nested replies)
- Automatic rate limiting (default 2 seconds between requests, respects Reddit guidelines)
- Filters deleted/removed content
- Deduplicates using internal tracking database
- Trains Markov model in real-time

**Options:**
- `--posts N`: Number of posts to fetch (default: 10, max: 100 per request)
- `--comments N`: Max comments per post (default: 100)
- `--no-comments`: Skip comments, posts only
- `--markov-db PATH`: Path to Markov database (default: `ollama_markov.db`)
- `--reddit-db PATH`: Path to Reddit scraper database (default: `reddit_scraper.db`)
- `--order N`: Markov order (default: 2)
- `--rate-limit SECONDS`: Delay between requests (default: 2.0)
- `--user-agent STRING`: Custom user agent

**Example Workflow:**
```bash
# Scrape one subreddit
python reddit_tools/fetch_reddit_training_data.py sysadmin --posts 25

# Scrape multiple subreddits in one command
python reddit_tools/fetch_reddit_training_data.py sysadmin programming devops --posts 30 --comments 150

# Scrape another subreddit separately
python reddit_tools/fetch_reddit_training_data.py python --posts 50 --comments 150

# Model is trained from all scraped data via the Markov database
```

**Recommendations:**
- Start with 10–25 posts, ~100 comments each for testing
- Scale to 50–100 posts for quality training (depends on subreddit activity)
- Reddit API is public and unauthenticated; respect rate limits
- Scrape multiple subreddits to blend corpora
- The scraper creates its own tracking database (`reddit_scraper.db`) to avoid duplicate processing
- Both databases should be kept in your project directory; add to `.gitignore` if they contain sensitive data

### Training-Time Filters
Applied before updating the Markov tables:
- Skip:
  - Code blocks and technical logs
  - Quoted/forwarded text (e.g., `>`)
  - Stack traces, error dumps, long pastes
  - Messages below minimum length (configurable)
- Normalize:
  - URLs → `<URL>`
  - User mentions → `<USER>`
  - Email addresses → `<EMAIL>`
  - Phone numbers → `<PHONE>`
  - Emojis: preserved or normalized (configurable)
- Deduplication: drop exact duplicates
- Optional: rate-limit per user/source

### Raw Message Storage
All accepted messages are stored verbatim in a corpus table so:
- The model can be rebuilt
- User data can be deleted on request
- Tokenization strategies can change later

---

## Storage Design (SQLite)

The core Markov database is completely independent of any external data sources, including Reddit.

### Core Markov Database Tables

#### Raw Corpus
```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  channel_id TEXT,
  user_id TEXT,
  content TEXT
);
```

#### Transition Data

**Normalized (write-optimized)**
```sql
CREATE TABLE transitions (
  order_n INTEGER,
  state_text TEXT,
  next_token TEXT,
  count INTEGER
);
```

**Compacted (read-optimized)**
```sql
CREATE TABLE states (
  order_n INTEGER,
  state_text TEXT,
  dist_blob BLOB,         -- packed map: next_token -> count
  total_count INTEGER,
  updated_at DATETIME
);
```

**Compaction Strategy:**
A background job (triggered after every N writes or on a timer, configurable) merges `transitions` into `states` for fast generation-time sampling. The `dist_blob` uses a compact binary format to store the probability distribution, reducing storage and improving sampling speed.

### Separate Reddit Scraper Database (Optional)

If using the Reddit scraper tool (`reddit_tools/`), a separate database is maintained:

```sql
CREATE TABLE reddit_messages (
  id INTEGER PRIMARY KEY,
  reddit_id TEXT UNIQUE,
  content TEXT,
  source_type TEXT,
  subreddit TEXT,
  imported BOOLEAN DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  imported_at DATETIME
);
```

This database is **not part of the core project** and is only used for deduplication within the scraper. The Markov database has zero awareness of Reddit or any scraper-specific tracking.

---

## Generation Pipeline

1. **Prompt Handling**
   - `/api/chat`: messages array is flattened into context
   - `/api/generate`: prompt used directly
2. **Seed State Selection**
   - Use last `n` tokens if available
   - Otherwise:
     - back off to lower order
     - or jump to `<START>` state
3. **Sampling Loop**
   - Weighted random choice from state distribution
   - Optional top-k restriction
   - Optional distribution flattening/sharpening
   - **Length biasing**: When `recommended_tokens` is set, the probability of selecting `<END>` is gradually increased as generation approaches and exceeds the recommended length
     - Uses sigmoid curve: `1 / (1 + e^(-0.2 * (current_length - 0.8 * recommended_length)))`
     - Starts boosting at ~80% of recommended length
     - Boost factor at recommended length: ~6x
     - Boost increases exponentially beyond recommended length
     - Still respects `max_tokens` as hard upper limit
     - Only applied if `<END>` token is available in current state's distribution
4. **Stopping Conditions**
   - `<END>` token (biased by length recommendations)
   - max tokens / characters
   - repetition detection
   - timeout

---

## Safety Filters

### Training-Time Safety
- Input scrubbing (PII, links, mentions)
- Channel and role allowlists
- Per-user rate limiting
- Opt-out and deletion support

### Output-Time Safety
- Blocklist detection (regex/token-based)
- Resample-on-fail strategy
- Replacement mode:
  - Slurs replaced with humorous neutral tokens (e.g. “clankers”)
  - Can be disabled or channel-scoped
- Harassment phrase detection:
  - e.g. “kill yourself”, “I will find you”
  - Triggers canned safe responses
- Mention suppression:
  - No `@everyone`, `@here`
  - No raw user mentions
- Loop detection:
  - Abort if repeating token sequences
- Entropy gating:
  - Low-entropy states trigger backoff or reset

---

## Ollama-Compatible API

### Endpoints

Both endpoints **train the model** on user messages. Behavior differs by mode:

#### `GET /api/tags`
- **Input**: None
- **Output**: List of available models in Ollama format
- **Use case**: Model discovery for Ollama clients
- **Response format**:
  ```json
  {
    "models": [
      {
        "name": "ollama-markov:latest",
        "model": "ollama-markov:latest",
        "modified_at": "2026-02-07T12:00:00Z",
        "size": 0,
        "digest": "markov-model",
        "details": {
          "parent_model": "",
          "format": "markov",
          "family": "markov",
          "families": ["markov"],
          "parameter_size": "0",
          "quantization_level": "N/A"
        }
      }
    ]
  }
  ```

#### `POST /api/generate`
- **Input**: `{ model, prompt, stream, options }`
- **Training Mode**: Adds prompt to corpus, returns `{ response: "Trained", done: true }`
- **Live Mode**: Adds prompt to corpus, generates text, returns `{ response: "<generated text>", done: true }`
- **Use case**: Raw prompt-based generation (equivalent to Ollama)

#### `POST /api/chat`
- **Input**: `{ model, messages: [{role, content}] }`
- **Training Mode**: Adds user messages to corpus, returns `{ message: {role: "assistant", content: "Trained"} }`
- **Live Mode**: Adds user messages to corpus, generates response, returns Ollama-format message
- **Use case**: Chat-style interaction with history (most common for Discord bots, etc.)

### Options
Both endpoints accept Ollama-standard options (via an `options` object in the request):
- `temperature`: Sampling temperature (higher = more random) — overrides TEMPERATURE
- `top_k`: Restrict to top K most likely tokens
- `num_predict`: Max tokens to generate — overrides MAX_TOKENS
- `recommended_tokens`: Target output length in tokens — overrides RECOMMENDED_TOKENS
- `stop`: Stop sequences (future enhancement)

### Streaming
- Both endpoints support `stream: true` for token-by-token responses
- Uses chunked transfer encoding with newline-delimited JSON

### OpenAI-Compatible Endpoints

For compatibility with web interfaces and OpenAI-compatible clients, the server also provides:

#### `GET /v1/models`
- Returns list of available models
- No authentication required
- Response format:
  ```json
  {
    "object": "list",
    "data": [
      {
        "id": "ollama-markov",
        "object": "model",
        "created": 1706745600,
        "owned_by": "ollama-markov"
      }
    ]
  }
  ```

#### `POST /v1/chat/completions`
- OpenAI-compatible chat completion endpoint
- Accepts OpenAI-format requests with `messages`, `temperature`, `max_tokens`
- Maps parameters:
  - `temperature` → sampling temperature
  - `max_tokens` → maximum tokens to generate
  - `top_k` → top-k sampling
- Returns OpenAI-format responses with message and usage info
- Includes `system_fingerprint: "fp_ollama"` for Ollama compatibility
- **Trains the model** on user messages (same as Ollama endpoints)
- Example request:
  ```json
  {
    "model": "ollama-markov",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.8,
    "max_tokens": 500
  }
  ```
- Example response:
  ```json
  {
    "id": "chatcmpl-1234567890",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "ollama-markov",
    "system_fingerprint": "fp_ollama",
    "choices": [{
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Generated response text"
      },
      "finish_reason": "stop"
    }],
    "usage": {
      "prompt_tokens": 0,
      "completion_tokens": 0,
      "total_tokens": 0
    }
  }
  ```

---

## Deployment & Operation

### Startup & Configuration
- Configuration loaded from `.env` file (using python-dotenv) or environment variables
- `.env` file must be in the project root directory
- Key settings:
  - `MODE`: `training` or `live`
  - `OLLAMA_PORT`: HTTP server port (default 11434)
  - `MARKOV_ORDER`: n-gram order (default 2–3)
  - `COMPACTION_INTERVAL`: how often to merge transitions (time-based or write-based)
  - `RECOMMENDED_TOKENS`: Target output length in tokens (default 50, ~2-3 sentences)
  - `MAX_TOKENS`: Maximum output length in tokens (default 500, hard limit)
  - `TEMPERATURE`: Sampling temperature (default 0.8, 0=deterministic, >1=random)
  - `SSL_ENABLED`: Enable HTTPS (default false)
  - `SSL_CERT`: Path to SSL certificate file
  - `SSL_KEY`: Path to SSL private key file

### SSL/HTTPS Support

The server supports HTTPS for secure client connections:

**Configuration:**
- Set `SSL_ENABLED=true` in `.env` or environment variables
- Provide paths to SSL certificate and key files
- For development, use the provided script to generate self-signed certificates:
  ```bash
  python scripts/generate_ssl_cert.py
  ```

**Notes:**
- Self-signed certificates will trigger security warnings in browsers/clients
- For production deployments, use CA-signed certificates (Let's Encrypt, etc.)
- Some Ollama clients may require HTTPS for network connections
- The Flask development server is used; for production, consider a proper WSGI server with reverse proxy

### Training Phase
1. Optional: Bootstrap with `scripts/import_training_data.py` (files → corpus)
2. Run server in `MODE=training`
3. External clients send messages via `/api/chat` or `/api/generate`
4. Server stores messages, updates model, returns status
5. Once corpus is sufficient, switch to Live mode

### Live Phase
1. Set `MODE=live`
2. Restart or reconfigure server
3. External clients send messages as before
4. Server stores messages, updates model, generates and returns responses
5. Continue learning from incoming data

### Monitoring
- Log all inputs, outputs, safety violations
- Optional stats tracking (corpus size, transition count, response latency)
- Database can be queried directly for transparency

---

## Corpus Size Guidelines

### Word Model
- **Order-2 (recommended starting point)**
  - Minimum viable: ~20k words (basic phrase patterns, expect rough output)
  - Good quality: ~100k–500k words (natural phrasing, stable behavior)
  - Excellent: 500k+ words (rich variety, confident structure)

- **Order-3 (higher fidelity)**
  - Minimum: ~100k words (sparse, inconsistent patterns)
  - Good: ~500k–2M words (much better coherence, nuanced transitions)
  - Excellent: 2M+ words (sophisticated phrase structures, high quality)

- **Higher orders (4+)**
  - Generally not recommended without 2M+ words
  - Risk of overfitting and repetition with smaller corpora

**Starting recommendation:** Begin with order-2 at ~50k words, then scale to order-3 as corpus grows. Discord message volume is usually sufficient to reach good-quality thresholds within weeks of active training.

---

## Explicit Non-Goals

- **Not an LLM**: No semantic understanding, reasoning, or planning
- **No factual accuracy**: Generates plausible text, not true information
- **No long-term memory**: Stateless generation; no conversation tracking across sessions
- **No reasoning**: Markov chains are statistical, not logical
- **Not for critical systems**: Limited capabilities are by design
- **No user impersonation detection**: Use with care in multi-user contexts

---

## Guiding Principles

- **Transparent**: All transitions are stored and inspectable. No black-box training.
- **Rebuildable**: Raw corpus preserved. Models can be rebuilt with different tokenization, orders, or filters.
- **Simple**: Markov chains are straightforward. No complex neural operations. Easy to understand and debug.
- **Lightweight**: Minimal CPU/memory. Can run on modest hardware.
- **Flexible**: General-purpose text generator. Works with any corpus, any domain.

---

## Implementation Status

### Current Features (Implemented)

**Core Functionality:**
- ✅ Word-level Markov model with configurable order (2-3 default)
- ✅ Ollama-compatible API endpoints (`/api/generate`, `/api/chat`, `/api/tags`)
- ✅ OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`)
- ✅ Dual-mode operation (Training and Live)
- ✅ Incremental training via HTTP API
- ✅ SQLite storage with raw corpus and transitions
- ✅ Text preprocessing and PII scrubbing
- ✅ Safety filters (blocklists, harassment detection)
- ✅ SSL/HTTPS support
- ✅ Streaming responses (word-by-word)

**Generation Control:**
- ✅ Temperature-based sampling
- ✅ Top-K token restriction
- ✅ **Output length control** (recommended and maximum tokens)
  - Configurable via `.env`: `RECOMMENDED_TOKENS` and `MAX_TOKENS`
  - Per-request override via `options` object
  - Sigmoid-based length biasing encourages natural stopping near target length
- ✅ Per-request option overrides

**Tools & Utilities:**
- ✅ Optional Reddit scraper (separate `reddit_tools/` directory)
- ✅ Batch import scripts for JSON/CSV/text files
- ✅ Interactive test script
- ✅ SSL certificate generation script

### Latest Updates (2026-02-07)

**Added output length control:**
- New `RECOMMENDED_TOKENS` config setting (default: 50 tokens ≈ 2-3 sentences)
- Enhanced generation pipeline with sigmoid-based length biasing
- Automatic probability boost for `<END>` token as output approaches recommended length
- Per-request `recommended_tokens` option for dynamic control
- Updated documentation in README and design spec
