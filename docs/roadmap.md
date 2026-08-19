# Roadmap

## Phase 0 — Project Setup

* [x] Initialize repository
* [x] Create Python project structure
* [x] Configure environment variables
* [x] Add pytest
* [x] Establish basic logging
* [x] Create initial README and architecture documentation

## Phase 1 — Security Scanning Agent (chosen task, report-only)

Goal: prove that an LLM agent can find real security vulnerabilities in a repository and report them safely, without ever modifying the repository.

Chosen task: **security vulnerability scanning**. Report only — no fix, no PR, no exploit/PoC execution (see `docs/architecture.md` for the full reasoning).

### Phase 0 — Project Setup
* [x] Initialize repository
* [x] Create Python project structure
* [x] Configure environment variables (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, model, cost cap)
* [x] Add pytest
* [x] Establish basic logging (tool calls, turns, token usage per run)

### Phase 1a — Minimal scan loop
* [x] `Finding` / `ScanResult` structured output models
* [x] Claude Agent SDK query wrapper: read-only tools (`Read`/`Grep`/`Glob`), system prompt, `max_turns` cap
* [x] CLI prints findings to stdout against a local repo path
* [ ] Demo: run against a repo with a planted vulnerability, see it detected  _(pending: needs a live run with a funded API key)_

### Phase 1b — SCA (dependency) integration
* [x] Subprocess wrapper for a dependency/CVE scanner (e.g. `osv-scanner`), graceful skip if not installed
* [x] Merge SCA findings with LLM findings
* [ ] Demo: a repo with a known-vulnerable dependency gets flagged  _(pending: needs a live run with a funded API key)_

### Phase 1c — GitHub issue filing
* [x] GitHub REST client (PAT auth): create issue, list open issues
* [x] Dedup: don't re-file a finding already open
* [ ] Demo: findings become real GitHub issues; re-running doesn't duplicate them  _(pending: needs a live run with a funded API key)_

### Phase 1d — Diff-scan mode
* [x] Git diff extraction between two refs
* [x] `scan-diff` subcommand scoped to changed files/hunks only
* [ ] Demo: a PR-sized diff gets a fast, cheap scan  _(pending: needs a live run with a funded API key)_

### Phase 1e — Trigger glue
* [x] Example git hook script invoking `scan-diff`
* [x] Example GitHub Actions workflow for CI-triggered diff scans
* [x] Example cron/systemd timer invoking `scan-full` on a schedule

### Success Criteria

The agent can:

```text
Receive scan request (diff or full repo)
    ↓
Inspect repository (read-only)
    ↓
Identify vulnerabilities (LLM review + SCA)
    ↓
Produce structured findings
    ↓
Dedup against open issues
    ↓
File GitHub issue(s)
```

## Phase 2 — Reliable Agent Loop *(deferred — applies once fix+PR mode exists)*

Not needed for report-only scanning; retry/repair and diff-capture only matter once the agent modifies code. Revisit when fix+PR mode is added.

* [ ] Feed test failures back to the agent
* [ ] Implement retry/repair loop
* [ ] Capture git diff
* [ ] Add workspace safety restrictions
* [ ] Add timeout handling
* [ ] Add tool-call logging *(the logging itself is already part of Phase 1 — this item is about repair-loop-specific logging)*
* [ ] Add structured run results

## Phase 3 — Extended GitHub Integration *(partially absorbed into Phase 1c; remainder deferred)*

Issue creation, dedup, and PAT auth are built in Phase 1c. Everything below is deferred until fix+PR mode is added:

* [ ] Pull request retrieval
* [ ] Branch creation
* [ ] Commit changes
* [ ] Create pull request
* [ ] Add GitHub webhook support (deferred with FastAPI — see `docs/architecture.md`)

## Phase 4 — Background Processing

Only introduce this phase when synchronous processing becomes a real limitation.

* [ ] Add Redis
* [ ] Create analysis jobs
* [ ] Create worker process
* [ ] Add job status
* [ ] Add retry handling
* [ ] Support concurrent jobs

## Phase 5 — Persistence

* [ ] Add PostgreSQL
* [ ] Store repositories
* [ ] Store maintenance tasks
* [ ] Store agent runs
* [ ] Store tool executions
* [ ] Store validation results
* [ ] Add run history

## Phase 6 — Retrieval Improvements

* [ ] Measure repository context requirements
* [ ] Improve code search
* [ ] Add dependency-aware retrieval
* [ ] Evaluate whether embeddings are necessary
* [ ] Add vector retrieval only if justified

## Phase 7 — Evaluation

Build a benchmark of known maintenance tasks.

Measure:

* [ ] Task success rate
* [ ] Test pass rate
* [ ] False positive rate
* [ ] Average iterations
* [ ] Runtime
* [ ] Token usage
* [ ] Cost
* [ ] Failure categories

Compare changes to the agent against the benchmark rather than relying only on anecdotal demos.

## Phase 8 — Deployment

Potential deployment:

```text
AWS
├── API service
├── Worker service
├── PostgreSQL
└── Redis
```

Tasks:

* [ ] Containerize services
* [ ] Deploy API
* [ ] Deploy worker
* [ ] Configure PostgreSQL
* [ ] Configure Redis
* [ ] Add secrets management
* [ ] Add logging/monitoring
* [ ] Document deployment

## Phase 9 — Expansion

Potential future capabilities:

* [ ] Dependency updates
* [ ] Documentation maintenance
* [ ] Test repair
* [ ] Security maintenance
* [ ] Code quality maintenance
* [ ] Scheduled repository scans
* [ ] Automatic pull requests

## Scope Rule

Do not advance to the next phase simply because it is listed here.

A phase should be implemented when the previous phase demonstrates a real need for it.

The primary goal is a **small, reliable autonomous system**, not maximum feature count.
