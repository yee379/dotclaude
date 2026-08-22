# Performance Review Catalogue

Loaded at §4 of `/codebase-eng-review`. Work every area; flag issues **and** proactively
suggest concrete optimisations with an effort estimate, even when they are not blockers.

For each area below, flag issues **and proactively suggest concrete optimisations** — not just problems. If you spot a clear win (even if it's not a blocker), surface it as a recommendation with an effort estimate.

**Database and I/O**
* N+1 queries — identify any loop that issues a query per item; recommend eager loading, batching, or a JOIN.
* Missing indexes — flag any query filtering or sorting on an unindexed column; propose the index.
* Over-fetching — `SELECT *` or loading full entities when only a few fields are needed; recommend projections.
* Transaction scope — long-held transactions that block rows longer than necessary; recommend tightening.
* Connection pool sizing — new services or high-throughput paths with no pool config.

**Algorithmic complexity**
* O(n²) or worse loops — nested iterations over collections that could be replaced with a map/set lookup.
* Repeated work inside loops — computations that are loop-invariant and should be hoisted out.
* Sorting large collections repeatedly — recommend caching sorted results or using a heap/priority queue.

**Memory and allocations**
* Large objects held in memory longer than needed — recommend streaming, pagination, or early release.
* Unnecessary copies of large collections — flag places where a view or generator would suffice.
* Unbounded growth — caches, queues, or in-memory stores with no eviction policy.

**Caching opportunities**
* Expensive computations or external calls that are called repeatedly with the same inputs — recommend memoisation or a cache layer with an appropriate TTL.
* Results that could be precomputed at write time rather than recalculated at read time.

**Concurrency and parallelism**
* Sequential I/O that could be parallelised (`asyncio.gather`, thread pools, batch APIs).
* Blocking calls on the async/event loop path — recommend offloading to a thread executor.
* Lock contention — shared mutable state under a lock that could be replaced with a lock-free structure or message passing.

**Frontend / API efficiency** (if applicable)
* Over-fetching from APIs — returning large payloads when clients use only a subset; recommend field selection or GraphQL.
* Chatty APIs — multiple round-trips that could be collapsed into one request.
* Missing HTTP caching headers on stable resources.

**Quick-win checklist** — flag any of these present in the plan:
- [ ] Bulk-insert / upsert instead of per-row writes in a loop
- [ ] Lazy evaluation where eager evaluation is used but the result is not always needed
- [ ] Compiled regex / prepared statements instead of string-built queries in a hot path
- [ ] Pagination or cursor-based iteration instead of loading full result sets
- [ ] Response compression (gzip/brotli) not enabled on large payloads
