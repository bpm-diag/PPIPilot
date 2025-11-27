### Parameter Validation Rules

1. **Mutually Exclusive**: Cannot have both `"begin"/"end"` and `"count"` in the same PPIjson
2. **Required**: `"aggregation"` is always required
3. **Optional**: All other parameters are optional
4. **Empty Values**: Empty strings for `"begin"` or `"end"` default to process boundaries
5. **Column Validation**: `"group_by"` and attribute names in conditions must exist in the event log
6. **Case Sensitivity**: Activity names and attribute values are case-sensitive



## Time Conversion

The system automatically handles:
- **Nanosecond conversion**: Values > 1e6 are converted from nanoseconds to seconds
- **Timedelta objects**: Converted to seconds using `.total_seconds()`
- **Human-readable formatting**: Uses `format_time_duration()` for display
