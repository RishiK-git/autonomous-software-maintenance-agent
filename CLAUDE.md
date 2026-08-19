# Claude Code Instructions

## Project

This project is an autonomous software maintenance agent.

The long-term goal is to build an agent that can inspect software repositories, identify maintenance issues, investigate them, make safe changes, validate those changes, and optionally create a GitHub pull request.

The project should demonstrate strong software engineering, backend systems, agentic orchestration, and practical use of LLMs.

### Phase 1

The chosen Phase 1 task is security vulnerability scanning: report only (file GitHub issues, do not modify the target repo or open PRs), no exploit/PoC execution, built on the Claude Agent SDK rather than a hand-rolled tool layer. See `docs/roadmap.md` for the build order and `docs/architecture.md` for the current architecture and what's deferred.

## Core Principles

### 1. Explain before coding

Before making non-trivial changes:

1. Explain what you intend to change.
2. Explain why the change is needed.
3. Identify the files that will be modified.
4. Mention any important tradeoffs.
5. Wait for approval when the change affects architecture.

For small, obvious fixes, proceed without unnecessary discussion.

### 2. Don't break existing functionality

Before modifying existing code:

* Understand how the current implementation works.
* Prefer small, incremental changes.
* Do not rewrite working systems unnecessarily.
* Run relevant tests after changes.
* Do not remove existing functionality without approval.

### 3. Ask before changing architecture

Do not introduce major infrastructure or architectural changes without discussing them first.

Examples:

* Adding Redis
* Adding PostgreSQL
* Introducing background workers
* Changing the API architecture
* Introducing a new framework
* Changing the LLM provider
* Adding cloud infrastructure
* Changing the agent execution model

Explain the motivation and alternatives before implementing.

### 4. Avoid unnecessary dependencies

Do not add a dependency simply because it is popular.

Before introducing a library, consider:

* Can the standard library solve this?
* Is the dependency actually necessary?
* What complexity does it introduce?
* Does it meaningfully improve the project?

## Agent Design

The agent should be:

* Tool-driven
* Observable
* Iterative
* Constrained
* Testable
* Deterministic where possible

Avoid creating an autonomous loop where the LLM can continuously modify the system without limits.

Agent execution should have explicit:

* Tool permissions
* Iteration limits
* Time limits
* Failure handling
* Validation steps

## Safety

Repository modifications must be treated as potentially destructive.

Prefer:

1. Inspect
2. Plan
3. Modify isolated working state
4. Run validation
5. Review diff
6. Apply/submit changes

Never allow arbitrary destructive shell commands without explicit approval.

The agent should not modify files outside its designated workspace.

## Code Quality

Prefer:

* Clear names
* Small functions
* Strong typing
* Explicit error handling
* Modular components
* Dependency injection where useful
* Testable business logic

Avoid:

* Huge functions
* Global mutable state
* Hard-coded credentials
* Duplicated logic
* Premature abstractions

## Python

Use modern Python.

Prefer:

* Type hints
* Pydantic for structured data
* async/await when I/O concurrency benefits from it
* pytest for testing
* environment variables for configuration

Follow normal Python formatting and linting conventions.

## API

If FastAPI is used:

* Keep routes thin.
* Put business logic in services.
* Validate request/response models with Pydantic.
* Handle errors explicitly.
* Keep infrastructure concerns separate from application logic.

## LLM Usage

Do not rely on the LLM to perform tasks that deterministic code can perform reliably.

Use the LLM for:

* Reasoning
* Classification
* Planning
* Code analysis
* Deciding which tools to use

Use deterministic code for:

* File operations
* Git operations
* Test execution
* Parsing structured data
* Queue management
* Validation

Prefer structured outputs over parsing free-form LLM responses.

## Testing

Every significant feature should have tests.

Prioritize tests for:

* Agent state transitions
* Tool behavior
* Repository analysis
* Failure handling
* Structured LLM outputs
* API endpoints

When possible, test agent behavior using deterministic fixtures rather than real repositories.

## Development Workflow

For each feature:

1. Understand the existing implementation.
2. Explain the proposed approach.
3. Implement the smallest useful version.
4. Run tests.
5. Review the implementation.
6. Refactor only when necessary.
7. Update documentation when behavior or architecture changes.

## Scope Control

The goal is to build a strong MVP, not an enterprise platform.

Do not add:

* Multi-agent orchestration unless clearly justified
* Kubernetes
* Complex microservices
* Excessive cloud infrastructure
* Elaborate frontend systems
* Unnecessary abstractions

If a simpler implementation demonstrates the concept, prefer the simpler implementation.

## Important

The project should remain understandable to a software engineer reading the repository for the first time.

Optimize for:

**Correctness → Simplicity → Testability → Performance → Scale**

Do not optimize for technology count.
