# Prompt Logging Quick Start Guide

## 🎯 What is This?

A debug feature that saves all prompts sent to OpenAI and their responses during error correction. Perfect for testing and debugging!

## ⚡ Quick Setup

### 1. Enable Logging

Open `interface_2.py` and find this section at the top:

```python
# DEBUG/TESTING FLAGS
SAVE_PROMPTS_AND_RESPONSES = True   # ← Set to True to enable
PROMPTS_LOG_FOLDER = "debug_prompts_log"
```

### 2. Run Your Analysis

Run your PPI analysis as normal. When errors occur and the fallback mechanism activates, logs will be saved automatically.

### 3. Check the Logs

Look in the `debug_prompts_log` folder. You'll find files like:

```
20241105_113045_123456_level1_Average_time_by_resource_iter1.txt
20241105_113050_789012_level2_iter1.txt
```

### 4. Review the Content

Open any file to see:
- The exact prompt sent to OpenAI
- The full response received
- Metadata (timestamp, level, PPI name, iteration)

See `EXAMPLE_DEBUG_LOG.txt` for a sample log file.

## 🔴 Important: Disable Before Production!

**Before deploying or sharing your code:**

```python
SAVE_PROMPTS_AND_RESPONSES = False  # ← Set to False!
```

## 📚 Full Documentation

- **Detailed guide:** `DEBUG_PROMPTS_LOGGING.md`
- **Configuration options:** `ERROR_CORRECTION_CONFIG.md`
- **Example log file:** `EXAMPLE_DEBUG_LOG.txt`

## 🚀 Common Use Cases

### Debug a Failing PPI
1. Enable logging
2. Run analysis
3. Find the Level 1 file for the failing PPI
4. Check if prompt is correct and response is valid

### Compare Iterations
1. Set `MAX_LEVEL1_ITERATIONS = 3`
2. Enable logging
3. Run analysis
4. Compare `iter1.txt`, `iter2.txt`, `iter3.txt` files

### Analyze Error Corrections
1. Enable logging
2. Let analysis reach Level 2
3. Open Level 2 files
4. See how OpenAI corrects the JSON

## 📁 File Structure

```
debug_prompts_log/
├── 20241105_113045_123456_level1_PPI_Name_iter1.txt
├── 20241105_113045_234567_level1_PPI_Name_iter2.txt
├── 20241105_113050_789012_level2_iter1.txt
└── 20241105_113050_890123_level2_iter2.txt
```

## 🧹 Cleanup

Delete the folder when done:

```bash
# Windows
rmdir /s debug_prompts_log

# Linux/Mac
rm -rf debug_prompts_log
```

## ⚠️ Remember

- ✅ Use for testing and debugging
- ✅ Review logs after each test
- ✅ Delete logs regularly
- ❌ Don't leave enabled in production
- ❌ Don't commit logs to git (already in `.gitignore`)
- ❌ Don't share logs with sensitive data

---

**That's it! Happy debugging! 🐛🔍**
