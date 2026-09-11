# ThermoRL

## Project

ThermoRL is a safety-constrained RL scheduler for workload placement
across heterogeneous HPC/data-center cooling zones.

The current research goal is to integrate ThermoRL with the ExaDigiT/RAPS
digital-twin environment and evaluate whether thermal-aware scheduling
provides a measurable advantage over classical schedulers under
high-load / cooling-constrained conditions.

## Architecture

Core principle:

    ExaDigiT / RAPS = environment / digital twin
    ThermoRL = scheduler / controller
    Adapter = boundary between them

Prefer:

    workload
      → RAPS
      → observation
      → ThermoRL adapter
      → ThermoRL
      → scheduling action
      → RAPS
      → next observation

Keep ThermoRL decoupled from RAPS internals where practical.

## ThermoRL Sources

Research paper:
    The ThermoRL paper in the repository defines the intended
    algorithm/formulation.

Existing implementation:
    /home/bipin/thermoRL/thermoRL/thermoRL-new

The existing implementation is a REFERENCE IMPLEMENTATION, NOT
authoritative ground truth. It may contain architectural, algorithmic,
or performance limitations and may be improved or replaced where justified.

Paper specification, existing implementation, and RAPS implementation
must be treated as separate sources of truth.

## Research Discipline

Do not overstate experimental results.

Do not claim hardware lifetime extension from simulation proxies unless
supported by appropriate evidence.

Prefer experiments that can falsify the hypothesis.

For scheduler comparisons, use the same workload and environmental
conditions wherever scientifically appropriate.

Prioritize correctness and reproducibility over impressive demonstrations.

## Repository Navigation

Graphify is the preferred first tool for repository-level discovery,
architecture exploration, and tracing relationships between components.

Use Graphify to identify relevant files/functions before reading large
amounts of source code.

Actual source code remains authoritative for implementation behavior.

## MCPs

Available MCPs:

- Graphify → repository/codebase discovery and relationships
- Context7 → current third-party library/framework/API documentation
- Firecrawl → external web research and web/document crawling
- Token Counter → context/token estimation when useful

Use the appropriate MCP when its information domain is relevant.

Do not use broad repository grep/ripgrep searches when Graphify can answer
the discovery question.

## Development Rules

Do not make large architectural changes without first understanding the
existing implementation.

For substantial changes:

    understand → plan → implement → test → validate

Prefer small, modular, reproducible changes.

Do not modify code when the task is explicitly reconnaissance or planning.