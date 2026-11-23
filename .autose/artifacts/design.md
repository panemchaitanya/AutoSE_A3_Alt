# Design: Numeric Operation Fallback on Missing Fields

## Approach
Modify the `increment`, `add`, and `subtract` operations in `tinydb/operations.py` to handle missing fields gracefully by defaulting their initial value to 0 instead of causing a `KeyError`.

## Files to change
- `tinydb/operations.py`
- `tests/test_operations.py` (NEW or modified tests for missing fields)

## Functions/classes
- `tinydb/operations.py`: modify `increment`, `add`, and `subtract` operations/functions to use `.get(field, 0)` or check presence.

## Test plan
- Test `increment` on a missing field (with default amount and custom amount).
- Test `add` on a missing field.
- Test `subtract` on a missing field.

## Constraints respected
- Adheres to the layering rules and existing architecture where operations are small transform factories in `tinydb/operations.py`.