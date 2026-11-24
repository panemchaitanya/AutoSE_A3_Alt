# Spec: TinyDB String Document IDs Support

## Source
Issue #1: "update() and remove() silently do nothing when I pass the doc id as a string"
> `db.get(doc_id='1')` finds my document fine, but when I pass the same id as a string to `update` or `remove`, nothing happens. No error, no warning, the document is just unchanged.

## Requirements
- FR-1: The `update` method shall accept document IDs passed as string representations of integers in `doc_ids` and successfully update the corresponding documents.
- FR-2: The `remove` method shall accept document IDs passed as string representations of integers in `doc_ids` and successfully remove the corresponding documents.
- NFR-1: Write operations (`update`, `remove`) must behave consistently with read operations (`get`) regarding integer-convertible string document IDs without introducing silent no-ops.

## Acceptance criteria
- Given a database containing a document with integer ID 1, when `db.update({'x': 2}, doc_ids=['1'])` is executed, then the document with ID 1 is updated to `{'x': 2}` and the method returns `[1]`.
- Given a database containing a document with integer ID 1, when `db.remove(doc_ids=['1'])` is executed, then the document with ID 1 is removed from the database and the method returns `[1]`.

## Assumptions and open questions
- Assumption: String IDs passed to `update` or `remove` are integer-convertible strings (consistent with `db.get(doc_id='1')`), chosen to maintain backward compatibility and API consistency without breaking existing numeric ID lookups.
