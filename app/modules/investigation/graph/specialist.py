from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ToolBudgetExceeded(RuntimeError):
    pass


@dataclass
class ToolBudget:
    max_calls: int
    agent: str
    calls: list[dict[str, Any]] = field(default_factory=list)

    def remaining(self) -> int:
        return self.max_calls - len(self.calls)

    def record(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Record a tool call or raise ``ToolBudgetExceeded`` when at ``max_calls``."""
        if len(self.calls) >= self.max_calls:
            raise ToolBudgetExceeded(f"{self.agent} exceeded {self.max_calls} tool calls")
        record = {"agent": self.agent, "tool": tool, "params": params}
        self.calls.append(record)
        return record
