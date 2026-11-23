# Design: String Document IDs in Update and Remove Operations

## Approach
To make `update()` and `remove()` consistent with `get(doc_ids=...)`, we need to normalize/coerce the document IDs passed in `doc_ids` to match how `get()` or table storage keys handle them (string/integer conversion or set lookup). Specifically, when `doc_ids` is provided as an iterable containing strings (or mixed integers/strings), we can check existence and perform updates/removals using string representations or normalized IDs identical to `get()`, ensuring string IDs like `'1'` successfully match stored document ID `1` while non-castable or missing IDs are silently skipped or return empty lists.

## Files to change
- `tinydb/table.py`
- `tests/test_tinydb.py` (NEW or existing test file if present; let's check existing tests)

## Functions/classes
- Modify `Table.update`: accept string-formatted doc IDs in `doc_ids` and normalize/match them against table keys consistently with `get()`.
- Modify `Table.remove`: accept string-formatted doc IDs in `doc_ids` and normalize/match them against table keys consistently with `get()`.

## Test plan
- Test `update(doc_ids=['1'])` on a database with document ID 1 successfully updates the document and returns `[1]`.
- Test `remove(doc_ids=['1'])` on a database with document ID 1 successfully removes the document and returns `[1]`.
- Test `update(doc_ids=['999'])` or non-existent/non-castable string IDs returns `[]` and leaves documents unchanged.
- Verify performance overhead of string ID coercion is negligible (< 1%).

## Constraints respected
- ADR 2 & 4: Query cache is appropriately cleared on table mutations (`_update_table`).
- Layering: No architectural layers violated; changes are strictly contained within `Table` methods in `tinydb/table.py`.