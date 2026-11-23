# Design: increment() missing field handling

## Approach
Modify `tinydb/operations.py` so that `increment`, `add`, and `subtract` check if the target field exists in the document (using `field in doc`). If it is missing, treat the default value as `0` before performing the operation. This avoids `KeyError` when operating on documents without the specified field, allowing counters and numeric fields to be initialized lazily.

## Files to change
- `tinydb/operations.py`

## Functions/classes
- `add(field: str, n: Union[int, float, str])`
- `subtract(field: str, n: Union[int, float])`
- `increment(field: str)`
- (`decrement` can also optionally be updated if appropriate, but specification focuses on `increment`, `add`, and `subtract`)

## Test plan
- Test `increment` on a document without the field; verify it creates the field with value 1.
- Test `increment` on a document where the field already exists; verify it increments correctly.
- Test `add` with a value (e.g., 5) on a document without the field; verify it creates the field with value 5.
- Test `subtract` with a value (e.g., 3) on a document without the field; verify it creates the field with value -3.
- Test existing functionality for `add`, `subtract`, and `increment` on existing fields.

## Constraints respected
- Layering: `tinydb/operations.py` remains focused purely on transform closures and does not import database/query/storage modules unnecessarily.
