from __future__ import annotations

import asyncio

from ..schemas import AgentResponse, PcapMetadata
from .base import AgentSpec, run_agent
from .specs import ALL_AGENTS


async def run_all_agents(meta: PcapMetadata) -> list[AgentResponse]:
    """Run agents concurrently in a thread pool — the LLM SDKs are synchronous."""
    loop = asyncio.get_running_loop()

    async def _one(spec: AgentSpec) -> AgentResponse:
        try:
            return await loop.run_in_executor(None, run_agent, spec, meta)
        except Exception as exc:  # noqa: BLE001
            return AgentResponse(
                agent_name=spec.name,
                severity="medium",
                analysis=f"Agent failed: {exc}",
                findings=[],
                recommendations=[],
            )

    return await asyncio.gather(*(_one(spec) for spec in ALL_AGENTS))
