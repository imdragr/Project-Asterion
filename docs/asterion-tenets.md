# Asterion Architecture — Ground Truths

> This document defines **what must always be true** about Asterion: its
> invariants, principles, anti-goals, and the current status of its
> architecture.
>
> It is the companion to [Engineering Style](./asterion-style.md), which
> defines **how software is implemented**. Where the two overlap, this
> document is authoritative on _what_ must hold; Engineering Style is
> authoritative on _how_ it is expressed in code. Cross-reference rather
> than duplicate.
>
> Changing any invariant or principle in this document requires an
> Architecture Decision Record (see [Governance](#governance)).

---

## What Asterion Is

Asterion is a **provenance-aware, domain-agnostic knowledge engine**. Horology
is the **first implemented domain**, not the platform itself.

The system is designed to support multiple enthusiast and knowledge domains —
watches, cars, perfumes, books, eyewear, fountain pens, and others — without
requiring modifications to the core platform. A domain is added as a **Domain
Pack** on top of a generic **Core**.

This is an evolution of the vision, not a replacement of the existing
architecture. Every invariant and principle below was selected because it is a
fundamental system-design property, not a horology-specific implementation
detail — which is precisely why the platform can generalize.

> **Status discipline:** the multi-domain capability is _design intent_, not a
> finished abstraction. Horology is the only implemented domain today. The
> Core/Domain-Pack boundary is being **validated through horology**, not
> hardened in advance (see [Anti-Goal 7](#anti-goal-7--premature-generalization)
> and [Architectural Status](#architectural-status)).

---

## What Asterion Optimizes For

Asterion is a long-lived, human-curated knowledge platform. It optimizes for:

- **Correctness** over performance.
- **Human trust and provenance** over full automation.
- **Simplicity and understandability** over cleverness.
- **Operational simplicity** over architectural novelty.
- **Evolvability** over premature optimization.
- **Explicitness** over magic.
- **Traceability** over convenience.

These are values, not an ordering. When they conflict, resolve by the
precedence below.

---

## Precedence — Conflict Resolution

Principles inevitably conflict. When they do, the higher-ranked concern wins:

1. **Correctness**
2. **Human trust and provenance**
3. **Simplicity and understandability**
4. **Operational simplicity**
5. **Evolvability**
6. **Performance**

Rationale for the order: Asterion is a single-operator, curated knowledge
platform. A system that is fast but wrong, untrustworthy, unmaintainable, or
un-operable has failed at something more important than speed. Performance is
last not because it is unimportant, but because it is the concern most safely
deferred until the others are satisfied.

---

## Asterion Core and Domain Packs

Asterion is composed of a generic **Core** and pluggable **Domain Packs**.

### Asterion Core

Generic knowledge-engine capabilities, independent of any single domain:

- Identity and canonicalization
- Entity resolution
- Provenance
- Claims and assertions
- Sources and ingestion
- Eventing
- Review workflows
- Search and retrieval
- Pipeline orchestration

### Domain Packs

Domain-specific knowledge and rules layered on top of Core:

- **Horology** — the initial implementation.
- Future domains — cars, perfumes, books, eyewear, fountain pens, etc.

A Domain Pack is a **bounded context**. Adding one primarily involves:

- new ontologies
- new canonicalization rules
- new validation rules
- domain-specific extraction logic

**Horology is an implementation of the platform, not the platform itself.**

---

## Architectural Layers

```text
Applications
    ↓
Domain Packs
    ↓
Asterion Core
    ↓
Infrastructure Adapters
```

- **Applications** — user-facing products and APIs.
- **Domain Packs** — watches, cars, perfumes, books, etc.
- **Asterion Core** — generic knowledge-engine capabilities.
- **Infrastructure Adapters** — databases, message brokers, search engines,
  external APIs, LLM providers.

**Dependencies always point inward, toward Asterion Core.** Core depends on
nothing outward: it defines the ports; infrastructure adapters implement them;
domain packs and applications build on top. This is the essence of onion /
hexagonal architecture that Asterion adopts — see Invariant 4 for the
calibration (dependency _direction_ is mandatory; internal abstraction
_ceremony_ is not).

---

## Architectural Invariants

The following invariants are foundational. Changing any of them requires an ADR.

### Invariant 1 — Every datum has exactly one canonical owner

At any point in time, each piece of business data has exactly one canonical,
authoritative owner.

Examples of canonical ownership:

- Entity / relational truth → Postgres
- Workflow truth → Temporal
- Large binary artifacts → Blob storage

**Derived representations are permitted** — projections, analytical stores
(e.g. ClickHouse), search indexes, materialized views, and caches — provided
they are:

- explicitly **non-authoritative**,
- **rebuildable** from the canonical owner, and
- **documented** as derived.

What is forbidden is _ambiguous_ ownership: two systems each believing they are
the source of truth for the same datum.

---

### Invariant 2 — Every meaningful state transition is observable

No meaningful state transition may occur silently.

A transition is **meaningful** if it changes business state, crosses a system
boundary, or advances a fact's lifecycle (creation, extraction, review,
approval, publication, deletion). Internal computational steps are not
meaningful transitions and need not be individually observable.

Every meaningful transition must, where applicable, emit:

- Logs
- Metrics
- Domain events
- Audit records

See [Engineering Style §12](./asterion-style.md) for how observability is
implemented.

---

### Invariant 3 — Every external interaction is explicit

External systems are represented through explicit boundaries (adapters) at the
point where Asterion meets something it does not own.

Examples:

- Source adapters (e.g. YouTube)
- Storage adapters
- LLM adapters

Business logic must never directly depend on the _implementation details_ of an
external system. Note the calibration in Invariant 4: adapters exist only at
**genuine external boundaries**, not as ceremony around internal code.

---

### Invariant 4 — Business concepts do not depend on infrastructure concepts

The core domain expresses business concepts. It must not be shaped by the
concepts of any particular infrastructure. Combined with the layering above:
dependencies point inward, toward Core.

Calibration (this invariant is about coupling, not abstraction for its own sake):

**Allowed:**

- Using SQLAlchemy directly inside infrastructure / persistence code.
- Using a ClickHouse client directly inside analytical code.
- Using a Temporal client directly inside orchestration code.

**Discouraged:**

- Repository abstractions layered over SQLAlchemy without clear, present value.
- Portability layers built solely to hedge a hypothetical future migration.

Infrastructure may change. The _meaning_ of the domain should not. But Asterion
explicitly rejects abstraction layers whose only justification is speculative
portability.

---

### Invariant 5 — Human decisions override automated decisions

Automation proposes. Humans decide.

When an automated decision and a curated human decision conflict, the human
decision is authoritative. Human curation is a defining property of Asterion,
not a fallback.

---

### Invariant 6 — Every fact carries provenance

Every fact in Asterion must be traceable to its origin.

Provenance includes, where applicable:

- original source
- source location and timestamp
- extraction run
- model used
- confidence score
- human reviewer and approval history

A fact without provenance is considered **untrustworthy**. Provenance is
append-only: it records what happened, and is never silently rewritten.

This invariant is the architectural expression of Asterion's purpose — a
_curated_ knowledge platform is only as valuable as its ability to answer
"where did this come from, and who vouched for it?" Provenance is also
**domain-agnostic**: it lives in Core, not in any Domain Pack.

---

### Invariant 7 — Core is closed for modification, open for extension

**New domains must be addable without modifications to Asterion Core.**

Adding a new domain should require only new Domain Pack material — ontologies,
canonicalization rules, validation rules, and domain-specific extraction logic.
It must not require changing the core platform.

The test, when adding a domain forces a change to Core:

1. either the abstraction is **incorrect** (fix the boundary), or
2. the concept genuinely belongs in **Core** (promote it deliberately, with an
   ADR if it touches an invariant).

This invariant is held with the discipline of
[Anti-Goal 7](#anti-goal-7--premature-generalization): it states the _intended_
boundary, which is validated by real domains over time — not a license to build
speculative extensibility ahead of need.

---

## Cross-Domain Ground Truths

The following principles are reaffirmed and apply **across all domains**. They
are not new with the multi-domain vision; they are restated here to make clear
they are domain-independent.

- **Event-driven architecture from Day 0.** Meaningful transitions emit domain
  events (Invariant 2; Engineering Style §3). This does not mandate Kafka —
  in-process eventing is event-driven too (see Architectural Status).
- **Onion / hexagonal architecture; ports and adapters.** Adopted as
  **dependency direction points inward** (see Architectural Layers, Invariant
  3, Invariant 4) — calibrated by Engineering Style §9: boundaries, not
  internal abstraction ceremony.
- **Domain-first design.** The domain model leads; infrastructure follows
  (Invariant 4).
- **Strong bounded contexts.** Each Domain Pack is a bounded context (see
  Asterion Core and Domain Packs).
- **Infrastructure independence.** Business concepts do not depend on
  infrastructure concepts (Invariant 4).
- **Provenance as a first-class concern** (Invariant 6).
- **Spec-driven development.** Design before implementation (Engineering Style
  §1).
- **Incremental evolution over premature abstraction.** Anti-Goal 5 and
  Anti-Goal 7.

> These principles were intentionally selected because they are fundamental
> system-design principles rather than horology-specific implementation
> details. That is exactly why Asterion can serve multiple domains.

---

## Architectural Anti-Goals

Asterion intentionally avoids the following. None of these contradict adopting
infrastructure that correctly models the domain (see
[Architectural Status](#architectural-status)); they reject infrastructure and
abstractions adopted _speculatively_.

### Anti-Goal 1 — Premature microservices

Asterion is not a microservices platform. Services are extracted only when
operational pressure justifies it, not on principle.

### Anti-Goal 2 — Fully autonomous knowledge extraction

Asterion is not intended to operate without human oversight. Human curation is
fundamental (see Invariant 5).

### Anti-Goal 3 — Infrastructure purity

Pragmatism beats purity. A simple solution that works is preferred over an
elegant one that few understand.

### Anti-Goal 4 — Speculative distributed complexity

Distributed-systems complexity is introduced when it correctly models the
domain or solves a concrete problem — never for its own sake. Complexity must be
_intentional_, not aspirational.

### Anti-Goal 5 — Rewrite-driven development

Systems evolve incrementally. Large rewrites are treated as failures of
architecture, not as routine renewal.

### Anti-Goal 6 — Speculative vendor-neutrality

Infrastructure choices (Temporal, ClickHouse, and others) are deliberate. We do
not build portability layers to hedge migrations that are not planned. We accept
pragmatic coupling, and isolate a dependency behind an adapter only where there
is clear, present value (see Invariant 4).

### Anti-Goal 7 — Premature generalization

Asterion is a domain-agnostic engine by _design intent_, but it is built using
**horology as the primary proving ground**. Abstractions are extracted only
after they have been observed repeatedly across real domains — not invented
ahead of need.

> One example is an implementation.
>
> Two examples are a coincidence.
>
> Three examples suggest an abstraction.

The Core/Domain-Pack boundary (Invariant 7) is the _target_ shape. Where it is
not yet proven by multiple domains, prefer implementing concretely in the
horology pack and promoting to Core only once a second and third domain reveal
the genuine abstraction. Resist building a "universal knowledge platform"
before real domain experience earns it.

---

## Architectural Status

Asterion does not adopt a generic "earn complexity only at scale" doctrine. The
governing architectural principle is:

> **Use the simplest architecture that correctly models the problem domain.**

Complexity is acceptable when it is:

- intentional,
- understood,
- actively used,
- aligned with domain requirements, and
- non-speculative.

To keep this document honest about reality, each major architectural component
and capability carries a **status**. This axis is **descriptive, not
prescriptive** — it communicates what exists today, what is actively being
introduced, and what remains future intent. It does not veto domain-driven
choices.

Statuses: `Adopted` · `Adopting` · `Planned` · `Not currently planned`.

| Component / Capability       | Status                | Role / Justification                                                                                                                                                                                                                         |
| ---------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Postgres                     | Adopted               | Canonical entity / relational truth (Invariant 1).                                                                                                                                                                                           |
| Temporal                     | Adopting              | Durable, retry-heavy, human-in-the-loop workflow orchestration for the ingestion pipeline. Foundational: long-running curated workflows are intrinsic to Asterion's domain.                                                                  |
| ClickHouse                   | Adopting              | **ROLE TO BE CONFIRMED** — state which it primarily serves: ingestion observability, raw-extraction landing, analytical exploration, or knowledge-graph analytics. Document the chosen role here so future readers understand why it exists. |
| Blob storage                 | Planned               | Canonical store for large binary artifacts (Invariant 1).                                                                                                                                                                                    |
| LLM adapter                  | Adopting              | Knowledge extraction, accessed through an explicit adapter (Invariant 3).                                                                                                                                                                    |
| Kafka                        | Not currently planned | Event distribution is currently handled in-process / via Temporal. Adoption would require stronger, concrete justification.                                                                                                                  |
| **Horology Domain Pack**     | Adopted               | The first and only implemented domain; the proving ground for Core.                                                                                                                                                                          |
| **Core / Domain-Pack split** | Adopting              | Design intent (Invariant 7). Being validated through horology. Abstractions promoted to Core only as further domains earn them (Anti-Goal 7).                                                                                                |
| **Additional Domain Packs**  | Planned               | Cars, perfumes, books, eyewear, etc. None implemented yet.                                                                                                                                                                                   |

Status is expected to change as the system is built. Updating a status is a
documentation act and does **not** require an ADR; changing an invariant or
principle does.

---

## Governance

Changes to any **invariant** or **principle** in this document require an
**Architecture Decision Record (ADR)**.

- **Location:** `docs/adr/`
- **Naming:** `ADR-NNNN-short-title.md` (zero-padded, sequential)
- **Length:** intentionally lightweight — one page maximum.

ADRs are _more_ valuable for a solo developer, not less: they preserve the
reasoning you will otherwise forget. Keep them short.

### ADR template

```markdown
# ADR-NNNN — <title>

Status: Proposed | Accepted | Superseded by ADR-XXXX
Date: YYYY-MM-DD

## Context

What forces are at play? What problem or pressure prompted this decision?

## Decision

What we decided, stated plainly.

## Consequences

What becomes easier, what becomes harder, what we are now committed to.
```

Intentional technical debt is tracked separately, in `docs/technical-debt.md`
(see [Engineering Style §11](./asterion-style.md)).
