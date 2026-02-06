# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test
```bash
python test_markov.py
```

You should see:
- ✓ 10 training samples processed
- ✓ Database created with transitions
- ✓ Text generation examples

### 3. Try Interactive Mode
```bash
python interactive_test.py
```

Menu options:
- Add training text manually
- Generate text with different temperatures
- View database stats
- Clear and reset

## What's Implemented Now ✓

### Core Markov Model
- **Training**: Feed text → model learns word transitions
- **Generation**: Start from seed state → generate coherent text
- **Temperature control**: 0 (deterministic) to 2+ (random)
- **Persistence**: Save/load model from disk

### Text Processing
- **Tokenization**: Word-level with punctuation
- **Normalization**: Replace URLs, emails, mentions
- **Filtering**: Skip code blocks, short text, duplicates

### Storage
- **SQLite database**: Raw messages + transitions
- **Compaction**: Merge transitions for faster reads
- **Statistics**: Query corpus size and transition counts

## Example Usage

### Add Training Data
```python
from ollama_markov.model.markov import MarkovModel
from ollama_markov.model.tokenizer import Tokenizer
from ollama_markov.processing.text_processor import TextProcessor

tokenizer = Tokenizer()
processor = TextProcessor({"min_message_length": 3})
model = MarkovModel(order=2)

# Train on text
text = "The quick brown fox jumps over the lazy dog."
tokens = processor.preprocess(text)
model.train(tokens)

# Generate text
output = model.generate(seed_state="the", max_tokens=20, temperature=1.0)
print(tokenizer.detokenize(output.split()))
```

### Generate from Different Seeds
```python
# Deterministic (temperature=0)
output = model.generate("the", max_tokens=15, temperature=0.5)

# Random (temperature=1.5)
output = model.generate("python", max_tokens=15, temperature=1.5)

# Top-K sampling (restrict to top 5 tokens)
output = model.generate("the", max_tokens=15, top_k=5)
```

## Database Structure

```
ollama_markov.db (SQLite)
├── messages          (raw corpus, for auditing/rebuilding)
├── transitions       (write-optimized: state → next_token → count)
└── states           (read-optimized: compacted probability distributions)
```

## Common Tasks

### View Database Stats
```bash
python interactive_test.py
# Choose option 3: Show stats
```

### Clear Database and Start Fresh
```bash
python interactive_test.py
# Choose option 4: Clear database
```

### Train on a File
```python
# In interactive_test.py, the "Add training text" option
# Or modify test_markov.py to load from a file:

with open("mytext.txt") as f:
    for line in f:
        train_from_text(model, db, processor, line)
```

## Configuration (.env)

```
# Optional - defaults shown
MODE=training
OLLAMA_PORT=11434
MARKOV_ORDER=2
MAX_TOKENS=500
TEMPERATURE=0.8
MIN_MESSAGE_LENGTH=3
LOG_LEVEL=INFO
DB_PATH=ollama_markov.db
```

## Next Steps

1. **Add more training data** — The model improves with more text
2. **Experiment with order-3** — Set `MARKOV_ORDER=3` in .env for more coherent output
3. **Implement API** — Next phase is the HTTP endpoints (see IMPLEMENTATION_STATUS.md)
4. **Add safety filters** — Customize output filtering for your use case

## Troubleshooting

**"seed state not found"**
- The exact state may not exist in the model
- Try shorter seeds or leave it empty for random generation

**"No generation - seed state not in model"**
- Not enough training data yet
- Add more sentences to build richer transitions

**"Text did not pass preprocessing filters"**
- Text is too short (< MIN_MESSAGE_LENGTH)
- Or detected as code block
- Check processing/text_processor.py for rules

## File Structure

```
ollama_markov/
├── model/           ← Markov chain logic (DONE)
├── storage/         ← SQLite interface (DONE)
├── processing/      ← Text filters (DONE)
├── api/             ← HTTP endpoints (TODO)
└── scripts/         ← Import tools (TODO)

test_markov.py      ← Automated test
interactive_test.py ← Interactive testing
```

## Performance Notes

- **Model order 2**: ~20k words for basic quality, 100k+ for good quality
- **Order 3**: ~100k words minimum, 500k+ recommended
- **Database compaction**: Run every 1000 writes for optimal performance
- **Generation speed**: ~milliseconds per token on modern hardware

## What's Working Now

✓ Training from text
✓ Generating coherent text
✓ Temperature-based sampling
✓ Top-K token restriction
✓ Text normalization
✓ Message filtering
✓ SQLite persistence
✓ Database compaction
✓ Basic statistics

## What's Coming Next

→ HTTP API endpoints (/api/generate, /api/chat)
→ Safety output filters
→ Batch import tools
→ Database management utilities

For more details, see:
- [design-spec.md](design-spec.md) — Full technical design
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) — What's done/TODO
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — Architecture details
