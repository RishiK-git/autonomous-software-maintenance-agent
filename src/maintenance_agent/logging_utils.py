"""Structured per-run logging: tool calls, turns, token usage, cost estimate.

This is plain observability plumbing (stdlib logging + a small accumulator),
not findings logic — findings live in findings.py.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("maintenance_agent")

# Rough per-million-token pricing for cost estimation. Not billing-accurate;
# good enough to enforce the soft per-run cost ceiling in config.py.
_PRICING_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    # model: (input, output)
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}
_DEFAULT_PRICING = (3.00, 15.00)


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@dataclass
class RunLog:
    """Accumulates observability data for a single scan run.

    The Claude Agent SDK's ResultMessage reports an authoritative
    ``total_cost_usd`` for the run — prefer that (via finalize_from_usage)
    over the token-based estimate below, which exists only as a fallback
    for display before the run completes or if the SDK omits cost.
    """

    model: str
    started_at: float = field(default_factory=time.monotonic)
    turns_used: int = 0
    tool_calls: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    findings_count: int = 0
    _authoritative_cost_usd: float | None = field(default=None, repr=False)

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls.append(tool_name)
        logger.debug("tool call: %s", tool_name)

    def record_turn(self) -> None:
        self.turns_used += 1

    def finalize_from_usage(
        self,
        *,
        num_turns: int,
        usage: dict[str, object] | None,
        total_cost_usd: float | None,
    ) -> None:
        """Record the final SDK-reported turn count, token usage, and cost."""
        self.turns_used = num_turns
        if usage:
            self.input_tokens = int(usage.get("input_tokens") or 0)
            self.output_tokens = int(usage.get("output_tokens") or 0)
            self.cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)
        self._authoritative_cost_usd = total_cost_usd

    def _estimated_cost_usd(self) -> float:
        input_price, output_price = _PRICING_PER_MTOK_USD.get(self.model, _DEFAULT_PRICING)
        return (self.input_tokens / 1_000_000) * input_price + (
            self.output_tokens / 1_000_000
        ) * output_price

    def cost_usd(self) -> tuple[float, bool]:
        """Returns (cost, is_estimated)."""
        if self._authoritative_cost_usd is not None:
            return self._authoritative_cost_usd, False
        return self._estimated_cost_usd(), True

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def summary(self) -> dict[str, object]:
        cost, is_estimated = self.cost_usd()
        return {
            "model": self.model,
            "turns_used": self.turns_used,
            "tool_calls": len(self.tool_calls),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cost_usd": round(cost, 4),
            "cost_is_estimated": is_estimated,
            "findings_count": self.findings_count,
            "elapsed_seconds": round(self.elapsed_seconds(), 2),
        }

    def log_summary(self) -> None:
        logger.info("run summary: %s", self.summary())
