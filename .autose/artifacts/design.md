# Design: Add a limit parameter to search()

## Approach
We will update `Table.search` to accept an optional `limit: Optional[int] = None` parameter. When `limit` is provided, the search results will be sliced to at most `limit` elements before being returned (and before caching, or cached appropriately according to standard query caching). Specifically, `search(cond, limit=N)` returns at most the first `N` matches ordered by document ID. If `limit=None` or `limit` exceeds the number of matches, all matches are returned. Note that query caching keys by query object `cond`, so if different limits are passed with the same `cond`, we should be mindful of how caching works or whether `limit` should be part of the cache key or if caching should only apply when `limit` is not specified / or if `limit` should be included in the cache key or query representation. Wait, let's check if query cache keys by `cond`. Yes, `self._query_cache.get(cond)`. If someone calls `db.search(cond, limit=10)` and then `db.search(cond, limit=5)`, if cached by `cond`, it might return 10 results instead of 5. Therefore, if `limit` is not `None`, should we bypass the query cache or include `limit` in the cache / cache key? Or simpler: if `limit is not None`, we can either slice the cached result if cached, or skip caching when `limit is not None`, or store/key appropriately. Slicing the cached result if `cached_results` is not None (i.e. `cached_results[:limit]`) is extremely clean, efficient, and correct because query cache stores all matching documents in document ID order!

## Files to change
- `tinydb/table.py`
- `tests/test_tinydb.py` (or existing test files, let's check existing test files using `run_shell` or list_files)

## Functions/classes
- `Table.search(self, cond: QueryLike, limit: Optional[int] = None) -> list[Document]`

## Test plan
- Test `db.search(cond, limit=10)` with 100 matching documents returns exactly 10 in ascending doc ID order.
- Test `db.search(cond)` and `db.search(cond, limit=None)` returns all matching documents.
- Test `db.search(cond, limit=10)` with 5 matching documents returns all 5 documents.
- Test query caching behavior with `limit`.

## Constraints respected
- ADR 2: Query cache keyed by stable query hash (we reuse or safely slice cached results).
- Layering and typing standards.
