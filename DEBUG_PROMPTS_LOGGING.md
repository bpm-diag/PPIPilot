# Debug Prompts Logging

## Overview

This feature allows you to save all prompts sent to OpenAI and their responses during the error correction fallback mechanism. This is useful for:
- **Debugging:** Understanding what prompts are being sent and what responses are received
- **Testing:** Analyzing the quality of prompts and responses
- **Optimization:** Improving prompt templates based on actual usage
- **Documentation:** Creating examples of prompt/response pairs

## ⚠️ Important Note

**This is a TESTING/DEBUG feature only.** It should be **disabled in production** to:
- Avoid filling up disk space with log files
- Protect sensitive data in prompts/responses
- Improve performance (no file I/O overhead)

## Configuration

### Enable/Disable Logging

Edit the configuration at the top of `interface_2.py`:

```python
# DEBUG/TESTING FLAGS
SAVE_PROMPTS_AND_RESPONSES = True   # Set to False to disable logging
PROMPTS_LOG_FOLDER = "debug_prompts_log"  # Folder where logs are saved
```

### Quick Toggle

**To Enable (for testing):**
```python
SAVE_PROMPTS_AND_RESPONSES = True
```

**To Disable (for production):**
```python
SAVE_PROMPTS_AND_RESPONSES = False
```

## How It Works

When `SAVE_PROMPTS_AND_RESPONSES = True`:

1. **Folder Creation:** A folder named `debug_prompts_log` is automatically created in the project root
2. **File Generation:** Each OpenAI API call generates a separate `.txt` file
3. **Naming Convention:** Files are named with timestamp, level, PPI name, and iteration number
4. **Content:** Each file contains the full prompt and the full response

### File Naming Format

**Level 1 (Re-translation):**
```
20241105_113045_123456_level1_Average_time_by_resource_iter1.txt
```

**Level 2 (Error correction):**
```
20241105_113050_789012_level2_iter1.txt
```

**Format breakdown:**
- `20241105_113045_123456` - Timestamp (YYYYMMDD_HHMMSS_microseconds)
- `level1` or `level2` - Fallback level
- `Average_time_by_resource` - PPI name (Level 1 only, sanitized for filename)
- `iter1` - Iteration number
- `.txt` - Text file extension

## File Content Structure

Each log file contains:

```
================================================================================
TIMESTAMP: 2024-11-05 11:30:45
LEVEL: LEVEL1
PPI NAME: Average time by resource
ITERATION: 1
================================================================================

================================================================================
PROMPT SENT TO OPENAI:
================================================================================
[Full prompt text here, including template and all substitutions]

================================================================================
RESPONSE FROM OPENAI:
================================================================================
[Full response from OpenAI, including any JSON or text]
```

## Usage Examples

### Example 1: Debug a Failing Re-translation

1. Enable logging:
   ```python
   SAVE_PROMPTS_AND_RESPONSES = True
   ```

2. Run your analysis with errors

3. Check the `debug_prompts_log` folder

4. Open the Level 1 file for the failing PPI:
   ```
   20241105_113045_123456_level1_Failing_PPI_Name_iter1.txt
   ```

5. Review:
   - Is the prompt formatted correctly?
   - Are the activities and attributes correct?
   - Is the error message clear?
   - Is the OpenAI response valid JSON?

### Example 2: Compare Iterations

1. Enable logging

2. Run analysis with `MAX_LEVEL1_ITERATIONS = 3`

3. Check the folder for multiple iteration files:
   ```
   20241105_113045_123456_level1_PPI_Name_iter1.txt
   20241105_113045_234567_level1_PPI_Name_iter2.txt
   20241105_113045_345678_level1_PPI_Name_iter3.txt
   ```

4. Compare how the prompt changes between iterations (especially retry attempts)

### Example 3: Analyze Level 2 Corrections

1. Enable logging

2. Run analysis that triggers Level 2

3. Open Level 2 files:
   ```
   20241105_113050_789012_level2_iter1.txt
   ```

4. Review:
   - How many PPIs are being corrected in the batch?
   - What errors are being reported?
   - How does OpenAI correct the JSON?

## Best Practices

### During Testing

✅ **DO:**
- Enable logging when debugging specific issues
- Review logs after each test run
- Delete old logs regularly to save space
- Use logs to improve prompt templates

❌ **DON'T:**
- Leave logging enabled for long periods
- Commit log files to version control (they're in `.gitignore`)
- Share logs that contain sensitive data

### Before Production

✅ **MUST DO:**
- Set `SAVE_PROMPTS_AND_RESPONSES = False`
- Delete or archive all log files
- Verify the folder is in `.gitignore`

## Disk Space Considerations

### File Sizes

Typical file sizes:
- **Level 1 (single PPI):** 2-10 KB per file
- **Level 2 (batch correction):** 10-50 KB per file

### Storage Estimates

With default configuration (2 Level 1 + 2 Level 2 iterations):

| Scenario | Files per Run | Approx. Size | 100 Runs |
|----------|---------------|--------------|----------|
| 3 error PPIs | ~12 files | ~150 KB | ~15 MB |
| 10 error PPIs | ~40 files | ~400 KB | ~40 MB |
| 20 error PPIs | ~80 files | ~800 KB | ~80 MB |

**Recommendation:** Clean the folder regularly during testing.

## Cleaning Up Logs

### Manual Cleanup

Simply delete the folder:
```bash
# Windows
rmdir /s debug_prompts_log

# Linux/Mac
rm -rf debug_prompts_log
```

The folder will be recreated automatically on the next run if logging is enabled.

### Automated Cleanup (Optional)

You can add a cleanup function to your code:

```python
import shutil
import os

def cleanup_debug_logs():
    """Remove all debug log files"""
    if os.path.exists(PROMPTS_LOG_FOLDER):
        shutil.rmtree(PROMPTS_LOG_FOLDER)
        print(f"✅ Cleaned up {PROMPTS_LOG_FOLDER}")
```

## Troubleshooting

### Logs Not Being Created

**Problem:** `SAVE_PROMPTS_AND_RESPONSES = True` but no files appear

**Solutions:**
1. Check if the folder exists (it should be created automatically)
2. Check file permissions (ensure write access)
3. Check console for error messages (look for "⚠️ Failed to save prompt/response log")
4. Verify the flag is set before running the analysis

### Too Many Files

**Problem:** Hundreds of log files accumulating

**Solutions:**
1. Delete old logs regularly
2. Reduce `MAX_LEVEL1_ITERATIONS` and `MAX_LEVEL2_ITERATIONS` during testing
3. Disable logging when not actively debugging

### Cannot Open Files

**Problem:** Files are locked or cannot be opened

**Solutions:**
1. Close any text editors that have the files open
2. Ensure no other process is accessing the folder
3. Check file permissions

## Privacy and Security

### Sensitive Data Warning

⚠️ **Log files may contain:**
- Activity names from your process logs
- Attribute names and values
- PPI names and descriptions
- Error messages with data details

### Recommendations

1. **Never commit logs to version control** (already in `.gitignore`)
2. **Don't share logs publicly** without reviewing content
3. **Delete logs** after debugging is complete
4. **Disable logging** in production environments
5. **Encrypt logs** if they must be stored long-term

## Integration with Version Control

The `debug_prompts_log/` folder is already added to `.gitignore`:

```gitignore
# Debug/Testing folders
debug_prompts_log/
```

This ensures log files are never accidentally committed to your repository.

## Summary

| Setting | Development | Testing | Production |
|---------|-------------|---------|------------|
| `SAVE_PROMPTS_AND_RESPONSES` | `True` | `True` | **`False`** |
| Clean logs | Weekly | After each test | N/A |
| Review logs | As needed | Always | N/A |

## Quick Reference

**Enable logging:**
```python
SAVE_PROMPTS_AND_RESPONSES = True
```

**Disable logging:**
```python
SAVE_PROMPTS_AND_RESPONSES = False
```

**Change folder:**
```python
PROMPTS_LOG_FOLDER = "my_custom_folder"
```

**Clean logs:**
```bash
# Delete the folder manually
rm -rf debug_prompts_log
```

---

**Remember:** Always disable logging before deploying to production! 🚀
