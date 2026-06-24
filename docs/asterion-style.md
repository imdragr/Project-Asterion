# Asterion Engineering Style

> Asterion is a long-lived knowledge platform.
>
> We optimize for correctness, understandability, and maintainability over
> short-term implementation speed.
>
> Code should be easy to reason about six months from now by someone who did
> not originally write it.

This document defines **how software is implemented**. It is the companion to
[Ground Truths](./asterion-tenets.md), which defines **what
must always be true**. Where a topic is owned by Ground Truths (invariants,
architectural status, precedence), this document cross-references rather than
restates it.

**Where code lives:** Asterion is a domain-agnostic Core with pluggable Domain
Packs (see Ground Truths,
[Asterion Core and Domain Packs](./asterion-tenets.md#asterion-core-and-domain-packs)).
Generic, domain-independent capabilities belong in **Core**; domain-specific
ontologies, canonicalization, validation, and extraction belong in a **Domain
Pack** (horology today). Dependencies point inward toward Core, and Core must
never import a Domain Pack (Invariant 7). When in doubt where something belongs,
default to the horology pack and promote to Core only once a second and third
domain earn the abstraction (Anti-Goal 7 — premature generalization).

## Influences

Asterion's engineering practices are heavily influenced by long-term systems
engineering philosophies, including:

- TigerStyle
- Domain-Driven Design (DDD)
- Event-Driven Architecture (EDA)
- Architecture Decision Records (ADRs)
- Reliability engineering practices from distributed systems

TigerStyle, in particular, places strong emphasis on correctness, explicitness,
simplicity, and long-term maintainability.

Asterion adopts many of these principles but is not a strict implementation of
TigerStyle. We evaluated its principles individually and adopted those that
align with Asterion's goals as a long-lived knowledge platform.

Adopted principles include:

- Design before implementation.
- Explicit invariants and assertions.
- Small and intentional public APIs.
- Explicit failure modeling.
- Preference for understandability over cleverness.
- Intentional and documented technical debt only.
- Strong emphasis on correctness and observability.

Some TigerStyle practices were modified or not adopted because they are less
applicable to a Python-based application platform.

Our goal is not ideological purity. It is software that remains understandable,
reliable, and maintainable for many years.

### A note on examples

Some examples below reference the **target architecture** (e.g. an event bus, a
DI container, Temporal). These are labeled **[target]**. Examples drawn from the
**current implementation** are labeled **[current]**. A label is only used where
the distinction matters.

---

# 1. Design Before Implementation

No significant feature should be implemented without first answering:

- What problem are we solving?
- What are the domain concepts?
- What are the invariants?
- What events exist?
- How can this fail?
- How is idempotency guaranteed?

Minimum required documentation before implementation:

- Architecture sketch
- Event definitions
- Aggregate boundaries
- Failure modes

---

# 2. Invariants Must Be Explicit

Critical business rules must be encoded as explicit checks that **cannot be
silently disabled**.

Do **not** use Python `assert` for business invariants — assertions are stripped
under `-O` / `PYTHONOPTIMIZE`, so the invariant vanishes exactly where it
matters most.

Bad:

```python
def publish_reference(reference):
    reference.status = "published"
```

Also bad (disappears under `-O`):

```python
def publish_reference(reference):
    assert reference.reviewed_at is not None
    reference.status = ReferenceStatus.PUBLISHED
```

Good:

```python
def publish_reference(reference):
    if reference.reviewed_at is None:
        raise InvariantViolation("Cannot publish an unreviewed reference.")
    if reference.status is not ReferenceStatus.REVIEWED:
        raise InvariantViolation(
            f"Cannot publish from status {reference.status}."
        )

    reference.status = ReferenceStatus.PUBLISHED
```

If an invariant exists, it should be visible in code — and it should still be
there at runtime.

---

# 3. Events Are Contracts

Events are immutable contracts between components.

Bad:

```python
publish("brand_created", brand.__dict__)
```

Good **[target]**:

```python
event = BrandCreatedEvent(
    brand_id=brand.id,
    brand_name=brand.name,
    created_at=utc_now(),
)

event_bus.publish(event)
```

Event schemas evolve intentionally. Breaking changes require a migration plan.

---

# 4. Failure Modes Must Be Enumerated

Every subsystem must define how it can fail. (This is the engineering practice
behind Ground Truths Invariant 2 — observable transitions.)

Example — YouTube ingestion may fail because of:

- Network timeout
- Quota exhaustion
- Invalid transcript
- Duplicate ingestion
- Schema mismatch

Prefer explicit, typed failures:

```python
class TranscriptUnavailable(Exception):
    pass

class DuplicateVideoError(Exception):
    pass
```

Avoid swallowing failures:

```python
except Exception:
    pass
```

---

# 5. Idempotency Is Non-Negotiable

Every asynchronous operation must be safe to retry. Workers may run more than
once; the system must behave correctly when they do.

A pre-read **check-then-act** is *not* idempotent — under concurrent workers,
both pass the check and both process:

Bad:

```python
if ingestion_repository.already_processed(video_id):
    return
worker.process_video(video_id)   # race: two workers both reach here
```

Use a **claim-based** pattern backed by a uniqueness guarantee. Claim the work
atomically and proceed only if *you* won the claim:

```python
claimed = ingestion_repository.claim(video_id)  # INSERT ... ON CONFLICT
                                                 # DO NOTHING RETURNING id
if not claimed:
    return  # someone else owns this video

worker.process_video(video_id)
```

```sql
-- claim(): returns a row only to the worker that won
INSERT INTO processed_videos (video_id, status)
VALUES (:video_id, 'claimed')
ON CONFLICT (video_id) DO NOTHING
RETURNING video_id;
```

**Enumerate the failure mode** (per §4): if processing crashes *after* the claim
commits, existence-based dedup will treat the work as done while it never
finished. Guard against it with one of:

- claim and work in the **same transaction** (both commit or both roll back), or
- a **status column** (`claimed → processing → done`) so incomplete work is
  visible and recoverable, rather than mere row existence.

---

# 6. Explicit Over Magic

Prefer obvious behavior over clever behavior.

Bad:

```python
@auto_discover_everything
@auto_wire_dependencies
@auto_register_events
```

Good **[target]**:

```python
container.register(BrandService)
container.register(VideoIngestionService)

event_bus.subscribe(
    VideoUploadedEvent,
    video_processor.handle,
)
```

The reader should understand execution flow by reading the code. (This is the
code-level expression of the *Explicitness over magic* value in Ground Truths.)

---

# 7. Push Control Flow Up

High-level orchestration should live at the top.

Bad:

```python
service.execute()
```

Good:

```python
videos = repository.fetch_pending()
validated = validator.validate(videos)
events = extractor.extract(validated)
publisher.publish(events)
```

Top-level workflows should read like a story.

---

# 8. Minimize Public APIs

Smaller interfaces are easier to maintain.

Bad:

```python
create_brand()
update_brand()
merge_brand()
patch_brand()
rename_brand()
canonicalize_brand()
```

Good:

```python
brand_service.handle(command)
```

or:

```python
aggregate.apply(event)
```

Every public API is a maintenance burden. Keep them small.

---

# 9. Optimize For Locality Of Reasoning

Understanding a feature should require reading as little code as possible.

Prefer:

```python
def ingest_video():
    ...
```

over needless call chains:

```python
def ingest_video():
    step_one()

def step_one():
    step_two()

def step_two():
    step_three()
```

Extract code only when doing so improves readability. Avoid unnecessary
indirection. (This bounds how far the adapter pattern in Ground Truths
Invariant 3/4 is taken: boundaries, not ceremony.)

---

# 10. Dependencies Must Justify Their Existence

Every dependency should answer:

- What problem does it solve?
- Why is it better than building internally?
- Can it be removed?
- What happens if it disappears?

Prefer mature, boring technology.

---

# 11. Intentional Technical Debt Only

Technical debt is allowed only when it is:

- intentional,
- documented,
- owned, and
- accompanied by explicit tradeoffs.

Every intentional debt item is documented in `docs/technical-debt.md`.

Example:

```markdown
## TD-001

Title:
Polling instead of CDC

Date:
2026-06-24

Owner:
Dhruva

Reason:
Faster MVP delivery.

Alternative:
Debezium CDC pipeline.

Risk:
Higher latency and duplicate processing.

Revisit:
After first production ingestion pipeline.
```

Undocumented technical debt is considered a bug.

---

# 12. Observability

This is the implementation of Ground Truths **Invariant 2 — Every meaningful
state transition is observable**. Before optimizing for scale, ensure the
system can answer:

- What happened?
- Why did it happen?
- When did it happen?
- Which component failed?

Every service should emit:

- Logs
- Metrics
- Traces

---

# 13. Comments Explain Why, Not What

Bad:

```python
# Increment count
count += 1
```

Good:

```python
# We intentionally overcount here because retries are possible.
count += 1
```

Code explains *what*. Comments explain *why*.

---

# 14. Prefer Boring Solutions

A simple solution that works is preferable to an elegant solution nobody
understands.

Asterion favors:

- PostgreSQL over niche databases.
- Explicit state machines over hidden framework magic.
- Simple workers over distributed orchestration — until the domain genuinely
  calls for durable workflow orchestration (see Ground Truths
  [Architectural Status](./asterion-tenets.md#architectural-status)).

Complexity must justify itself.

---

# 15. Testing Philosophy

A document this concerned with correctness must be explicit about how
correctness is verified. Tests are scoped to current reality and labeled by
status, mirroring the Ground Truths status axis.

## Current expectations

- **Unit tests** — pure domain logic and invariants. Fast, no I/O.
- **Integration tests** — code against real infrastructure, not mocks. Run
  against a **real Postgres** via **Testcontainers**; mocking the database hides
  the SQL and migration bugs that matter most.
- **Migration tests** — every migration must apply cleanly base→head, downgrade
  consistently, and match the model metadata. Enforced with **pytest-alembic**
  (`test_upgrade`, `test_up_down_consistency`, `test_model_definitions_match_ddl`,
  `test_single_head_revision`).

## Future expectations

- **Contract tests** — for event and adapter boundaries, once those boundaries
  stabilize.
- **End-to-end tests** — for the full ingestion pipeline, once it exists.

## CI expectations

CI must enforce, on every change:

- lint + format (`ruff`)
- type checking (`mypy`, strict)
- the test suite (`pytest`), including migration tests
- exactly **one** Alembic head (via `test_single_head_revision`)

A red bar blocks merge. Migration safety is enforced by tests, not by
convention.

---

# Long-Term Understandability Is The Final Metric

The primary question when reviewing code is:

> Will this still make sense one year from now?

If not, redesign it.
