

# Project Overview

Innovation-Research-Development-AI-System is a long-term cognitive infrastructure project focused on building:

- distributed cognitive runtimes
- autonomous research orchestration
- persistent semantic reasoning
- multi-agent scientific intelligence
- adaptive memory systems

This is NOT a chatbot project.

The system is designed as a persistent cognitive operating infrastructure capable of:
- orchestrating research agents
- maintaining long-term semantic memory
- evolving reasoning structures
- coordinating distributed cognition
- supporting autonomous scientific workflows

Primary optimization goals:
- scalability
- modular cognition
- reasoning traceability
- persistent memory
- runtime observability
- long-term maintainability

Avoid:
- shallow abstractions
- unnecessary framework complexity
- disconnected experimental modules
- monolithic architecture
- hype-driven implementations

Prefer:
- composable systems
- observable runtimes
- explicit reasoning flows
- modular infrastructure
- production-oriented architecture


# Tech Stack

Core Stack:
- Python 3.12+
- FastAPI
- Pydantic v2
- AsyncIO
- Docker
- Docker Compose

Memory Infrastructure:
- Qdrant (vector memory)
- Neo4j (knowledge graph)
- PostgreSQL (structured persistence)
- Redis (runtime synchronization)

AI / Cognition:
- OpenAI-compatible inference APIs
- Sentence Transformers
- LangChain only when necessary
- Custom orchestration layers preferred

Observability:
- Prometheus
- OpenTelemetry
- Structured logging

Testing:
- pytest
- pytest-asyncio

Do NOT introduce:
- Django
- Flask
- TensorFlow monoliths
- unnecessary frontend frameworks
- tightly coupled architectures
- hidden magic abstractions

Avoid:
- synchronous runtime patterns
- global mutable state
- blocking I/O inside cognition flows


# Architecture

Core Architecture:

src/
├── agents/              → cognitive agents
├── runtime/             → execution runtime and scheduling
├── memory/              → persistent cognition layers
├── reasoning/           → reasoning trace systems
├── orchestration/       → distributed coordination
├── infrastructure/      → event systems and runtime infrastructure
├── governance/          → policy enforcement and safety
├── telemetry/           → metrics and observability
├── protocols/           → inter-agent communication contracts
├── api/                 → FastAPI endpoints
└── experiments/         → isolated research prototypes

Rules:
- Runtime logic belongs in runtime/
- Persistent memory logic belongs in memory/
- Agent coordination belongs in orchestration/
- Shared runtime infrastructure belongs in infrastructure/
- Safety and validation belong in governance/
- Reasoning lineage belongs in reasoning/

Do not:
- mix orchestration with memory logic
- place business logic inside API routes
- create giant multi-purpose classes
- create hidden dependencies between modules

Prefer:
- composable services
- async-first architecture
- explicit interfaces
- isolated cognition modules

New subsystem?
Create:
src/{domain}/

before introducing cross-domain coupling.


# Coding Conventions

General Rules:
- Python type hints required everywhere
- Avoid `Any` unless justified
- Async-first design
- Prefer composition over inheritance
- Small focused classes
- Explicit dependencies only

Naming:
- snake_case for functions and files
- PascalCase for classes
- descriptive variable names only

Avoid:
- abbreviations
- dead code
- commented-out code blocks
- speculative abstractions
- premature optimization

Limits:
- files ideally under 400 lines
- functions ideally under 50 lines
- classes should have single responsibility

Error Handling:
- never silently swallow exceptions
- raise domain-specific errors when possible
- structured logging only

Comments:
- explain WHY
- do not explain obvious syntax


# Cognitive System Principles

The project must evolve toward:
- persistent cognition
- recursive reasoning
- semantic continuity
- distributed coordination
- autonomous research workflows

The project must NOT drift into:
- generic chatbot frameworks
- prompt-engineering-only systems
- demo-only architectures
- hype abstractions without runtime value

Every major subsystem should improve at least one:
- reasoning persistence
- orchestration scalability
- memory consistency
- runtime observability
- governance enforcement
- adaptive cognition


# Memory Architecture

Memory Layers:
- Vector Memory → Qdrant
- Graph Memory → Neo4j
- Runtime State → Redis
- Structured Persistence → PostgreSQL

Rules:
- cognition should be replayable
- reasoning should be traceable
- semantic state should persist across cycles

Do not:
- store cognition only in RAM
- tightly couple memory providers
- mix runtime cache with long-term memory


# Runtime & Orchestration

Runtime goals:
- distributed execution
- adaptive scheduling
- event-driven cognition
- multi-agent coordination

All runtime systems should support:
- async execution
- cancellation safety
- telemetry hooks
- observability

Avoid:
- blocking operations
- hidden runtime mutations
- recursive runaway execution

Schedulers must:
- support prioritization
- support future distributed scaling
- avoid starvation conditions


# Governance & Safety

Governance is mandatory infrastructure.

All cognition flows should eventually support:
- runtime validation
- reasoning trace inspection
- execution policy enforcement
- safety boundaries
- auditability

Do not:
- bypass governance layers
- disable validation silently
- introduce unrestricted autonomous execution


# Observability

Every critical runtime component should expose:
- metrics
- logs
- execution traces

Telemetry priorities:
- reasoning latency
- event throughput
- agent coordination health
- memory synchronization state
- runtime stability

Prefer:
- structured logs
- traceable execution flows
- measurable cognition


# Testing & Quality

Before marking work complete:
- run tests
- run linting
- verify async correctness
- validate imports
- verify no circular dependencies

Testing Requirements:
- runtime logic requires tests
- orchestration requires async tests
- memory systems require persistence validation
- governance systems require safety validation

Avoid:
- fake placeholder tests
- snapshot-only testing
- untested orchestration logic


# File Placement Rules

New runtime logic:
→ src/runtime/

New memory systems:
→ src/memory/

New reasoning systems:
→ src/reasoning/

New distributed coordination:
→ src/orchestration/

New infrastructure:
→ src/infrastructure/

New governance layers:
→ src/governance/

Experimental prototypes:
→ src/experiments/

Rules:
- prefer extending existing systems
- avoid near-duplicate abstractions
- create reusable infrastructure carefully
- one-off utilities should stay local


# Commands

Environment Setup:
- python -m venv .venv
- source .venv/bin/activate

Install:
- pip install -r requirements.txt

Development:
- uvicorn src.api.main:app --reload

Tests:
- pytest

Async Tests:
- pytest -s

Lint:
- ruff check .

Format:
- ruff format .

Docker:
- docker compose up --build

Future Infrastructure:
- prometheus
- grafana
- qdrant
- neo4j
- redis
- postgres


# Security Rules

Never:
- commit secrets
- commit .env files
- hardcode API keys
- expose internal runtime endpoints publicly
- log sensitive runtime state

All secrets:
- environment variables only

All external model access:
- configurable providers only

Governance rules must NOT be bypassed silently.

Agent autonomy should always:
- remain observable
- remain interruptible
- remain auditable


# Strategic Direction

This project is evolving toward:

Distributed Cognitive Infrastructure
→ Persistent Semantic Runtime
→ Autonomous Scientific Intelligence Platform
→ Cognitive Operating System

Long-term priorities:
1. persistent memory
2. distributed orchestration
3. reasoning traceability
4. governance enforcement
5. adaptive cognition
6. runtime observability
7. scientific autonomy

Do not lose architectural direction.

Every implementation should strengthen:
- cognition persistence
- orchestration capability
- reasoning quality
- infrastructure scalability
- governance integrity
- operational stability


# Documentation Rules

When adding major systems:
- update ROADMAP.md
- update ARCHITECTURE.md
- update PROJECT_UPDATE.md

When architecture changes:
- document rationale
- explain tradeoffs
- explain scalability implications

Avoid undocumented architectural drift.


# Final Philosophy

This repository is not a collection of scripts.

It is an evolving cognitive infrastructure system.

Optimize for:
- longevity
- composability
- observability
- persistence
- scalability
- reasoning integrity

Prefer systems that can evolve for years.
Avoid short-term hacks that damage architecture.