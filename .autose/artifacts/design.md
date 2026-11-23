# Design: Prevent mutating search and retrieval results from modifying internal database cache

## Approach
To prevent retrieved or searched document dictionaries from sharing references with internal database caches or raw storage data, we ensure that deep copies (or fresh instantiations with deep copies) of document dictionaries are returned whenever documents are retrieved or searched across `Table` methods (`search`, `get`, `__iter__`, and cache hits).
Specifically, `Table.search` currently caches the list of matching `Document` instances in `self._query_cache`. When a cache hit occurs, returning a shallow copy (`cached_results[:]`) returns the exact same `Document` objects that are cached, meaning mutating nested dictionaries inside those documents modifies the cached instances (violating S-02/S-06 and FR-001). We will update query caching and retrieval methods so that a deep copy of each document (or fresh `Document` instances with deep-copied underlying dictionaries) is returned on every retrieval and search.

## Files to change
- `tinydb/table.py`
- `tests/test_tables.py` (NEW or modified existing test file)

## Functions/classes
- `tinydb.table.Table.search`: Ensure cached results or newly evaluated documents are deep-copied (`copy.deepcopy`) so returning them never exposes references to internal structures or cache entries.
- `tinydb.table.Table.get`: Ensure retrieved documents via `doc_id`, `doc_ids`, or `cond` return deep copies of the underlying dictionaries wrapped in `document_class`.
- `tinydb.table.Table.__iter__`: Ensure iterated documents return deep copies.

## Test plan
- Test that searching for a document, mutating a field (including nested dicts/lists) on the returned `Document`, and searching again returns the original un-mutated values stored in the database.
- Test that `get` (by `doc_id`, `doc_ids`, and `cond`) and `all()` / iteration return deep copies such that local mutations do not affect database state or subsequent retrievals.

## Constraints respected
- ADR 2 (Query cache keyed by stable query hash & correctness of cache contents).
- Layering and pure Python constraints: no third-party dependencies outside stdlib (`copy`).
