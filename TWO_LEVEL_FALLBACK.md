# Two-Level Fallback Mechanism for Error Correction

## Overview

PPIPilot now implements a sophisticated two-level fallback mechanism for correcting JSON translation errors during PPI execution. This system provides a more robust error recovery process by attempting different correction strategies in sequence.

## Architecture

### Level 1: Re-translation (Primary Fallback)
When a PPI fails during execution, the system first attempts to **re-translate** the problematic PPI from scratch using specialized prompts that:
- Receive the PPI name and error details
- Provide instructions on how to properly translate the PPI
- Focus on creating a simple, valid JSON structure
- Learn from the previous error to avoid repeating it

**Location:** `3_prompt_retranslation/`
- `prompt_retranslation_time.txt` - For time-based PPIs
- `prompt_retranslation_occurrency.txt` - For count/occurrence PPIs

### Level 2: Error Correction (Secondary Fallback)
If Level 1 fails to produce a valid PPI, the system falls back to the **error correction** approach, which:
- Analyzes the original JSON structure
- Identifies specific errors in the translation
- Applies targeted fixes while preserving the original intent
- Removes problematic parameters rather than attempting complex fixes

**Location:** `3_prompt_json_correction/prompt_error_correction.txt`

## Workflow

```
┌─────────────────────────────────────┐
│  PPI Execution Detects Errors       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  PHASE 1: LEVEL 1 ITERATIONS        │
│  (Up to MAX_LEVEL1_ITERATIONS)      │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │  Iteration 1 │
        │  Re-translate│
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │  Re-execute  │
        │  Check errors│
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │ Still errors?│
        └──────┬───────┘
               │
        Yes ───┼─── No ──────────────┐
               │                     │
        ┌──────▼───────┐             │
        │  Iteration 2 │             │
        │  Re-translate│             │
        └──────┬───────┘             │
               │                     │
        ┌──────▼───────┐             │
        │  Re-execute  │             │
        │  Check errors│             │
        └──────┬───────┘             │
               │                     │
        ┌──────▼───────┐             │
        │ Still errors?│             │
        └──────┬───────┘             │
               │                     │
        Yes ───┘                     │
               │                     │
               ▼                     │
┌─────────────────────────────────┐  │
│  PHASE 2: LEVEL 2 ITERATIONS    │  │
│  (Up to MAX_LEVEL2_ITERATIONS)  │  │
└──────────────┬──────────────────┘  │
               │                     │
               ▼                     │
        ┌──────────────┐             │
        │  Iteration 1 │             │
        │  Error Fix   │             │
        └──────┬───────┘             │
               │                     │
        ┌──────▼───────┐             │
        │  Re-execute  │             │
        │  Check errors│             │
        └──────┬───────┘             │
               │                     │
        ┌──────▼───────┐             │
        │ Still errors?│             │
        └──────┬───────┘             │
               │                     │
        Yes ───┼─── No ──────────────┤
               │                     │
        ┌──────▼───────┐             │
        │  Iteration 2 │             │
        │  Error Fix   │             │
        └──────┬───────┘             │
               │                     │
        ┌──────▼───────┐             │
        │  Re-execute  │             │
        │  Check errors│             │
        └──────┬───────┘             │
               │                     │
        Yes ───┼─── No ──────────────┤
               │                     │
               ▼                     ▼
        ┌──────────────────────────────┐
        │  Return Results (with or     │
        │  without remaining errors)   │
        └──────────────────────────────┘
```

## Implementation Details

### Key Functions

#### `retranslate_ppi(ppi_name, error_info, activities, attributes, ppi_category, client)`
Re-translates a single PPI that caused errors.

**Parameters:**
- `ppi_name`: Name of the PPI to re-translate
- `error_info`: Dictionary containing error type and message
- `activities`: List of available activities in the log
- `attributes`: List of available attributes in the log
- `ppi_category`: Category ('time' or 'occurrency')
- `client`: OpenAI client instance

**Returns:** Re-translated PPI as dictionary, or None if failed

#### `correct_json_errors(original_json, errors_list, activities, attributes, client, use_retranslation=False)`
Corrects JSON errors using either re-translation (Level 1) or error correction (Level 2).

**Parameters:**
- `original_json`: Original JSON data with errors
- `errors_list`: List of error dictionaries
- `activities`: Available activities
- `attributes`: Available attributes
- `client`: OpenAI client
- `use_retranslation`: If True, uses Level 1; if False, uses Level 2

**Returns:** Path to corrected JSON file, or None if failed

#### `auto_correct_errors_with_retry(...)`
Main orchestration function that manages the two-level fallback process.

**Process:**
1. Execute PPIs and capture errors
2. If errors exist, attempt Level 1 correction
3. If Level 1 fails, attempt Level 2 correction
4. Re-execute with corrected JSON
5. Repeat up to `max_iterations` times

## Level 1: Re-translation Prompts

### Time-based PPIs (`prompt_retranslation_time.txt`)
**Focus:**
- Uses `begin` and `end` fields
- Aggregation: total, minimum, maximum, average
- NO `metric_condition` field
- NO `percentage` aggregation
- Simple filters or no filters

**Example Output:**
```json
{
    "PPIname": "Average time from Declaration SUBMITTED to APPROVED",
    "PPIjson": {
        "begin": "activity == 'Declaration SUBMITTED by EMPLOYEE'",
        "end": "activity == 'Declaration APPROVED by SUPERVISOR'",
        "aggregation": "average"
    }
}
```

### Count/Occurrence PPIs (`prompt_retranslation_occurrency.txt`)
**Focus:**
- Uses `count` field
- Aggregation: total, minimum, maximum, average, percentage
- `metric_condition` required for percentage
- NO `begin` or `end` fields
- Simple filters or no filters

**Example Output:**
```json
{
    "PPIname": "Percentage of cases with Declaration SUBMITTED",
    "PPIjson": {
        "count": "activity == 'Declaration SUBMITTED by EMPLOYEE'",
        "metric_condition": "> 0",
        "aggregation": "percentage"
    }
}
```

## Level 2: Error Correction Prompt

### Approach
- Analyzes original JSON and specific errors
- Applies general error-fixing rules
- Removes problematic parameters
- Preserves original PPI structure and intent

### Common Fixes
1. **Column not found** → Remove `group_by` or `filter` parameter
2. **Undefined variable** → Remove `filter` parameter
3. **Invalid aggregation** → Replace with "average"
4. **Complex AND/OR filters** → Remove entire `filter` field
5. **metric_condition in time PPIs** → Remove field

## Configuration

### Maximum Iterations - Easily Modifiable

The system now has **separate iteration limits** for Level 1 and Level 2, configurable at the top of `interface_2.py`:

```python
# ============================================================================
# ERROR CORRECTION CONFIGURATION - Easily modifiable parameters
# ============================================================================
MAX_LEVEL1_ITERATIONS = 2  # Maximum iterations for Level 1 (Re-translation)
MAX_LEVEL2_ITERATIONS = 2  # Maximum iterations for Level 2 (Error correction)
# ============================================================================
```

**How it works:**
1. **Level 1 Phase:** The system attempts re-translation up to `MAX_LEVEL1_ITERATIONS` times
2. **Level 2 Phase:** If errors persist after Level 1, the system attempts error correction up to `MAX_LEVEL2_ITERATIONS` times
3. **Final Result:** If errors still exist after both phases, results are returned as-is

### Retry Attempts per Level
Each level has internal retry logic within OpenAI API calls:
- **Level 1 (Re-translation):** 2 OpenAI retry attempts per PPI
- **Level 2 (Error correction):** 2 OpenAI retry attempts for batch correction

## Benefits

### Level 1 Advantages
- **Fresh Start:** Creates new JSON without bias from original errors
- **Simplicity:** Focuses on creating simple, valid structures
- **Context-Aware:** Uses PPI name and error details to guide translation
- **Error Learning:** Explicitly avoids patterns that caused previous errors

### Level 2 Advantages
- **Structure Preservation:** Maintains original PPI intent and complexity
- **Targeted Fixes:** Applies specific corrections to known error patterns
- **Fallback Safety:** Provides a safety net when re-translation fails
- **Batch Processing:** Can fix multiple errors in one pass

### Combined Benefits
- **Higher Success Rate:** Two chances to fix each error
- **Adaptive Strategy:** Different approaches for different error types
- **Graceful Degradation:** Falls back to simpler approach if complex one fails
- **Comprehensive Coverage:** Handles both simple and complex error scenarios

## Usage Example

```python
from fromLogtoPPI_prompt_pipeline_goal import auto_correct_errors_with_retry
import ppinatjson as pp

# Execute PPIs with automatic two-level error correction
batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, iteration_count = auto_correct_errors_with_retry(
    xes_file=xes_file,
    json_path=json_path,
    ppis_type='time',  # or 'occurrency' or 'both'
    activities=activities_list,
    attributes=attributes_list,
    client=openai_client,
    max_iterations=2
)

print(f"Completed after {iteration_count} iteration(s)")
print(f"Remaining errors: {len(errors_captured)}")
```

## Error Flow Example

### Scenario: Invalid group_by column

**Initial Error:**
```
KeyError: 'case:resource'
PPI: "Average time by resource type"
```

**Level 1 Attempt:**
```
🔄 LEVEL 1 FALLBACK: Re-translating PPI 'Average time by resource type'
✅ Successfully re-translated PPI
Result: Simple time PPI without group_by
```

**If Level 1 Failed:**
```
❌ Failed to re-translate PPI
🔧 LEVEL 2 FALLBACK: Using error correction prompt
✅ Removed invalid group_by parameter
Result: Original PPI structure with group_by removed
```

## Monitoring and Logging

The system provides detailed console output:
- `🔄` Re-translation attempts (Level 1)
- `🔧` Error correction attempts (Level 2)
- `✅` Successful corrections
- `❌` Failed attempts
- `⚠️` Warnings and fallback triggers

### Example Console Output

```
======================================================================
ERROR CORRECTION CONFIGURATION:
  - Level 1 (Re-translation) max iterations: 2
  - Level 2 (Error correction) max iterations: 2
======================================================================

============================================================
LEVEL 1 - Iteration 1/2 (Total: 1)
============================================================

⚠️ Found 3 errors in Level 1 iteration 1
🔄 Attempting Level 1 correction (re-translation)...

============================================================
LEVEL 1 FALLBACK: Re-translating problematic PPIs
============================================================

🔄 LEVEL 1 FALLBACK: Re-translating PPI 'Average time by resource'...
✅ Successfully re-translated PPI 'Average time by resource'

✅ Successfully re-translated: 2 PPIs
❌ Failed to re-translate: 1 PPIs

⚠️ 1 PPIs failed re-translation, will trigger Level 2 fallback
✅ JSON corrected with Level 1. Proceeding to next iteration...

============================================================
LEVEL 1 - Iteration 2/2 (Total: 2)
============================================================

⚠️ Found 1 errors in Level 1 iteration 2
🔄 Attempting Level 1 correction (re-translation)...
❌ Level 1 correction failed.

============================================================
Level 1 completed after 2 iterations
============================================================

⚠️ Still have 1 errors after Level 1. Proceeding to Level 2...

============================================================
LEVEL 2 - Iteration 1/2 (Total: 3)
============================================================

⚠️ Found 1 errors in Level 2 iteration 1
🔧 Attempting Level 2 correction (error fixing)...

============================================================
LEVEL 2 FALLBACK: Using error correction prompt
============================================================

✅ JSON corrected with Level 2. Proceeding to next iteration...

============================================================
LEVEL 2 - Iteration 2/2 (Total: 4)
============================================================

✅ No errors found in Level 2 iteration 2. Returning results.
```

## Files Modified

1. **`fromLogtoPPI_prompt_pipeline_goal.py`**
   - Added `retranslate_ppi()` function
   - Modified `correct_json_errors()` to support both levels
   - Updated `auto_correct_errors_with_retry()` to use two-level fallback

2. **New Files Created:**
   - `3_prompt_retranslation/prompt_retranslation_time.txt`
   - `3_prompt_retranslation/prompt_retranslation_occurrency.txt`

3. **Existing Files Used:**
   - `3_prompt_json_correction/prompt_error_correction.txt`

## Future Enhancements

Potential improvements:
- Add Level 3 fallback with even simpler PPI structures
- Implement machine learning to predict which level to use first
- Add caching of successful corrections for similar errors
- Provide user feedback in UI about which level succeeded
- Track success rates of each level for analytics
