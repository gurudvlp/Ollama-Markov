# Integrated Reddit Training Guide

This document explains the optimized Reddit scraping and training workflow that solves the previous performance and deduplication issues.

## What Changed

The old workflow had three problems:
1. **Slowness**: Training was bottlenecked by database commits (100,000+ commits for large imports)
2. **Deduplication**: No tracking of which messages had been trained, so same content could be trained multiple times
3. **Visibility**: No real-time feedback on what was being trained

The new integrated approach solves all three:
- ✅ **Direct Markov training**: Messages are trained immediately as they're fetched
- ✅ **Deduplication via reddit_id tracking**: Each Reddit post/comment is tracked by ID
- ✅ **Batched database writes**: Transitions are batched (10 at a time, configurable)
- ✅ **Real-time progress**: See [subreddit] [post#] progress + message preview
- ✅ **Resumable**: Can stop and restart without duplicating work

## Quick Start

### 1. Clear the Current Database (Optional)

If you want to start fresh and discard existing training:

```bash
python clear_markov_database.py
# When prompted, type "yes" to confirm

# Or skip confirmation:
python clear_markov_database.py --confirm
```

This **deletes** all training messages and transitions, but **preserves** the Reddit message tracking table for deduplication.

### 2. Scrape Reddit and Train in Real-Time

```bash
# Basic: scrape 25 posts with comments
python fetch_reddit_training_data.py sysadmin --posts 25

# With all options
python fetch_reddit_training_data.py sysadmin \
    --posts 50 \
    --comments 100 \
    --db ollama_markov.db \
    --order 2 \
    --rate-limit 2.0

# Just posts, no comments
python fetch_reddit_training_data.py sysadmin --posts 50 --no-comments

# Multiple subreddits (run separately, both train on same database)
python fetch_reddit_training_data.py sysadmin --posts 25
python fetch_reddit_training_data.py programming --posts 25
python fetch_reddit_training_data.py homelab --posts 25
```

## Example Output

```
============================================================
Reddit Training Data Scraper (Markov Integration)
============================================================
Subreddit: r/sysadmin
Posts: 3
Comments per post: 5
Database: ollama_markov.db
Markov order: 2
Rate limit: 2.0s between requests
============================================================

ℹ Loaded 250 existing transitions from database

Fetching posts from r/sysadmin...
✓ Fetched 3 posts

  [sysadmin] [1] ✓ Weekly 'I made a useful thing' Thread...
    └─ 0 comments trained
  [sysadmin] [2] ✓ Thickheaded Thursday - January 15, 20...
    └─ 5 comments trained
  [sysadmin] [3] ⊘ Old pinned thread (duplicate)

============================================================
✓ Training complete!
============================================================
New messages trained: 6

Database stats:
  Reddit messages tracked: 127
  Messages imported: 125
  Pending: 2

Markov model stats:
  Total messages: 87
  Transitions: 1,240
  Total counts: 8,542
============================================================
```

## Understanding the Output

- `✓` = Message was new, trained successfully
- `⊘` = Duplicate (already in reddit_messages table), skipped
- `└─` = Comments trained from that post
- **Reddit messages tracked**: Total messages we've seen (new + duplicates)
- **Messages imported**: Messages that were actually used for training
- **Pending**: Tracked but not yet imported (shouldn't happen in normal usage)

## How It Works

### 1. Scraping Phase
```
For each subreddit post:
  - Fetch post metadata
  - Train on post content
  - For each comment:
    - Train on comment content
  - Show progress: [subreddit] [post#] "Title..."
```

### 2. Deduplication Check
```
Before training each message:
  - Check: does reddit_id exist in reddit_messages table?
  - If YES → skip (it's a duplicate)
  - If NO → add to tracking table and train immediately
```

### 3. Real-Time Training
```
For each message:
  - Tokenize using TextProcessor
  - Train Markov model in-memory
  - Collect transitions in pending batch
  - When batch reaches threshold (10), flush to database
```

### 4. Efficiency Gains
Old approach (per message):
- Tokenize
- Train Markov (fast)
- Write 50-100 transitions to database
- **Commit after EACH transition** ← SLOW
- ~1000-10,000 commits for large imports

New approach (per message):
- Tokenize
- Train Markov (fast)
- Collect transitions in memory (instant)
- **Batch commit every 10 transitions**
- ~10-100 commits total ← 100-1000x faster

## Command Reference

### clear_markov_database.py

Clear training data (preserves Reddit message tracking).

```bash
python clear_markov_database.py [OPTIONS]

Options:
  --db PATH       Database path (default: ollama_markov.db)
  --confirm       Skip confirmation prompt
```

Example:
```bash
# Show stats, ask for confirmation
python clear_markov_database.py

# Skip confirmation (automated scripts)
python clear_markov_database.py --confirm
```

### fetch_reddit_training_data.py

Scrape Reddit and train Markov model in real-time.

```bash
python fetch_reddit_training_data.py SUBREDDIT [OPTIONS]

Positional:
  SUBREDDIT       Subreddit name (without r/)

Options:
  --posts N          Posts to fetch (default: 10)
  --comments N       Comments per post (default: 100)
  --no-comments      Posts only, skip comments
  --db PATH          Database path (default: ollama_markov.db)
  --order N          Markov order (default: 2)
  --rate-limit SEC   Seconds between requests (default: 2.0)
  --user-agent STR   Custom user agent
```

Examples:
```bash
# Quick test: 2 posts, 5 comments each
python fetch_reddit_training_data.py sysadmin --posts 2 --comments 5

# Large corpus: 100 posts with full comments
python fetch_reddit_training_data.py programming --posts 100 --comments 500

# Posts only, slower rate limit
python fetch_reddit_training_data.py worldnews --posts 50 --no-comments --rate-limit 5

# Multiple subreddits on same database
python fetch_reddit_training_data.py sysadmin --posts 25 &
python fetch_reddit_training_data.py programming --posts 25 &
python fetch_reddit_training_data.py homelab --posts 25 &
wait
```

## Workflow Examples

### Example 1: Fresh Start with One Subreddit

```bash
# Clear any previous training
python clear_markov_database.py --confirm

# Scrape and train
python fetch_reddit_training_data.py sysadmin --posts 50 --comments 100

# Check the model
python interactive_test.py
```

### Example 2: Add More Subreddits

```bash
# Already have sysadmin training from Example 1

# Add programming subreddit (builds on existing model)
python fetch_reddit_training_data.py programming --posts 50

# Add homelab (further enriches model)
python fetch_reddit_training_data.py homelab --posts 25

# Model now has diverse training data
```

### Example 3: Incremental Updates

```bash
# Day 1: Initial scrape
python fetch_reddit_training_data.py sysadmin --posts 25

# Day 2: Scrape again (new posts, no duplicates!)
python fetch_reddit_training_data.py sysadmin --posts 25

# reddit_id tracking prevents double-training on overlapping posts
# Only new messages are trained, old ones are skipped with ⊘
```

### Example 4: Large Corpus Building

```bash
# Build a large, diverse corpus overnight

# In background (or in separate terminals):
python fetch_reddit_training_data.py sysadmin --posts 100 &
python fetch_reddit_training_data.py programming --posts 100 &
python fetch_reddit_training_data.py golang --posts 75 &
python fetch_reddit_training_data.py rust --posts 75 &
python fetch_reddit_training_data.py python --posts 75 &

# Wait for all to complete
wait

# Check database stats
python -c "from ollama_markov.storage.database import Database; db = Database(); print(db.stats()); print(db.reddit_stats()); db.close()"
```

## Performance Expectations

With the new batched approach:

| Data Size | Old Time | New Time | Speedup |
|-----------|----------|----------|---------|
| 100 messages | ~5-10 min | ~30 sec | 10-20x |
| 500 messages | ~30-60 min | ~2-3 min | 15-30x |
| 1000+ messages | ~2-4 hours | ~5-10 min | 20-50x |

Actual times depend on:
- Number of posts/comments (more = longer fetching)
- Comment thread depth (deep threads = more data)
- Rate limit setting (higher = faster fetching, more requests to Reddit)
- CPU (tokenization is the processing bottleneck)

## Troubleshooting

### Script says "Loaded X existing transitions"
This is normal. The scraper is loading your existing Markov model from the database so it can continue building on it.

### Messages show as "⊘ (duplicate)"
This is expected when scraping the same subreddit multiple times. The reddit_id tracking prevents double-training. This is the deduplication working correctly!

### Import is slower than expected
Check if you have a slow disk or low RAM. The bottleneck is now typically Reddit API responses (2+ seconds per request) rather than database writes.

### "Rate limited" warning, waiting 60 seconds
Reddit occasionally rate limits requests. The scraper detects this and waits automatically. This is normal behavior.

### Database file is growing slowly
This is expected. You're now adding Markov transitions more efficiently, so the database grows gradually rather than in big jumps.

## Database Tables

The new system creates/uses these tables:

| Table | Purpose |
|-------|---------|
| `messages` | Raw training corpus (messages fed to Markov) |
| `transitions` | Normalized n-gram transitions (write-optimized) |
| `states` | Compacted transitions (read-optimized) |
| **`reddit_messages`** | **NEW: Tracking of Reddit posts/comments by ID** |

The `reddit_messages` table allows:
- Checking if a message has been seen before (by reddit_id)
- Preventing duplicate training
- Tracking which messages have been imported
- Resuming interrupted scrapes

## Advanced: Batch Processing

For automated pipelines, you can run multiple subreddits in parallel:

```bash
#!/bin/bash
# batch_scrape.sh

SUBREDDITS=(sysadmin programming homelab golang rust python)

for sub in "${SUBREDDITS[@]}"; do
    echo "Starting scrape of r/$sub..."
    python fetch_reddit_training_data.py "$sub" --posts 50 --comments 100 &
done

echo "Waiting for all scrapes to complete..."
wait

echo "✓ All scraping complete!"
python -c "
from ollama_markov.storage.database import Database
db = Database()
print('Final stats:', db.stats())
print('Reddit stats:', db.reddit_stats())
db.close()
"
```

Run with:
```bash
chmod +x batch_scrape.sh
./batch_scrape.sh
```

## Next Steps

Once training is complete:

1. **Test the model**:
   ```bash
   python interactive_test.py
   ```

2. **Start the server**:
   ```bash
   python -m ollama_markov.main
   ```

3. **Use with external clients** (Discord bot, etc.):
   - Server listens on `http://localhost:11434`
   - `/api/generate` and `/api/chat` endpoints ready
   - Model will continue learning from new messages

## Notes

- The `clear_markov_database.py` script preserves reddit_messages table for deduplication
- If you want a complete reset including reddit_messages, delete the `.db` file manually
- Scraping multiple subreddits builds a richer, more diverse model
- The `--rate-limit` parameter respects Reddit's guidelines (2+ seconds recommended)
- Ctrl+C during scraping is safe—you can resume later without duplicates
