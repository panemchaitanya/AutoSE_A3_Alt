# Spec: increment() crashes with KeyError when the field does not exist yet

## Source
Issue #2: "increment() crashes with KeyError when the field does not exist yet"
> "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up: KeyError: 'count'"
> "I would expect a counter on a missing field to simply start from 0, i.e. after the call above the document should be `{'page': '/home', 'count': 1}`. Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## Requirements
- FR-1: The `increment` operation shall treat a missing field on a target document as having a default value of 0 before incrementing.
- FR-2: The `add` operation shall treat a missing field on a target document as having a default value of 0 before adding the specified amount.
- FR-3: The `subtract` operation shall treat a missing field on a target document as having a default value of 0 before subtracting the specified amount.

## Acceptance criteria
- Given a document without a `count` field, when `db.update(increment('count'), doc_ids=[1])` is executed, then the document shall be updated to contain `count: 1`.
- Given a document without a `score` field, when `db.update(add('score', 5), doc_ids=[1])` is executed, then the document shall be updated to contain `score: 5`.
- Given a document without a `score` field, when `db.update(subtract('score', 3), doc_ids=[1])` is executed, then the document shall be updated to contain `score: -3`.

## Assumptions and open questions
- Assumption: Default value for numeric operations (`increment`, `add`, `subtract`) on non-existent fields is 0, as explicitly requested by the issue author.
