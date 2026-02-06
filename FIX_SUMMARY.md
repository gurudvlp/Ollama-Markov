# Fix: Loading Trained Model Data in Interactive Test

## Problem

When running `interactive_test.py` after training with `test_markov.py`, the model would say "No training data yet" even though the database showed:
- 10 messages stored
- 92 transitions saved
- 523 total transition counts

## Root Cause

The issue was a disconnect between where data is **stored** and where it's **loaded**:

1. `test_markov.py` **trained** the model and **stored transitions in the database**
2. `interactive_test.py` created a **fresh, empty MarkovModel**
3. The new model had no idea about the stored transitions
4. When checking `if not model.transitions:`, it returned True (empty)

### Data Flow Before Fix

```
test_markov.py:
  Train → Store in DB → Discard model

interactive_test.py:
  Create empty model → Can't generate → Error!
```

## Solution

Added methods to **load transitions from the database into the model**:

### 1. `MarkovModel.load_from_database(db)`
- New method to populate in-memory transitions from database
- Filters by n-gram order to match current model
- Returns count of transitions loaded

### 2. `Database.get_all_transitions()`
- New method to retrieve all transitions from DB
- Returns list of (order_n, state_text, next_token, count) tuples

### 3. Updated `interactive_test.py`
- Automatically loads transitions on startup
- Shows user how many transitions were loaded
- Now generation works immediately after training

## New Data Flow

```
test_markov.py:
  Train → Store in DB

interactive_test.py:
  Create empty model → Load from DB → Ready to generate!
```

## Testing

Before fix:
```
$ python interactive_test.py
✗ "No training data yet"
```

After fix:
```
$ python interactive_test.py
✓ Loaded 92 transitions from database
$ [Choose option 2 to generate]
✓ Generated: "lazy dog."
```

## Code Changes

**ollama_markov/model/markov.py:**
- Added `load_from_database(db)` method

**ollama_markov/storage/database.py:**
- Added `get_all_transitions()` method

**interactive_test.py:**
- Call `model.load_from_database(db)` on startup
- Display feedback on transitions loaded

## Now Works As Expected

✓ Train with `test_markov.py`
✓ Run `interactive_test.py`
✓ Automatically loads previous training
✓ Can immediately generate text
✓ Can add more training data incrementally
✓ Database persists between runs
