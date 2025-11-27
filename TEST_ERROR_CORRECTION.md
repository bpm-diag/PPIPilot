# Test Error Correction and Retry Mechanisms

## Overview
This document explains how to test both the error correction mechanism and the retry mechanism in PPIPilot by injecting intentional errors or forcing 0 PPI generation.

## Test PPIs Injected

When test mode is enabled, the following two PPIs with intentional errors will be added to the JSON:

### 1. Average time with complex filter (will trigger filter removal)
```json
{
    "PPIname": "Average time from 'Declaration SAVED by EMPLOYEE' to the next activity in the process, excluding rejections",
    "PPIjson": {
        "begin": "activity == 'Declaration SAVED by EMPLOYEE'",
        "end": "",
        "aggregation": "average",
        "filter": "activity != 'Declaration REJECTED by EMPLOYEE' and activity != 'Declaration REJECTED by ADMINISTRATION' and activity != 'Declaration REJECTED by SUPERVISOR' and activity != 'Declaration REJECTED by MISSING' and activity != 'Declaration REJECTED by PRE_APPROVER' and activity != 'Declaration REJECTED by BUDGET OWNER'"
    }
}
```

**Expected Error**: The complex filter with multiple `and` operators will cause a `metric_resolution` error during JSON parsing/validation.

### 2. Minimum time with invalid group_by attribute
```json
{
    "PPIname": "Minimum time for 'Request Payment' across different case amounts",
    "PPIjson": {
        "begin": "activity == 'Request Payment'",
        "end": "",
        "aggregation": "minimum",
        "group_by": "case:amount"
    }
}
```

**Expected Error**: If `case:amount` doesn't exist in the log attributes, this will cause either a `metric_resolution` or `metric_computation` error.

## How to Test

There are two test modes available:

### Test Mode A: Error Correction Mechanism

#### Step 1: Enable Error Correction Test Mode
1. Upload your XES file and configure OpenAI key
2. Select PPI category (preferably **"time"** to test the time-based error PPIs)
3. Choose an activity
4. **Check the "🧪 Test Error Correction" checkbox** before clicking "Send options selected"
5. You should see an info message: "⚠️ Two PPIs with intentional errors will be added to test error correction."

### Step 2: Generate PPIs with Test Errors
1. Click "Send options selected"
2. The system will:
   - Generate normal PPIs from OpenAI
   - Inject the 2 test PPIs with errors
   - Execute all PPIs (including the error ones)
   - Capture errors from the test PPIs

### Step 3: Verify Error Capture
After execution, check:
1. **Console output** should show: `🧪 TEST MODE: Injected 2 test PPIs with errors to [filepath]`
2. **Error section** should appear in the UI showing the captured errors
3. **Error details** should include:
   - PPI name
   - Error type (`metric_resolution` or `metric_computation`)
   - Error message
   - Full error traceback

#### Step 4: Test Error Correction
1. Click the **"🔧 Fix JSON Errors with AI"** button
2. The system will:
   - Send the original JSON + errors to OpenAI
   - Request corrected versions
   - Save corrected JSON
   - Re-execute with corrected PPIs
3. Check the results to see if the errors were fixed

#### Expected Outcomes for Error Correction Test

**For the complex filter PPI:**
- **Before correction**: Error due to complex `and` operators in filter
- **After correction**: Filter should be simplified or removed, PPI should execute successfully

**For the invalid group_by PPI:**
- **Before correction**: Error due to non-existent `case:amount` attribute
- **After correction**: Either `group_by` removed or replaced with valid attribute

---

### Test Mode B: Retry Mechanism

#### Step 1: Enable Retry Test Mode
1. Upload your XES file and configure OpenAI key
2. Select any PPI category
3. Choose an activity
4. **Check the "🔄 Test Retry Mechanism" checkbox** before clicking "Send options selected"
5. You should see a warning message: "⚠️ First attempt will return 0 PPIs to trigger retry (max 2 retries)."

#### Step 2: Observe Retry Behavior
1. Click "Send options selected"
2. The system will:
   - **First attempt (Attempt 1/3)**: Generate PPIs normally, then clear all PPIs to simulate 0 results
   - Console shows: `🧪 RETRY TEST MODE: Cleared all PPIs from [filepath] to test retry mechanism`
   - System detects 0 valid PPIs and triggers retry
   - **Second attempt (Attempt 2/3)**: Generate PPIs normally without clearing (should succeed)
   - If still 0 PPIs, **Third attempt (Attempt 3/3)**: Final retry

#### Step 3: Verify Retry Logic
After execution, check:
1. **Console output** should show:
   - `🧪 RETRY TEST MODE: Cleared all PPIs...` (only on first attempt)
   - `⚠️ No valid PPIs in results table on attempt 1. Retrying...`
   - `Generating PPIs... (Attempt 2/3)`
   - `✅ Success! Generated X valid PPIs on attempt 2`
2. **UI spinner** should show retry attempt numbers
3. **Final results** should contain valid PPIs from the second attempt

#### Expected Outcomes for Retry Test

- **Attempt 1**: 0 PPIs (forced by test mode) → triggers retry
- **Attempt 2**: Normal PPI generation → should succeed with valid PPIs
- **Max retries**: System stops after 3 total attempts (initial + 2 retries)

## Verification Checklists

### Error Correction Test Checklist
- [ ] "🧪 Test Error Correction" checkbox appears in UI
- [ ] Info message shows when error correction test is enabled
- [ ] Console shows "🧪 TEST MODE: Injected 2 test PPIs with errors"
- [ ] Error section appears after execution
- [ ] 2 errors are captured and displayed
- [ ] Error details include PPI name, type, and message
- [ ] "🔧 Fix JSON Errors with AI" button appears
- [ ] Clicking fix button triggers OpenAI correction
- [ ] Corrected JSON is saved and re-executed
- [ ] Results show whether errors were fixed

### Retry Mechanism Test Checklist
- [ ] "🔄 Test Retry Mechanism" checkbox appears in UI
- [ ] Warning message shows when retry test is enabled
- [ ] Console shows "🧪 RETRY TEST MODE: Cleared all PPIs..." on first attempt
- [ ] UI spinner shows "Generating PPIs... (Attempt 1/3)"
- [ ] Console shows "⚠️ No valid PPIs in results table on attempt 1. Retrying..."
- [ ] UI spinner shows "Generating PPIs... (Attempt 2/3)"
- [ ] Second attempt generates valid PPIs
- [ ] Console shows "✅ Success! Generated X valid PPIs on attempt 2"
- [ ] Final results table contains valid PPIs from successful attempt
- [ ] Success message appears: "✅ PPI generation completed! Generated X valid PPIs."

## Notes

### Error Correction Test
- Test mode only injects errors for **"time"** category PPIs
- The injected PPIs are added **after** normal PPI generation
- Test PPIs are designed to trigger common error patterns
- The error correction system should preserve the original intent while fixing technical issues

### Retry Mechanism Test
- Retry test works for **any** category (time, occurrency, or both)
- The clearing of PPIs happens **only on the first attempt** (retry_count == 0)
- Subsequent retries generate PPIs normally without clearing
- Maximum of 3 total attempts: initial attempt + 2 retries
- The retry mechanism is triggered when `len(df_sin_error) == 0`

### Combining Both Tests
- ⚠️ **Do NOT enable both test modes simultaneously**
- The retry test clears all PPIs, so error correction test would have nothing to correct
- Test them separately for accurate results
