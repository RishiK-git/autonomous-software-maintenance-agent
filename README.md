# Autonomous Software Maintenance Agent

An agentic software engineering system that autonomously identifies and resolves routine maintenance tasks in GitHub repositories.

## Goal

Build an AI agent capable of operating on a software repository rather than simply answering questions about it.

The agent should be able to:

1. Inspect a repository.
2. Identify a maintenance task.
3. Investigate the relevant code and documentation.
4. Plan a change.
5. Modify the repository.
6. Run tests and validation.
7. Recover from failures when possible.
8. Produce a reviewable diff.
9. Optionally create a GitHub pull request.

The system should prioritize safe, verifiable changes over unrestricted autonomy.

## Initial MVP

The first version should focus on a narrow maintenance workflow:

```text
Repository
    ↓
Maintenance scan
    ↓
Identify actionable issue
    ↓
Agent investigation
    ↓
Plan
    ↓
Modify repository
    ↓
Run tests
    ↓
Review diff
    ↓
Success / Failure
```

A successful MVP does not need to support every type of software maintenance.

## Phase 1 Scope (Current)

The chosen task for Phase 1 is **security vulnerability scanning**.

Decisions specific to this phase:

* **Report only, not fix.** The agent detects and explains vulnerabilities and files GitHub issues. It does not modify the target repository or open pull requests. Fix + PR mode is a later phase.
* **No exploit/PoC execution.** Detection is via LLM code review and dependency (SCA) scanning only — no agent-written exploit code is executed anywhere. Sandboxed PoC verification is a later phase.
* **Claude Agent SDK** provides the agent loop and read-only exploration tools (`Read`/`Grep`/`Glob`), rather than a hand-rolled tool layer.
* **CLI only**, invoked by external triggers (git hook, CI, cron/systemd) — no server, no webhook receiver yet.
* **GitHub issues are the persistence layer** for this phase — no database yet.

See `docs/roadmap.md` for the full build order and `docs/architecture.md` for what's deferred and why.

### Running scans

The CLI itself doesn't schedule anything — it's invoked by external triggers, matching the layered model of a cheap scan on every change plus a deeper periodic sweep:

* `maintenance-agent scan-diff --repo <path> --base <ref> --head <ref>` — fast, LLM-only, scoped to a diff. Triggered by:
  * `scripts/pre-push-scan-hook.sh` — local git hook, advisory only (never blocks a push), install with `cp scripts/pre-push-scan-hook.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push`
  * `.github/workflows/security-scan.yml` — real CI workflow, runs on every PR to `main` and files GitHub issues (needs an `ANTHROPIC_API_KEY` repo secret)
* `maintenance-agent scan-full --repo <path> --github-repo OWNER/REPO` — deeper, LLM review + SCA dependency scan. Triggered by:
  * `scripts/full-scan.cron` — example crontab entry for a periodic sweep (e.g. nightly)

Both subcommands print findings to stdout by default; add `--github-repo OWNER/REPO` to file them as GitHub issues instead (deduped against currently-open ones).

## Potential Maintenance Tasks

Possible future tasks include:

* Dependency updates
* Documentation fixes
* Broken tests
* Simple bug fixes
* Stale TODO detection
* Code quality issues
* Configuration updates
* Security-related maintenance ← **chosen for Phase 1** (see above)

The first implementation should choose a single task type rather than attempting all of these.

## Technology Direction

Potential technologies:

* Python — used from Phase 1
* Claude Agent SDK — used from Phase 1 (agent loop + built-in read-only tools)
* GitHub API — used from Phase 1 (issue filing, via a personal access token)
* pytest — used from Phase 1
* FastAPI — deferred until a webhook-driven (push-based) trigger is needed instead of external scheduling
* GitHub Webhooks — deferred with FastAPI
* Redis — deferred until concurrent/background job load is real (multi-repo scanning, webhook bursts)
* PostgreSQL — deferred until run history/analytics beyond filed GitHub issues is needed
* Docker — deferred until sandboxed PoC/exploit execution or isolated test-running is added
* AWS — deferred until an always-on hosted service (vs. a CLI run by cron/CI) is needed

Not every technology needs to be used in the MVP.

Each technology should solve a real architectural problem.

## High-Level Architecture

```text
                    GitHub
                       │
                 Repository Event
                       │
                       ▼
                ┌─────────────┐
                │   FastAPI   │
                │ Webhook API │
                └──────┬──────┘
                       │
                       ▼
                  Job Queue
                       │
                       ▼
                ┌─────────────┐
                │    Agent    │
                └──────┬──────┘
                       │
              ┌────────┼─────────┐
              ▼        ▼         ▼
           GitHub    Search    Test Runner
            API       Tools        │
              │        │           │
              └────────┼───────────┘
                       ▼
                  LLM Reasoning
                       │
                       ▼
                 Repository
                       │
                       ▼
                  Validation
                       │
                       ▼
                Reviewable Diff
```

This architecture is intentionally conceptual. Do not implement every component before the MVP is proven.

## Design Goals

### Autonomous

The system should be capable of deciding what information it needs and which tools to use.

### Safe

The agent should operate inside controlled boundaries and validate modifications before they are considered successful.

### Observable

Agent runs should record useful information such as:

* Task
* Tools used
* Agent iterations
* Test results
* Errors
* Final outcome
* Execution time

### Measurable

The project should eventually support evaluation of:

* Task success rate
* Test pass rate
* Agent iterations
* Runtime
* LLM token usage
* Cost
* Failure modes

## Non-Goals

The initial project is not intended to be:

* A general-purpose coding agent
* A replacement for a developer
* A multi-agent framework
* An enterprise-scale deployment
* A generic chatbot

The focus is on building a constrained autonomous software maintenance workflow.

## Development

See:

* `CLAUDE.md` for development instructions.
* `docs/architecture.md` for architectural decisions.
* `docs/roadmap.md` for planned work.
