# Level 1 Batch Re-translation

## Overview

Level 1 now uses **batch re-translation** instead of individual re-translation for each PPI with errors. This means a single OpenAI API call handles all problematic PPIs at once.

## How It Works

### Before (Individual Re-translation)
```
3 PPIs with errors → 3 separate OpenAI API calls
- Call 1: Re-translate "Average time by resource"
- Call 2: Re-translate "Count of rejected declarations"
- Call 3: Re-translate "Maximum processing time"
```

### Now (Batch Re-translation)
```
3 PPIs with errors → 1 OpenAI API call
- Single call: Re-translate all 3 PPIs together
  • "Average time by resource"
  • "Count of rejected declarations"
  • "Maximum processing time"
```

## Benefits

### 1. **Faster Execution**
- **Before:** 3 PPIs = ~15-30 seconds (3 API calls × 5-10 sec each)
- **Now:** 3 PPIs = ~5-10 seconds (1 API call)

### 2. **Lower Cost**
- **Before:** 3 PPIs = 3 API calls = 3× cost
- **Now:** 3 PPIs = 1 API call = 1× cost

### 3. **Better Context**
- OpenAI sees all PPIs together
- Can maintain consistency across translations
- Better understanding of the overall task

### 4. **Simpler Logging**
- Single log file per batch instead of multiple files
- Easier to review and debug

## Technical Details

### Function: `retranslate_ppis_batch()`

**Input:**
```python
ppi_names_with_errors = [
    ("Average time by resource", error_info_1),
    ("Count of rejected declarations", error_info_2),
    ("Maximum processing time", error_info_3)
]
```

**Prompt Format:**
```
You need to re-translate the following 3 PPIs that caused errors:

- Average time by resource (Error: KeyError: 'case:resource')
- Count of rejected declarations (Error: NameError: name 'rejected' is not defined)
- Maximum processing time (Error: KeyError: 'case:amount')

AVAILABLE ACTIVITIES IN THE LOG:
Declaration SUBMITTED by EMPLOYEE, Declaration APPROVED by ADMINISTRATION, ...

AVAILABLE ATTRIBUTES IN THE LOG:
case:concept:name, case:amount, time:timestamp, ...

Please return a JSON array with ALL 3 re-translated PPIs...
```

**Output:**
```json
[
  {
    "PPIname": "Average time by resource",
    "PPIjson": { ... }
  },
  {
    "PPIname": "Count of rejected declarations",
    "PPIjson": { ... }
  },
  {
    "PPIname": "Maximum processing time",
    "PPIjson": { ... }
  }
]
```

### Validation

The system validates that:
1. ✅ Response is a valid JSON array
2. ✅ Each PPI has `PPIname` and `PPIjson` fields
3. ✅ All expected PPIs are present in the response

If validation fails:
- ❌ Retry with clearer instructions (up to 2 attempts)
- ❌ If all retries fail → trigger Level 2 fallback

## Debug Logging

When `SAVE_PROMPTS_AND_RESPONSES = True`, batch re-translations are saved with the prefix `level1_batch`:

```
debug_prompts_log/
└── 20241105_124500_123456_level1_batch_iter1.txt
```

**File content includes:**
- Full prompt with all PPI names and errors
- Complete OpenAI response with all re-translated PPIs
- Metadata (timestamp, iteration)

## Example Console Output

```
============================================================
LEVEL 1 FALLBACK: Re-translating problematic PPIs
============================================================

Re-translating 3 problematic PPIs in batch
Keeping 8 working PPIs unchanged

🔄 LEVEL 1 FALLBACK: Re-translating 3 PPIs in batch using specialized prompt...
Sending batch re-translation request to OpenAI for 3 PPIs...
Batch re-translation attempt 1 - response length: 1234
📝 Saved prompt and response to: debug_prompts_log/20241105_124500_123456_level1_batch_iter1.txt
✅ Successfully re-translated 3 PPIs in batch

✅ Successfully re-translated: 3 PPIs in batch
✅ Re-translated JSON saved with 11 total PPIs
```

## Error Handling

### Missing PPIs in Response

If OpenAI doesn't return all requested PPIs:

```
⚠️ 1 PPIs missing from batch response: {'Maximum processing time'}
Will trigger Level 2 fallback for missing PPIs
```

### Invalid Response Format

If OpenAI returns malformed JSON:

```
❌ Failed to parse batch re-translated JSON on attempt 1: Expecting value: line 1 column 1 (char 0)
IMPORTANT: Your previous response was not valid JSON. Please return ONLY a valid JSON array...
```

### Complete Failure

If all retry attempts fail:

```
❌ Failed to re-translate PPIs in batch after 2 attempts
❌ Batch re-translation failed, will trigger Level 2 fallback
```

## Comparison: Individual vs Batch

| Aspect | Individual | Batch |
|--------|-----------|-------|
| **API Calls** | N calls (N = # of errors) | 1 call |
| **Time** | ~5-10 sec × N | ~5-10 sec |
| **Cost** | N × base cost | 1 × base cost |
| **Log Files** | N files | 1 file |
| **Context** | Isolated per PPI | All PPIs together |
| **Consistency** | May vary | More consistent |
| **Debugging** | Multiple files to check | Single file to check |

## Performance Impact

### Example: 5 PPIs with Errors

**Individual Re-translation:**
- API calls: 5
- Time: ~25-50 seconds
- Cost: 5× base
- Log files: 5

**Batch Re-translation:**
- API calls: 1
- Time: ~5-10 seconds
- Cost: 1× base
- Log files: 1

**Improvement:**
- ⚡ **5× faster**
- 💰 **5× cheaper**
- 📁 **5× fewer log files**

## Backward Compatibility

The old `retranslate_ppi()` function is still available but no longer used by default. It's kept for:
- Backward compatibility
- Potential future use cases
- Reference implementation

## Future Enhancements

Potential improvements:
1. **Adaptive batching:** Split very large batches into smaller chunks
2. **Partial success handling:** Accept partial results if some PPIs are valid
3. **Batch-specific prompts:** Create optimized prompts for batch re-translation
4. **Parallel batching:** Process multiple batches in parallel for very large error sets

---

**Summary:** Level 1 now processes all errors in a single batch, making it faster, cheaper, and easier to debug! 🚀
