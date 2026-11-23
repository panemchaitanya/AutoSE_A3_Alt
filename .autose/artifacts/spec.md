# Spec: Numeric Operation Fallback on Missing Fields

## Source
Issue #2: increment() crashes with KeyError when the field does not exist yet
> "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up... I would expect a counter on a missing field to simply start from 0, i.e. after the call above the document should be `{'page': '/home', 'count': 1}`. Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## Requirements
- FR-1: The `increment` operation shall treat a missing target field as having an initial value of 0 before applying the increment.
- FR-2: The `add` operation shall treat a missing target field as having an initial value of 0 before adding the specified value.
- FR-3: The `subtract` operation shall treat a missing target field as having an initial value of 0 before subtracting the specified value.

## Acceptance criteria
- Given a document without a target field, When `increment(field, n)` is applied, Then the resulting document contains the field with value equal to `n` (defaulting `n` to 1 if omitted).
- Given a document without a target field, When `add(field, n)` is applied, Then the resulting document contains the field with value equal to `n`.
- Given a document without a target field, When `subtract(field, n)` is applied, Then the resulting document contains the field with value equal to `-n`.

## Assumptions and open questions
- Assumption (ASM-1): Operations `increment`, `add`, and `subtract` apply to numeric types where a missing field implicitly evaluates to 0.