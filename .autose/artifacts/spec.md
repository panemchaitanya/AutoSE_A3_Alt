# Spec: TinyDB Increment and Operations Missing Field Handling

## Source
- Issue #2: "increment() crashes with KeyError when the field does not exist yet"
- Quote: "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up: KeyError: 'count'"
- Quote: "I would expect a counter on a missing field to simply start from 0, i.e. after the call above the document should be `{'page': '/home', 'count': 1}`. Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## Requirements
- FR-1: The `increment` operation shall initialize a missing field in a target document to 0 before incrementing its value by 1.
- FR-2: The `decrement` operation shall initialize a missing field in a target document to 0 before decrementing its value by 1.
- FR-3: The `add` operation shall initialize a missing field in a target document to 0 before adding `n`.
- FR-4: The `subtract` operation shall initialize a missing field in a target document to 0 before subtracting `n`.

## Acceptance criteria
- Given a document without the field 'count', when `db.update(increment('count'), doc_ids=[1])` is invoked, then the field 'count' is set to 1.
- Given a document without the field 'count', when `db.update(decrement('count'), doc_ids=[1])` is invoked, then the field 'count' is set to -1.
- Given a document without the field 'score', when `db.update(add('score', 5), doc_ids=[1])` is invoked, then the field 'score' is set to 5.
- Given a document without the field 'score', when `db.update(subtract('score', 3), doc_ids=[1])` is invoked, then the field 'score' is set to -3.

## Assumptions and open questions
- None. All requirements are directly stated by the issue author.