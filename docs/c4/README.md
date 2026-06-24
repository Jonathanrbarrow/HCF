# HCF — C4 Architecture Diagrams

> **This is a living document.** Update it every time the architecture changes before pushing to git.
>
> Last updated: 2026-06-24

## How to Use This Directory

| File | Purpose |
|------|---------|
| [context.md](context.md) | Level 1 — System Context: who uses HCF and what external systems it depends on |
| [containers.md](containers.md) | Level 2 — Container Diagram: deployable units and communication |
| [components.md](components.md) | Level 3 — Component Diagram: internal modules and data flow |
| [decisions.md](decisions.md) | Architecture Decision Records (ADRs) |

## Update Checklist

Before pushing to git, ask:

- [ ] Did I add/remove/rename a module? → Update [components.md](components.md)
- [ ] Did I add/change an external API dependency? → Update [context.md](context.md)
- [ ] Did I add a new deployable unit (service, worker, cache)? → Update [containers.md](containers.md)
- [ ] Did I make an architecture decision worth recording? → Add to [decisions.md](decisions.md)
