# Reddit Scraper Refactoring - Summary

## Overview

Successfully refactored the codebase to completely separate Reddit scraping functionality from the core Ollama-Markov project. The core server now has **zero knowledge of or dependencies on Reddit**.

## Changes Made

### 1. Core Database (`ollama_markov/storage/database.py`)

**Removed:**
- `reddit_messages` table schema
- `reddit_message_exists()` method
- `add_reddit_message()` method
- `mark_reddit_message_imported()` method
- `reddit_stats()` method
- Comments in `clear_training_data()` about preserving Reddit tables

**Result:** The Database class is now purely generic, accepting messages from any source without knowledge of their origin.

### 2. New Reddit Tools Directory (`reddit_tools/`)

Created a separate directory structure for Reddit-specific functionality:

```
reddit_tools/
├── __init__.py                          # Package declaration
├── scraper_db.py                        # RedditScraperDB class
└── fetch_reddit_training_data.py        # Updated scraper script
```

### 3. Reddit Scraper Database (`reddit_tools/scraper_db.py`)

**New class:** `RedditScraperDB`
- Manages its own SQLite database (`reddit_scraper.db`)
- Handles Reddit-specific deduplication
- Tracks which posts/comments have been processed
- Methods:
  - `message_exists(reddit_id)` - Check for duplicates
  - `add_message(reddit_id, content, source_type, subreddit)` - Track new messages
  - `mark_imported(reddit_id)` - Mark as processed
  - `stats()` - Return Reddit-specific statistics
  - `close()` - Close database connection

**Key Design:**
- Completely independent from the core Markov database
- Only used by the Reddit scraper tool
- Can be replaced or removed without affecting the core server

### 4. Updated Reddit Scraper (`reddit_tools/fetch_reddit_training_data.py`)

**Changes:**
- Uses two separate databases:
  - `markov_db` (core Markov database) - for training data
  - `reddit_db` (Reddit scraper database) - for deduplication
- Now accepts command-line arguments for both database paths:
  - `--markov-db PATH`
  - `--reddit-db PATH`
- Uses only public, generic Database methods (`add_message()`, `add_transition()`)
- No Reddit-specific logic in the core project

**Updated flow:**
1. Fetch posts/comments from Reddit
2. Check `reddit_db` for duplicates
3. Add to `reddit_db` tracking
4. Process text and train via `markov_db` (using generic API)
5. Mark as imported in `reddit_db`

### 5. Documentation Updates

**design-spec.md:**
- Added "Optional Tools (Separate)" section
- Clarified that the core server has zero Reddit dependencies
- Updated Redis scraper section with new architecture
- Updated Storage Design to show separate Reddit database
- Added note about Reddit scraper using only public API methods

**README.md:**
- Updated "Fetch Reddit Data" section to point to `reddit_tools/`
- Changed workflow to show new direct-training approach
- Removed references to intermediate JSON files
- Added note: "The core Ollama-Markov server has zero dependencies on Reddit"

**.gitignore:**
- Removed outdated rule for root `fetch_reddit_training_data.py`
- Updated comments about runtime database files
- Properly ignores `*.db` files for both databases

### 6. File Changes

**Removed:**
- `fetch_reddit_training_data.py` (from root directory)

**Created:**
- `reddit_tools/__init__.py`
- `reddit_tools/scraper_db.py`
- `reddit_tools/fetch_reddit_training_data.py` (improved version)

**Modified:**
- `ollama_markov/storage/database.py` (removed Reddit code)
- `design-spec.md` (architecture documentation)
- `README.md` (usage instructions)
- `.gitignore` (updated rules)

## Verification

✓ No Reddit references in core database class
✓ Reddit tools properly separated in dedicated directory
✓ Two independent databases (Markov + Reddit tracking)
✓ Scraper uses only public Database API methods
✓ Documentation updated with new architecture
✓ Old Reddit scraper removed from root directory

## Usage

### Bootstrap with Reddit Data

```bash
# Scrape r/sysadmin and train the model directly
python reddit_tools/fetch_reddit_training_data.py sysadmin --posts 50

# Scrape multiple subreddits to build a diverse model
python reddit_tools/fetch_reddit_training_data.py programming --posts 25
python reddit_tools/fetch_reddit_training_data.py learnprogramming --posts 25

# The model is trained directly; no intermediate files needed
# Running stats will show the trained model size
```

### Start the Core Server

```bash
# The server is completely independent of Reddit
python -m ollama_markov.main

# It will use the ollama_markov.db created by the scraper
# The reddit_scraper.db is never accessed by the core server
```

## Architecture Principles

1. **Separation of Concerns**: Reddit scraping is completely separate from text generation
2. **Zero Dependencies**: The core server has no knowledge of Reddit or external sources
3. **Public API**: The scraper uses only public, generic methods from the Database class
4. **Modularity**: The Reddit tools can be replaced, upgraded, or removed without affecting the core
5. **Independent Tracking**: Each tool maintains its own state and deduplication logic

## Future Extensions

This architecture makes it easy to add other data sources:

1. Twitter scraper → `twitter_tools/` directory
2. Discord history importer → `discord_tools/` directory
3. Custom corpus import → `import_tools/` directory

Each would:
- Have its own directory
- Maintain its own tracking database
- Use only public Database API methods
- Be completely independent of the core server
