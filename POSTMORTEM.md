# Job Queue — Postmortem (English)

**Status:** completed. **Dates:** built June 2026, revisited October 2026.
**Scope:** a task queue with producer API, a competing-consumer worker, bounded retries, and a dead-letter box — PostgreSQL only, no broker.

## What I set out to learn

I could install Celery in an afternoon and have a "production-grade" queue. I could not explain what it did. The point of this project was to be able to explain it — so I built the smallest thing that is genuinely a queue, and let every shortcut in the design tell me where the real engineering was.

## Decisions

**D1 — Postgres table as the queue, `FOR UPDATE SKIP LOCKED` as the claim.**
The claim has to be atomic across workers. Postgres gives this for free on a row lock: each worker's `SELECT` skips rows another transaction holds. Redis/Bull/SQS all re-implement this atomicity one level up. Staying in the database also means job state is transactional with the business data that produced it — no dual-write problem between "save order" and "enqueue job."

**D2 — Status enum over a fancy state machine.** `PENDING → RUNNING → COMPLETED / DEAD_LETTER`, `PENDING` again on retry. Five states, one transition table I could draw on paper. Anything more would have been ceremony for a stage-1 project.

**D3 — Bounded retries (MAX_RETRIES=5) with error messages on the row.** Every failure writes `error_message` onto the row before re-queueing. The alternative — log-only errors — makes the queue un-debuggable the first time a job fails at 3am: with this, `SELECT * FROM jobs WHERE status='dead_letter'` is the whole incident report.

**D4 — Dead-letter as quarantine, not deletion.** A poisoned payload is a bug report you didn't have to reproduce. Keeping dead jobs with their payload means the fix starts at the data, not at a log grep.

**D5 — structlog + request-ID middleware.** Logs are JSON events (`job_completed`, `job_failed`, with ids), not prose. The request-ID middleware came from the auth-service sibling and made the API debuggable end-to-end.

## What went wrong (and what it taught me)

**W1 — The busy-poll tax.** The worker sleeps 2 seconds between empty polls. Fine for one worker; at N workers it's N/2 queries per second of pure load on Postgres. Real brokers solve this with `LISTEN/NOTIFY`-style push. I could move the worker onto Postgres `NOTIFY` and keep the "no Redis" property — deliberately not done, because the polling version taught me what the notification is *for*.

**W2 — The retry policy is a bare counter.** No exponential backoff, no jitter. A deadlocked downstream gets hammered 5 times as fast as it can fail. Backoff is a 15-line change; leaving it out was a choice to see the shape of the problem first.

**W3 — Long transactions hold row locks.** `FOR UPDATE` holds the row through `process_job`. A slow job keeps its row locked for the full run — fine at this scale, a real problem if a job runs minutes: the lock should be short (claim → commit) with a separate lease/heartbeat. This is the single change I'd make before any real deployment.

**W4 — `time.sleep()` in the worker loop.** Not asyncio, no graceful shutdown handling, SIGKILL leaves a job in RUNNING forever (no lease timeout to reclaim it). The event-log project inherits this lesson: *worker state must be recoverable from the log, or the log IS the state.*

## What I'd do differently / next

1. Claim with a short transaction + lease heartbeat (W3).
2. Exponential backoff with jitter (W2).
3. `LISTEN/NOTIFY` instead of polling (W1).
4. Then the real question: this queue is a state *table*. What if the *log* were the source of truth — replay, snapshots, idempotency? → that became the **append-only event log**, the next stage.

## Verdict

A queue is not a service you install; it's a pattern you can write down: **atomic claim + status column + retry policy + dead-letter quarantine.** Everything a broker sells you on top of that is scale, not semantics. Building it took the magic out of the tooling — which was the entire point.

---

*Stage 1 of a three-project backend sequence: auth-service → job-queue → event-log. Postmortems written for each.*