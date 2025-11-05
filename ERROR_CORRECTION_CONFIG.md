# Error Correction Configuration Guide

## Quick Configuration

To modify the error correction behavior, edit the following parameters at the top of `interface_2.py`:

```python
# ============================================================================
# ERROR CORRECTION CONFIGURATION - Easily modifiable parameters
# ============================================================================
MAX_LEVEL1_ITERATIONS = 2  # Maximum iterations for Level 1 (Re-translation)
MAX_LEVEL2_ITERATIONS = 2  # Maximum iterations for Level 2 (Error correction)
# ============================================================================
```

## Parameters Explained

### `MAX_LEVEL1_ITERATIONS`
**Default:** `2`

**Description:** Maximum number of times the system will attempt to re-translate problematic PPIs using the specialized re-translation prompts.

**What it does:**
- Each iteration re-translates all PPIs that caused errors
- Creates fresh JSON structures from scratch
- Learns from previous error messages
- Focuses on simplicity and validity

**When to increase:**
- If you notice many PPIs fail re-translation on first attempt
- If your log has complex activity names that need multiple attempts
- If you want to give more chances for the AI to understand the PPI intent

**When to decrease:**
- If re-translation is taking too long
- If Level 1 rarely succeeds and you want to move to Level 2 faster
- To reduce OpenAI API costs

**Recommended range:** 1-3

---

### `MAX_LEVEL2_ITERATIONS`
**Default:** `2`

**Description:** Maximum number of times the system will attempt to fix errors in the original JSON using targeted error correction.

**What it does:**
- Each iteration analyzes specific errors in the JSON
- Applies targeted fixes (removes invalid parameters, fixes aggregations, etc.)
- Preserves the original PPI structure and intent
- Uses the comprehensive error correction prompt

**When to increase:**
- If you notice errors persist after Level 2
- If your PPIs have multiple types of errors that need sequential fixing
- If you want more thorough error correction

**When to decrease:**
- If Level 2 corrections are taking too long
- If errors are rarely fixed by Level 2 (might indicate fundamental issues)
- To reduce OpenAI API costs

**Recommended range:** 1-3

---

## Configuration Examples

### Conservative (Fast, Lower Cost)
```python
MAX_LEVEL1_ITERATIONS = 1  # One quick re-translation attempt
MAX_LEVEL2_ITERATIONS = 1  # One error correction attempt
```
**Total max iterations:** 2  
**Best for:** Simple logs, quick testing, cost-sensitive scenarios

---

### Balanced (Default)
```python
MAX_LEVEL1_ITERATIONS = 2  # Two re-translation attempts
MAX_LEVEL2_ITERATIONS = 2  # Two error correction attempts
```
**Total max iterations:** 4  
**Best for:** Most production scenarios, good balance of success rate and speed

---

### Aggressive (Thorough, Higher Cost)
```python
MAX_LEVEL1_ITERATIONS = 3  # Three re-translation attempts
MAX_LEVEL2_ITERATIONS = 3  # Three error correction attempts
```
**Total max iterations:** 6  
**Best for:** Complex logs, critical analyses, when maximum success rate is needed

---

### Level 1 Focused
```python
MAX_LEVEL1_ITERATIONS = 3  # More re-translation attempts
MAX_LEVEL2_ITERATIONS = 1  # Minimal error correction
```
**Total max iterations:** 4  
**Best for:** When re-translation works well, when you prefer fresh translations

---

### Level 2 Focused
```python
MAX_LEVEL1_ITERATIONS = 1  # Quick re-translation attempt
MAX_LEVEL2_ITERATIONS = 3  # More error correction attempts
```
**Total max iterations:** 4  
**Best for:** When original PPI structure is good but has specific errors

---

## How Iterations Work

### Phase 1: Level 1 (Re-translation)
```
Iteration 1: Execute → Detect errors → Re-translate → Re-execute
Iteration 2: Execute → Detect errors → Re-translate → Re-execute
...
Iteration N: Execute → Detect errors → Re-translate → Re-execute
```

If errors persist after all Level 1 iterations, proceed to Level 2.

### Phase 2: Level 2 (Error Correction)
```
Iteration 1: Execute → Detect errors → Fix errors → Re-execute
Iteration 2: Execute → Detect errors → Fix errors → Re-execute
...
Iteration N: Execute → Detect errors → Fix errors → Re-execute
```

If errors persist after all Level 2 iterations, return results as-is.

---

## Cost Considerations

Each iteration involves:
- **1 OpenAI API call** per correction attempt (Level 1 or Level 2)
- **Additional retry calls** if the response is malformed (up to 2 retries per call)

### Example Cost Calculation (with 3 error PPIs):

**Conservative (1+1):**
- Level 1: 1 iteration × 3 PPIs = 3 API calls
- Level 2: 1 iteration × 1 batch = 1 API call
- **Total: ~4 API calls**

**Balanced (2+2):**
- Level 1: 2 iterations × 3 PPIs = 6 API calls
- Level 2: 2 iterations × 1 batch = 2 API calls
- **Total: ~8 API calls**

**Aggressive (3+3):**
- Level 1: 3 iterations × 3 PPIs = 9 API calls
- Level 2: 3 iterations × 1 batch = 3 API calls
- **Total: ~12 API calls**

*Note: Actual calls may be lower if errors are resolved before reaching max iterations.*

---

## Performance Considerations

### Execution Time

Each iteration includes:
1. **OpenAI API call:** 2-10 seconds (depends on response size)
2. **JSON parsing and validation:** <1 second
3. **PPI re-execution:** 1-5 seconds (depends on log size)

**Estimated total time per iteration:** 5-15 seconds

**Example total times:**
- Conservative (1+1): 10-30 seconds
- Balanced (2+2): 20-60 seconds
- Aggressive (3+3): 30-90 seconds

---

## Monitoring Success Rates

After running analyses, check the console output for:

```
✅ No errors found in Level 1 iteration X
```
→ Level 1 succeeded early, consider keeping current settings

```
⚠️ Still have X errors after Level 1. Proceeding to Level 2...
```
→ Level 1 didn't fully succeed, Level 2 is needed

```
✅ All errors resolved after Level 2
```
→ Level 2 succeeded, settings are working well

```
⚠️ X errors remain after all correction attempts
```
→ Consider increasing iterations or investigating error types

---

## Troubleshooting

### Too Many Remaining Errors
**Problem:** Errors persist even after max iterations  
**Solutions:**
- Increase `MAX_LEVEL1_ITERATIONS` and/or `MAX_LEVEL2_ITERATIONS`
- Check if errors are due to fundamental log issues (missing activities, etc.)
- Review error messages to identify patterns

### Taking Too Long
**Problem:** Error correction is too slow  
**Solutions:**
- Decrease `MAX_LEVEL1_ITERATIONS` and/or `MAX_LEVEL2_ITERATIONS`
- Use Conservative configuration (1+1)
- Check if log file is very large

### High API Costs
**Problem:** Too many OpenAI API calls  
**Solutions:**
- Use Conservative configuration (1+1)
- Reduce number of PPIs generated initially
- Improve initial PPI generation to reduce errors

---

## Best Practices

1. **Start with defaults (2+2)** and adjust based on results
2. **Monitor console output** to understand where errors are resolved
3. **Track success rates** over multiple analyses
4. **Adjust gradually** - change by 1 iteration at a time
5. **Consider your use case** - critical analyses warrant higher iterations
6. **Balance cost vs. accuracy** based on your requirements

---

## Quick Reference

| Scenario | Level 1 | Level 2 | Total | Use Case |
|----------|---------|---------|-------|----------|
| Fast & Cheap | 1 | 1 | 2 | Testing, simple logs |
| **Balanced (Default)** | **2** | **2** | **4** | **Production** |
| Thorough | 3 | 3 | 6 | Complex logs, critical |
| Re-translation focus | 3 | 1 | 4 | Fresh translations preferred |
| Error fixing focus | 1 | 3 | 4 | Original structure is good |

---

## Need Help?

If you're unsure which configuration to use:
1. Start with **Balanced (2+2)**
2. Run a few analyses
3. Check the console output
4. Adjust based on your success rate and performance needs

For more details, see `TWO_LEVEL_FALLBACK.md`
