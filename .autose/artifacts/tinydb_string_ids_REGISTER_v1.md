# Register: TinyDB String Document IDs Support (v1)

## A. Source Statements
- S-01: db.get(doc_id='1') finds my document fine [Issue Body]
- S-02: when I pass the same id as a string to update or remove, nothing happens. No error, no warning, the document is just unchanged. [Issue Body]
- S-03: Passing the int 1 instead of '1' works. [Issue Body]
- S-04: My ids come from a web form so they are always strings, and I really do not want to crash on every bad input either - but a silent no-op on a write is the worst of both worlds. [Issue Body]
- S-05: Please make these consistent with get (which accepts the string form). [Issue Body]

## B. Ambiguous Terms
None.

## C. Open Questions
None.

## D. Assumptions
None.

## E. Conflicts
None.

## F. Evidence Log
- EV-01: A3 repository-local analysis of TinyDB source code and test files. Code inspection confirms doc_ids lookup uses exact matching against integer table keys without coercing or parsing numeric string IDs during update/remove operations.

## G. Coverage Matrix
- Users and roles: COVERED (ACT-1)
- Core capabilities: COVERED (FR-001, FR-002)
- Data: COVERED
- Security and privacy: N/A
- Performance and capacity: N/A

## H. Change Log
- v1: Initial SRS, Register, and Validation specification created.
