# Design: TinyDB String Document IDs Support

## Approach
Modify `Table.update` and `Table.remove` methods in `tinydb/table.py` so that when `doc_ids` parameter is provided, any string representation of an integer is properly converted to an integer (using `self.document_id_class` or `int`), matching the robust behavior of `get` and other lookup operations.

## Files to change
- `tinydb/table.py`

## Functions/classes
- `Table.update` (modify doc_ids handling)
- `Table.remove` (modify doc_ids handling)

## Test plan
- Test `db.update({'x': 2}, doc_ids=['1'])` updates document 1 and returns `[1]`.
- Test `db.remove(doc_ids=['1'])` removes document 1 and returns `[1]`.
- Test mixed/invalid strings or standard integer IDs still work properly.

## Constraints respected
- ADR 2: Query cache is still properly cleared on table mutation.
- ADR 4: Table mutation methods clear the query cache after writing new state.
- Layering constraints: No changes to queries.py or storage classes are needed.
