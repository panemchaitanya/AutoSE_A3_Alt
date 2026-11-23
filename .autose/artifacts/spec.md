# Spec: String Document IDs in Update and Remove Operations

## Source
GitHub Issue #1: "update() and remove() silently do nothing when I pass the doc id as a string"
- Quoted key sentences:
  - "`db.get(doc_id='1')` finds my document fine, but when I pass the same id as a string to `update` or `remove`, nothing happens. No error, no warning, the document is just unchanged."
  - "Please make these consistent with `get` (which accepts the string form)."

## Requirements
- FR-1: The database `update` method shall accept document IDs formatted as strings (when castable to integers or matching the table's document ID type) in `doc_ids` and successfully update the matching documents, consistent with `get()`.
- FR-2: The database `remove` method shall accept document IDs formatted as strings (when castable to integers or matching the table's document ID type) in `doc_ids` and successfully remove the matching documents, consistent with `get()`.
- NFR-1: Document ID coercion for string inputs in `update` and `remove` shall not degrade execution performance beyond 1% overhead per call compared to integer ID handling.

## Acceptance criteria
- Given a database initialized with a document `{'x': 1}` resulting in document ID 1, when `db.update({'x': 2}, doc_ids=['1'])` is executed, then the document with ID 1 is updated to `{'x': 2}` and the method returns `[1]`.
- Given a database initialized with a document `{'x': 1}` resulting in document ID 1, when `db.remove(doc_ids=['1'])` is executed, then the document with ID 1 is removed and the method returns `[1]`.
- Given a database initialized with a document `{'x': 1}` resulting in document ID 1, when `db.update({'x': 3}, doc_ids=['999'])` is executed, then no documents are updated and the method returns an empty list `[]`.

## Assumptions and open questions
- Assumption: String document IDs passed to `update()` and `remove()` should be coerced to integers identically to how `get()` handles them, since TinyDB internal document IDs are integers by default. (Basis: Assumed based on user request for consistency with `get()`)
- Assumption: Non-castable string IDs (e.g. `'abc'`) should continue to yield no matching documents (returning empty list `[]`) without raising unhandled exceptions, or behave consistently with invalid integer/string lookups in `get()`.
