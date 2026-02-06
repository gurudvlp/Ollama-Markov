# Data Import Guide

There are multiple ways to import training data into Ollama-Markov. Choose the method that works best for your use case.

## Overview

All import methods:
- ✓ Process text through the text processor (normalization, filtering)
- ✓ Add messages to the raw corpus (for auditing and rebuilding)
- ✓ Train the Markov model with n-grams
- ✓ Store transitions in the database
- ✓ Load existing data to build on previous training

## Method 1: Interactive Input (Easiest)

Add training data one piece at a time interactively:

```bash
python interactive_test.py
# Choose option 1: "Add training text"
# Type or paste your text
# Model updates in real-time
```

**Best for:** Quick testing, small batches, interactive exploration

## Method 2: Batch Import Script (Most Scalable)

Import from files via command line. Supports multiple formats.

### Import from Plain Text (one message per line)

```bash
python -m ollama_markov.scripts.import_training_data data.txt \
    --format text \
    --channel my_channel
```

**File format:**
```
First message here.
Second message here.
Third message here.
```

### Import from JSON

```bash
python -m ollama_markov.scripts.import_training_data data.json \
    --format json \
    --channel discord \
    --user my_user
```

**File format:**
```json
[
  {
    "content": "First message",
    "timestamp": "2024-01-01T12:00:00",
    "user_id": "user123"
  },
  {
    "content": "Second message",
    "timestamp": "2024-01-01T12:01:00"
  }
]
```

Supports `content`, `text`, or `message` field names.

### Import from CSV

```bash
python -m ollama_markov.scripts.import_training_data data.csv \
    --format csv \
    --channel twitter \
    --column text
```

**File format:**
```
user_id,text,timestamp
user123,"First tweet here",2024-01-01
user456,"Second tweet here",2024-01-02
```

**Options:**
- `--column TEXT` - Column name containing messages (default: "content")
- `--user USERID` - User ID for messages (default: "csv_import")

## Method 3: Programmatic Import (Most Control)

Import data directly in Python scripts:

```python
from ollama_markov.config import load_config
from ollama_markov.model.markov import MarkovModel
from ollama_markov.processing.text_processor import TextProcessor
from ollama_markov.storage.database import Database

config = load_config()
db = Database(config["db_path"])
processor = TextProcessor(config)
model = MarkovModel(config["markov_order"])

# Load existing training
model.load_from_database(db)

# Import your data
data = [
    "First training message.",
    "Second training message.",
    "Third training message.",
]

for text in data:
    # Process and filter text
    tokens = processor.preprocess(text)

    if tokens:
        # Store in corpus
        db.add_message("my_user_id", "my_channel", text)

        # Train model
        model.train(tokens)

        # Store transitions
        for state, next_tokens in model.transitions.items():
            for next_token, count in next_tokens.items():
                db.add_transition(model.order, state, next_token, count)

# Check results
stats = db.stats()
print(f"Imported successfully: {stats['message_count']} messages")
print(f"Learned {stats['total_transitions']} transitions")

db.close()
```

## Common Import Tasks

### Import Discord Chat History

If you have Discord chat exported as JSON:

```bash
python -m ollama_markov.scripts.import_training_data discord_export.json \
    --format json \
    --channel discord \
    --user discord_bot
```

### Import Twitter Posts

Export tweets to CSV (using a tool like twidownloader):

```bash
python -m ollama_markov.scripts.import_training_data tweets.csv \
    --format csv \
    --channel twitter \
    --column text
```

### Import Book or Article Text

Plain text file (one message per line or per paragraph):

```bash
python -m ollama_markov.scripts.import_training_data book.txt \
    --format text \
    --channel literature
```

### Combine Multiple Sources

```bash
# Import from first source
python -m ollama_markov.scripts.import_training_data source1.txt \
    --format text --channel source1

# Import from second source (model keeps learning)
python -m ollama_markov.scripts.import_training_data source2.csv \
    --format csv --channel source2 --column content

# Add more from interactive
python interactive_test.py
# Option 1 to add more
```

## Data Processing

All imports go through the text processor which:

### Filters Out:
- ✗ Code blocks (detected by: ```, indentation, `Traceback`, `Error:`)
- ✗ Messages below minimum length (default: 3 tokens)
- ✗ Duplicate messages

### Normalizes:
- URLs → `<URL>`
- Emails → `<EMAIL>`
- Phone numbers → `<PHONE>`
- User mentions → `<USER>`
- Preserved: Punctuation, contractions, special characters

### Stored:
- ✓ Raw corpus (original text) - for auditing and rebuilding
- ✓ Transitions (n-gram counts) - for generation

## Command Reference

```bash
python -m ollama_markov.scripts.import_training_data FILE \
    --format {text,json,csv} \
    --channel CHANNEL_ID \
    [--user USER_ID] \
    [--column COLUMN_NAME] \
    [--db DATABASE_PATH] \
    [--order N-GRAM_ORDER]
```

**Arguments:**
- `FILE` - Path to data file (required)
- `--format` - File format: text, json, or csv (required)
- `--channel` - Channel identifier for tracking (required)
- `--user` - User ID for messages (default: "seed")
- `--column` - CSV column name (default: "content")
- `--db` - Database path (default: "ollama_markov.db")
- `--order` - Markov order (default: 2)

## Best Practices

### 1. Start with Interactive Testing
```bash
# Test with small sample first
python interactive_test.py
# Option 1: Add a few test messages
# Option 2: Generate to check quality
```

### 2. Import in Stages
```bash
# Stage 1: Bootstrap with example data
python -m ollama_markov.scripts.import_training_data bootstrap.txt \
    --format text --channel bootstrap

# Stage 2: Check results
python interactive_test.py
# Option 3: View stats

# Stage 3: Import more data
python -m ollama_markov.scripts.import_training_data full_dataset.csv \
    --format csv --channel main
```

### 3. Monitor Quality
```bash
# After each import, check stats
python interactive_test.py
# Option 3: Show stats
# Option 2: Try generating

# If quality is low:
#   - Import more data
#   - Check if data is being filtered out
#   - Try higher Markov order
```

### 4. Corpus Size Recommendations
- Order 2: 20k-100k words for quality
- Order 3: 100k-500k words for good coherence
- Order 4+: 500k+ words

## Troubleshooting

### "No messages imported"
**Issue:** All messages filtered out

**Solutions:**
- Check message length (minimum 3 tokens by default)
- Check for code blocks or special formatting
- Verify text is actual sentences, not codes/URLs

### Low generation quality
**Issue:** Generated text is repetitive or incoherent

**Solutions:**
- Import more data (more = better quality)
- Try order-3: `--order 3`
- Diversify data sources

### "Column not found" in CSV
**Issue:** CSV column name doesn't match

**Solutions:**
- Check CSV headers: `head -1 data.csv`
- Use correct column name: `--column actual_name`
- Or convert to different format

## Examples

See `examples_training_data.txt` for a sample dataset you can try:

```bash
python -m ollama_markov.scripts.import_training_data examples_training_data.txt \
    --format text --channel examples
```

Then test generation:
```bash
python interactive_test.py
# Option 2: Generate text
# Option 3: View updated stats
```
