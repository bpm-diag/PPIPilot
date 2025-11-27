# PPI JSON Parameters Guide

## Required Structure

```json
{
  "PPIname": "string (required)",
  "PPIjson": {
    // Parameters go here
  }
}
```

## Core Parameters

### **Metric Type** (Choose ONE approach):

**Option 1: Time-based Metrics**
```json
{
  "begin": "condition_string (optional)",
  "end": "condition_string (optional)",
  "aggregation": "required"
}
```

**Option 2: Count-based Metrics**
```json
{
  "count": "condition_string (required)",
  "aggregation": "required"
}
```

### **Required Parameter:**
- `"aggregation"` (string, always required)
  - **Valid values:** `"average"`, `"percentage"`, `"total"`, `"minimum"`, `"maximum"`

### **Optional Enhancement Parameters:**
- `"metric_condition"` (string): Additional condition like `"> 0"`, `"<= 100"`
- `"group_by"` (string): Attribute name for grouping (must exist in event log)
- `"filter"` (string): Filter condition to apply to cases

## Condition Formats

### **Activity Conditions:**
```
"activity == 'ActivityName'"
"activity != 'ActivityName'"
```

### **Attribute Conditions:**
```
"attribute_name == 'value'"
"attribute_name != 'value'"
"attribute_name < 'value'"
"attribute_name > 'value'"
"case:resource == 'John Doe'"
"case:amount > 1000"
```

### **Complex Conditions (OR):**
```
"activity == 'Activity1' or activity == 'Activity2'"
"attribute1 == 'value1' or attribute2 == 'value2'"
```

## Complete Examples

### **Time Metric - Minimal:**
```json
{
  "PPIname": "Process duration",
  "PPIjson": {
    "begin": "",
    "end": "",
    "aggregation": "average"
  }
}
```

### **Time Metric - Full:**
```json
{
  "PPIname": "Processing time by department",
  "PPIjson": {
    "begin": "activity == 'Start'",
    "end": "activity == 'End'",
    "aggregation": "average",
    "metric_condition": "> 0",
    "group_by": "org:department",
    "filter": "case:amount > 1000"
  }
}
```

### **Count Metric - Minimal:**
```json
{
  "PPIname": "Number of submissions",
  "PPIjson": {
    "count": "activity == 'Submit'",
    "aggregation": "total"
  }
}
```

### **Count Metric - Full:**
```json
{
  "PPIname": "Approvals by resource for high-value cases",
  "PPIjson": {
    "count": "activity == 'Approve'",
    "aggregation": "total",
    "metric_condition": "> 0",
    "group_by": "case:resource",
    "filter": "case:amount > 5000"
  }
}
```

## ❌ What NOT to Use

### **Invalid Combinations:**
1. **Never combine time and count metrics:**
   ```json
   // ❌ WRONG - Don't use both
   {
     "begin": "activity == 'Start'",
     "count": "activity == 'Submit'",
     "aggregation": "average"
   }
   ```

2. **Missing aggregation:**
   ```json
   // ❌ WRONG - aggregation is required
   {
     "begin": "activity == 'Start'",
     "end": "activity == 'End'"
   }
   ```

3. **Invalid attribute names:**
   ```json
   // ❌ WRONG - attribute must exist in event log
   {
     "count": "activity == 'Submit'",
     "aggregation": "total",
     "group_by": "nonexistent_column"
   }
   ```

## ✅ Validation Rules

1. **Mutually Exclusive**: Cannot have both `"begin"/"end"` and `"count"` in the same PPIjson
2. **Required**: `"aggregation"` is always required
3. **Optional**: All other parameters are optional
4. **Empty Values**: Empty strings for `"begin"` or `"end"` default to process boundaries
5. **Column Validation**: `"group_by"` and attribute names in conditions must exist in the event log
6. **Case Sensitivity**: Activity names and attribute values are case-sensitive

## Supported Operators

- `==` (equals)
- `!=` (not equals)
- `<` (less than)
- `>` (greater than)
- `<=` (less than or equal)
- `>=` (greater than or equal)
