"""Data-only stub of the parent accelerator's ``utilities/orchestrator``.

DEC-001 / DEC-004 exclude chat orchestration from ``doc-ingest-pipeline``.
The parent ``ConfigHelper`` and ``EnvHelper`` still reference the
``OrchestrationStrategy`` enum and ``OrchestrationSettings`` data container
purely for **config schema compatibility** (the ``default.json`` config and
PostgreSQL fallback branch both name the strategy). No orchestration code,
LLM clients, plugins, or tools from the parent ``orchestrator/`` package are
ported -- only the inert enum + dataclass below.

Ports just the data definitions from
``code/backend/batch/utilities/orchestrator/__init__.py`` and
``orchestration_strategy.py`` at parent commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``.
"""

from .orchestration_strategy import OrchestrationStrategy


class OrchestrationSettings:
    def __init__(self, orchestration: dict):
        self.strategy = OrchestrationStrategy(orchestration["strategy"])


__all__ = ["OrchestrationSettings", "OrchestrationStrategy"]
