# Architecture Overview

## Core Server (No External Dependencies)

```
┌─────────────────────────────────────────────────────────────┐
│          Ollama-Markov Server (ollama_markov/)              │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ HTTP API Server (/api/generate, /api/chat)           │   │
│  │ - Accepts messages from any source                    │   │
│  │ - Routes to text processing pipeline                  │   │
│  │ - Returns Ollama-compatible responses                 │   │
│  └───────────────────────┬────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼────────────────────────────────┐   │
│  │ Text Processing                                        │   │
│  │ - Normalization                                        │   │
│  │ - Tokenization                                         │   │
│  │ - Safety filtering (PII scrubbing, etc.)              │   │
│  └───────────────────────┬────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼────────────────────────────────┐   │
│  │ Markov Model Training                                  │   │
│  │ - Update transitions                                   │   │
│  │ - Generate text (if live mode)                         │   │
│  │ - Apply output safety filters                          │   │
│  └───────────────────────┬────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼────────────────────────────────┐   │
│  │ Generic Database (storage/database.py)                 │   │
│  │ - Messages table (any source)                          │   │
│  │ - Transitions table (n-grams)                          │   │
│  │ - States table (compacted distributions)              │   │
│  │ - ZERO knowledge of external sources (Reddit, etc.)   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Point:** The core server is completely self-contained and has no knowledge of where training data comes from.

---

## Optional Reddit Scraper Tool (Separate Directory)

```
┌──────────────────────────────────────────────────────────────┐
│        Reddit Scraper Tool (reddit_tools/)                   │
│        [COMPLETELY INDEPENDENT OF CORE SERVER]               │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ fetch_reddit_training_data.py                        │    │
│  │ - Fetch posts/comments from public subreddits        │    │
│  │ - Check for duplicates (using reddit_scraper.db)     │    │
│  │ - Process and tokenize text                          │    │
│  │ - Train model via generic Database API               │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                         │
│  ┌──────────────────▼───────────────────────────────────┐    │
│  │ Reddit Scraper Database (scraper_db.py)              │    │
│  │ - Tracks which posts/comments have been processed     │    │
│  │ - Handles deduplication (reddit_scraper.db)          │    │
│  │ - Separate from core Markov database                  │    │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Generic Database Connection                           │    │
│  │ - Uses public API methods ONLY:                       │    │
│  │   - add_message()                                     │    │
│  │   - add_transition()                                  │    │
│  │   - stats()                                           │    │
│  │ - NO direct access to internal tables                 │    │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Key Points:**
- The Reddit scraper is completely optional
- It maintains its own tracking database
- It uses ONLY public API methods from the core Database class
- The core server has ZERO knowledge of Reddit

---

## Database Separation

### Core Markov Database (`ollama_markov.db`)

```sql
-- Used by the core server and all clients
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  channel_id TEXT,        -- Generic channel identifier
  user_id TEXT,           -- Generic user identifier
  content TEXT             -- Message content (from ANY source)
);

CREATE TABLE transitions (
  order_n INTEGER,
  state_text TEXT,
  next_token TEXT,
  count INTEGER
);

CREATE TABLE states (
  order_n INTEGER,
  state_text TEXT,
  dist_blob BLOB,
  total_count INTEGER,
  updated_at DATETIME
);
```

**Characteristics:**
- Completely generic
- No source-specific fields
- Works with any training data
- No Reddit references whatsoever

### Reddit Scraper Database (`reddit_scraper.db`)

```sql
-- Used ONLY by the Reddit scraper tool
CREATE TABLE reddit_messages (
  id INTEGER PRIMARY KEY,
  reddit_id TEXT UNIQUE,      -- Reddit-specific ID
  content TEXT,
  source_type TEXT,            -- "post" or "comment"
  subreddit TEXT,              -- Reddit-specific field
  imported BOOLEAN DEFAULT 0,
  created_at DATETIME,
  imported_at DATETIME
);
```

**Characteristics:**
- Reddit-specific fields and logic
- Only accessed by the scraper tool
- Never accessed by the core server
- Can be deleted without affecting the model

---

## Data Flow Examples

### Example 1: Discord Bot Using Core Server

```
Discord Message
    ↓
HTTP POST to /api/chat
    ↓
[Core Server]
    - Extract text
    - Process & tokenize
    - Update Markov model
    - Generate response
    - Return reply
    ↓
Discord Bot Posts Reply
```

**Database:** Only `ollama_markov.db` is used
**Core Server Knows:** Nothing about Discord

---

### Example 2: Reddit Scraper Training the Model

```
Reddit API
    ↓
fetch_reddit_training_data.py
    ├─ Check reddit_scraper.db for duplicates
    ├─ Fetch new posts/comments
    ├─ Process text
    │
    └─ Train via generic Database API
        ├─ Call add_message() → ollama_markov.db
        ├─ Call add_transition() → ollama_markov.db
        ├─ Update reddit_scraper.db tracking
        └─ Mark as imported

    ↓
Model Trained (ollama_markov.db updated)
```

**Databases:** Both `ollama_markov.db` and `reddit_scraper.db` are used
**Core Server Knows:** Nothing about the Reddit scraper (it only used generic API)

---

## Why This Matters

### Before Refactoring ❌

```
ollama_markov/storage/database.py
├── reddit_messages table
├── reddit_message_exists()
├── add_reddit_message()
├── mark_reddit_message_imported()
└── reddit_stats()

❌ Core server coupled to Reddit
❌ Can't remove Reddit without breaking database schema
❌ Unclear separation of concerns
❌ Hard to add other data sources
```

### After Refactoring ✅

```
ollama_markov/storage/database.py
├── messages table (generic)
├── transitions table (generic)
└── states table (generic)

reddit_tools/scraper_db.py
├── reddit_messages table
├── message_exists()
├── add_message()
├── mark_imported()
└── stats()

✅ Core server has ZERO Reddit dependencies
✅ Can delete reddit_tools/ without breaking anything
✅ Clear separation of concerns
✅ Easy to add other data sources (twitter_tools/, discord_tools/, etc.)
✅ Each tool is self-contained and optional
```

---

## Extension: Adding New Data Sources

This architecture makes it trivial to add new data sources:

### Add a Twitter Scraper

```
twitter_tools/
├── __init__.py
├── scraper_db.py          (Twitter-specific tracking)
└── fetch_twitter_data.py  (Twitter scraper)

# Uses same pattern: maintains own database, uses core API
python twitter_tools/fetch_twitter_data.py
```

### Add a Discord Importer

```
discord_tools/
├── __init__.py
├── importer_db.py         (Discord-specific tracking)
└── import_discord_data.py (Discord history importer)

# Uses same pattern: maintains own database, uses core API
python discord_tools/import_discord_data.py
```

---

## Summary

- **Core Server:** Completely generic, self-contained, no external dependencies
- **Optional Tools:** Completely separate directories, each with its own tracking
- **Database Architecture:** Clean separation between generic Markov DB and tool-specific tracking DBs
- **API Design:** All external tools use only public Database methods
- **Scalability:** Easy to add new tools without modifying core server
