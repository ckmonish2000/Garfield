# Garfield

<p align="center">
  <img src="https://github.com/ckmonish2000/Garfield/blob/main/assets/banner.png" alt="entourage Logo" width="250">
</p>

**Code reviews for project managers** - Async-first workflow tool that catches bugs at the requirements stage, not after implementation.

## What is Garfield?

Garfield transforms scattered project communication into unified, AI-reviewed documentation that prevents bugs before code is written.

### The Problem
- PRDs lack critical details
- Context scattered across calls, chats, and threads
- Bugs found after implementation (expensive to fix)
- Remote teams struggle with async collaboration

### The Solution
- **Unified Documents**: Every meeting syncs to a living document
- **Async Collaboration**: Resolve questions via comments, not meetings
- **AI-Powered Reviews**: Catch TRD issues before implementation
- **Seamless Tickets**: Auto-generate Linear tickets from approved TRDs

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/garfield.git
cd garfield

## Core Workflow

```
Meeting → Document → PRD (async review) → TRD → AI Analysis → Tickets
```

1. **Meeting Sync**: Google Calendar meetings auto-create documents
2. **PRD Development**: Team collaborates async with semantic highlights
3. **TRD Creation**: Engineers write technical requirements
4. **AI Review**: Agent analyzes TRD against codebase during editing pauses
5. **Ticket Generation**: Approved TRDs break down into Linear tickets

## Key Features

- **Meeting Dashboard**: All synced meetings in one place
- **Semantic Highlighting**: AI surfaces important context for editors
- **Change Detection**: Monitors document edits (Chokidar-based)
- **Code Cross-Reference**: Analyzes TRDs against repository
- **Linear Integration**: Auto-generates tickets from TRDs

## Why Garfield?

Inspired by [GitLab's async communication handbook](https://handbook.gitlab.com/handbook/company/culture/all-remote/asynchronous/)

> In an era where AI writes 90% of code, catching bugs at the requirements stage is 10x more valuable than debugging later.

## Documentation

- [Vision](docs/vision.md) - Full vision and philosophy
- [Architecture](docs/architecture.md) - System design (coming soon)
- [API Reference](docs/api.md) - Integration details (coming soon)

## Tech Stack (TBD)

## License

MIT License - see [LICENSE](LICENSE) for details

## Status

Early development - not production-ready yet.

---

**Garfield** - Because the best bug fix is the one you prevent.
