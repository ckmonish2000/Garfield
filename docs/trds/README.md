# Garfield Improvement Program (GIP)

The **Garfield Improvement Program (GIP)** is the process by which changes to Garfield are proposed, discussed, and tracked. A GIP is a design document that describes a new feature, a significant change to existing behavior, or a cross-cutting concern that affects multiple parts of the system.

GIPs are the primary mechanism for proposing substantial changes, collecting community input on a design, and documenting the decisions that shape Garfield's evolution.

## When to Write a GIP

Not every change needs a GIP. Bug fixes, minor UI tweaks, and small refactors can go through normal pull requests. You **should** write a GIP when proposing:

- **New workflow features** — e.g., a document state machine, async-first meeting flow, or response time SLAs
- **Changes to the async collaboration model** — e.g., new threading behavior, notification strategies, or comment resolution logic
- **New integrations** — e.g., Linear ticket generation, Google Calendar sync, or future third-party connectors
- **AI agent behavior changes** — e.g., how the AI reviews TRDs, suggests templates, or detects sensitive content
- **Cross-cutting concerns** — e.g., privacy model, quality gates, handbook mode, or decision record format
- **Architectural changes** — e.g., document model redesign, new data pipelines, or significant API surface changes

When in doubt, open a lightweight GIP. It's easier to close a short proposal than to untangle a change that was never discussed.

## GIP Format

Each GIP lives in its own folder under `docs/trds/`:

```
docs/trds/
├── README.md              ← this file
├── GIP-01/
│   └── README.md          ← full proposal
├── GIP-02/
│   └── README.md
└── ...
```

A GIP README must include the following sections:

### Required Sections

| Section | Purpose |
|---------|---------|
| **Title** | Short, descriptive name (e.g., "Document State Machine") |
| **Status** | Current lifecycle stage (see below) |
| **Author(s)** | Who is proposing / driving this GIP |
| **Created** | Date the GIP was opened |
| **Summary** | 2–3 sentence overview of the proposal |
| **Motivation** | Why this change is needed — the problem it solves |
| **Proposal** | Detailed description of the proposed design |
| **Alternatives Considered** | Other approaches and why they were rejected |
| **Impact** | What parts of the system are affected |
| **Open Questions** | Unresolved items for discussion |

### Optional Sections

- **Implementation Plan** — phased rollout, milestones, dependencies
- **Metrics** — how success will be measured
- **References** — links to related documents, prior art, or external resources

## GIP Lifecycle

Every GIP moves through a defined set of statuses:

```
Draft → In Review → Approved → Implemented
                  ↘ Rejected
                  ↘ Superseded
```

| Status | Meaning |
|--------|---------|
| **Draft** | Proposal is being written; not yet ready for formal review |
| **In Review** | Open for feedback from stakeholders and the broader team |
| **Approved** | Accepted for implementation; design is finalized |
| **Implemented** | The described changes have been shipped |
| **Rejected** | The proposal was reviewed and declined (with documented reasoning) |
| **Superseded** | Replaced by a newer GIP (link to the successor) |

### Status Transitions

- **Draft → In Review**: Author believes the proposal is complete enough for feedback. Announce in the appropriate channel.
- **In Review → Approved**: Stakeholders have signed off. All open questions are resolved or explicitly deferred.
- **In Review → Rejected**: The proposal does not align with project goals or a better alternative exists. The rejection rationale must be documented.
- **Approved → Implemented**: All described changes are merged and deployed.
- **Any → Superseded**: A newer GIP replaces this one. Add a reference to the successor.

## GIP Index

### Core Platform
*Document model, state machine, templates, quality gates*

| GIP | Title | Status |
|-----|-------|--------|
| — | *No GIPs yet* | — |

### AI & Intelligence
*AI agent behavior, smart suggestions, cross-document analysis*

| GIP | Title | Status |
|-----|-------|--------|
| — | *No GIPs yet* | — |

### Workflow & Integration
*Async workflows, meeting sync, SLAs, handbook mode*

| GIP | Title | Status |
|-----|-------|--------|
| — | *No GIPs yet* | — |

### Connectors & External
*Linear, Google Calendar, and future integrations*

| GIP | Title | Status |
|-----|-------|--------|
| — | *No GIPs yet* | — |

## Contributing a GIP

1. **Create a branch**: `git checkout -b gip/short-description`
2. **Create the folder**: `mkdir docs/trds/GIP-XX` (use the next available number)
3. **Write your proposal**: Copy the required sections above into `docs/trds/GIP-XX/README.md`
4. **Open a PR**: The PR description should link to the GIP and summarize the motivation
5. **Gather feedback**: Move the status to **In Review** and solicit input from relevant stakeholders
6. **Iterate**: Address comments, resolve open questions, and update the proposal
7. **Finalize**: Once approved, update the GIP Index in this file and merge

## Inspiration

The GIP process is modeled after [Wire's WIP (Wire Improvement Program)](https://github.com/niccokunzmann/wips) and similar RFC-style processes used across the industry. It is adapted to Garfield's domain of async-first collaboration, AI-powered document workflows, and integration-driven development.
