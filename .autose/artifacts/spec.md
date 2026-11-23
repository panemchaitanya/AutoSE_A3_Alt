# Spec: Add a limit parameter to search()

## Source
Issue #3: "Add a limit parameter to search()"
- S-01: "`db.search(cond)` always returns every match."
- S-02: "When a table has thousands of documents and I only need the first few (a "latest 10" list, a preview, pagination), I have to materialize the whole result list and slice it myself, which is wasteful."
- S-03: "Could `search` take an optional `limit`?"
- S-04: "`- limit=None` (default) keeps today's behavior - all matches, in document id order."
- S-05: "`- limit=N` returns at most the first N matches, in document id order."
- S-06: "- A limit larger than the number of matches just returns all matches."

## Requirements
- FR-1: The search method shall accept an optional parameter `limit` defaulting to `None`.
- FR-2: The search method shall return at most `N` matches when `limit=N` is provided, ordered by document ID.
- FR-3: The search method shall return all matches when `limit=None` or when `limit` is greater than the total number of matches.

## Acceptance criteria
- AC-001-1: Given a table containing 100 documents matching a condition, when `db.search(cond, limit=10)` is invoked, then exactly 10 documents are returned in ascending document ID order.
- AC-001-2: Given a table containing matching documents, when `db.search(cond)` or `db.search(cond, limit=None)` is invoked, then all matching documents are returned in ascending document ID order.
- AC-001-3: Given a table containing 5 documents matching a condition, when `db.search(cond, limit=10)` is invoked, then all 5 documents are returned.

## Assumptions and open questions
- ASM-1: Negative or non-integer values for `limit` are out of scope or will raise a ValueError / TypeError depending on standard Python slice/comparison behavior, as not specified by the issue.