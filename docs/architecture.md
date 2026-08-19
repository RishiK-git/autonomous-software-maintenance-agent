# Architecture

## Current Status

This document describes the intended architecture.

The architecture should evolve as the MVP is implemented. Do not build infrastructure solely because it appears in this document.

**Phase 1 (current)** narrows this to security vulnerability scanning, report-only: the agent explores a target repo read-only, produces structured findings, and files GitHub issues. It does not modify the repo, open PRs, or execute exploit/PoC code. Sections below describe the full intended system; each notes its Phase 1 status.

## Core System

The system consists of several conceptual components:

```text
GitHub
   ↓
Event/API Layer
   ↓
Task Management
   ↓
Agent
   ↓
Repository Tools
   ↓
Validation
   ↓
Result
```

## 1. GitHub Integration

The system should eventually integrate with GitHub through:

* GitHub REST API
* GitHub webhooks
* Pull request information
* Repository contents
* Issues
* Commits
* Branches

The GitHub integration should be isolated from the agent logic.

The agent should interact with GitHub through explicit tools rather than directly managing HTTP requests throughout the codebase.

## 2. Agent

The agent is responsible for reasoning about the maintenance task.

Potential capabilities:

* Inspect repository structure
* Search source code
* Read files
* Read documentation
* Inspect Git history
* Determine relevant files
* Form a plan
* Modify files
* Run tests
* Interpret failures
* Iterate

The agent should have a limited set of explicit tools.

## 3. Tool Layer

**Phase 1**: uses the Claude Agent SDK's built-in tools (`Read`, `Grep`, `Glob`) for read-only repository exploration, plus a narrowly scoped `Bash` allowance used only to invoke the SCA scanner subprocess (not arbitrary shell access). This was chosen over hand-rolling equivalents (`list_files`, `search_code`, `read_file`, ...) to avoid writing and maintaining that plumbing — the SDK's tools give the same "explore whatever the agent deems necessary" autonomy with less code. `write_file`, `git_diff` (as a repo-modifying concept), and `run_tests` are not needed in Phase 1 since the agent never modifies the target repo.

Tools available to the agent still have:

* Explicit inputs
* Explicit outputs
* Error handling
* Permission boundaries (Phase 1: read-only + one scoped subprocess allowance, no write access at all)

The agent's structured findings — not a tool call — are what triggers any external action (filing a GitHub issue). Filing, deduplication, and all GitHub API calls are deterministic Python, not something the LLM invokes directly.

## 4. Repository Isolation

**Phase 1**: not applicable in the "modification" sense — the agent operates read-only against the target repo (a local path or a shallow clone) and never writes to it. Isolation matters here only in the sense that the agent's tool permissions have no write access at all, which is a stronger guarantee than a writable-but-isolated workspace.

The full future flow, for when fix+PR mode is added:

```text
Agent
  ↓
Temporary workspace
  ↓
Repository clone
  ↓
Agent modifications
  ↓
Tests
  ↓
Diff
```

Docker may eventually be used to isolate test execution, and separately to sandbox any agent-written PoC/exploit code (no network, resource/time limits) if exploit verification is added. Neither is needed in Phase 1.

## 5. Task Queue

**Deferred.** No queue is needed while each scan is a single CLI invocation that runs to completion. A queue may be introduced when analysis becomes asynchronous — e.g. scanning many repos concurrently or absorbing a burst of webhook-triggered scans.

Potential architecture:

```text
FastAPI
   ↓
Redis
   ↓
Worker
   ↓
Agent
```

Redis should only be introduced if background jobs or concurrent processing justify it.

## 6. Database

**Deferred.** GitHub issues are the persistence layer for Phase 1: dedup works by checking currently-open issues via the GitHub API, and a filed issue *is* the record of a finding. No separate database is needed until richer run history/analytics (beyond what's visible in filed issues) becomes a real requirement.

PostgreSQL may eventually be used to persist:

* Repositories
* Tasks
* Agent runs
* Run status
* Tool executions
* Test results
* Final outcomes

Do not use PostgreSQL merely for configuration that could live elsewhere.

## 7. Retrieval

Repository retrieval should prevent unnecessarily sending an entire repository to the LLM.

Potential retrieval methods:

* Filename filtering
* Code search
* Dependency analysis
* Symbol search
* Embeddings/vector search if conventional retrieval becomes insufficient

RAG should be introduced only when repository context becomes a demonstrated bottleneck.

## 8. Validation

A modification should not be considered successful merely because the LLM says it succeeded. **Phase 1's equivalent**: a finding should not be considered real merely because the LLM says it is. Since there's no diff/tests to check (report-only), findings are constrained via structured output (Pydantic `Finding` model — category, severity, confidence, evidence) rather than free-form prose, and dependency findings are cross-referenced against the SCA scanner's own output rather than taken from LLM judgment alone.

Once fix+PR mode is added, validation should include:

1. Git diff inspection
2. Formatting/linting where appropriate
3. Tests
4. Additional task-specific checks

The validation result should be returned to the agent so it can attempt recovery.

## 9. Agent Loop

Conceptually (full future loop, once fix+PR mode exists):

```text
Task
 ↓
Plan
 ↓
Inspect
 ↓
Act
 ↓
Validate
 ↓
Success?
 ├── Yes → Finish
 └── No  → Diagnose → Act
```

**Phase 1** has no "Act" (write) step — it's read-only:

```text
Task (scan repo or diff)
 ↓
Inspect (Read/Grep/Glob + SCA subprocess)
 ↓
Reason → structured Finding(s)
 ↓
Dedup against open GitHub issues
 ↓
File issue(s)
```

The loop must have explicit limits.

Potential limits:

* Maximum iterations (Phase 1: SDK `max_turns` cap, config-driven)
* Maximum runtime
* Maximum tool calls
* Maximum token/cost budget (Phase 1: accumulated usage logged per run against a configurable soft ceiling — see `docs/roadmap.md`)

## Architectural Principles

### Prefer deterministic operations

Use code for operations that do not require reasoning.

### Keep the agent constrained

More autonomy is not automatically better.

### Make failures visible

Every important operation should produce useful diagnostics.

### Design for evaluation

Agent performance should eventually be measurable rather than judged only by demonstrations.
