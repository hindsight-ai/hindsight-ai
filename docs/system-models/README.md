# System Models — Hindsight AI

A model-based view of the Hindsight AI system. Where `docs/architecture.md` is a generated module index and the `docs/adr/` collection captures point-in-time decisions, this directory captures the **structural, behavioral, interface, data, and deployment models** that the system actually exhibits today.

These documents are written to support architecture review, refactoring, and onboarding. They are not aspirational — every claim should trace to a file path or migration revision. When code drifts, this directory is wrong; fix it or delete it.

## Views

| File | View | Question it answers |
|---|---|---|
| [00-context.md](00-context.md) | Context | What is the system? Who/what is outside it? |
| [01-structural.md](01-structural.md) | Structural | What modules exist and how do they depend on each other? |
| [02-behavioral.md](02-behavioral.md) | Behavioral | What state machines and key flows govern runtime behavior? |
| [03-interfaces.md](03-interfaces.md) | Interface | What contracts exist at module/process boundaries? |
| [04-data.md](04-data.md) | Data | What is persisted, how is it scoped, how does it migrate? |
| [05-deployment.md](05-deployment.md) | Deployment | What runs where in dev, staging, and prod? |
| [06-smells/](06-smells/) | Smell backlog | Where does the architecture diverge from its intent? |

## Conventions

- Diagrams: Mermaid only (renders natively in GitHub, no build step).
- Source-of-truth links use `path/to/file.py:LINE` or `path/to/file.ts:LINE` so editors can jump.
- ADR cross-references use the `ADR-NNNN` shorthand and link into `docs/adr/`.
- "Smell" entries link to the originating agent finding under `06-smells/findings/`.

## Related documentation

- `docs/architecture.md` — generated module/docstring index
- `docs/adr/` — accepted architecture decisions (numbered)
- `docs/rfcs/` — proposed changes under review
- `docs/authentication_flow.md`, `docs/data-governance-orgs-users.md`, `docs/search-retrieval-overview.md` — domain-specific deep-dives

## Maintenance

This directory was bootstrapped from a one-shot multi-agent analysis. Re-run when:

- A major module is added, removed, or renamed.
- A new persistence layer or external dependency is introduced.
- An ADR materially changes the topology described here.

The smell backlog (`06-smells/`) is a living artifact: close items by linking the PR that fixed them; add new ones as they surface.
