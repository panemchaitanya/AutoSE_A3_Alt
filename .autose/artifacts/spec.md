# Spec: increment() missing field handling

## Source
Issue #2: "increment() crashes with KeyError when the field does not exist yet"
> "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up: KeyError: 'count'"
> "Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## Requirements
- FR-1: The `increment` operation shall treat a missing field as having a default value of 0 and increment it by the specified amount (defaulting to 1 when no increment value is provided).
- FR-2: The `add` operation shall treat a missing field as having a default value of 0 and add the specified amount.
- FR-3: The `subtract` operation shall treat a missing field as having a default value of 0 and subtract the specified amount.

## Acceptance criteria
- Given a document without a target field, when the `increment` operation is applied, then the field is created with value 1 (or the specified increment amount).
- Given a document without a target field, when the `add` operation with value 5 is applied, then the field is created with value 5.
- Given a document without a target field, when the `subtract` operation with value 3 is applied, then the field is created with value -3.
- Given a document where the target field already exists with an integer value, when `increment`, `add`, or `subtract` is applied, then it operates correctly relative to the existing value without raising any KeyError.

## Assumptions and open questions
- Assumption: The default starting value for missing numeric fields in arithmetic operations (`increment`, `add`, `subtract`) is 0, as explicitly requested by the issue author.
