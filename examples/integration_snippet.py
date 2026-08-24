# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
Consumer snippet: another Intelligent Contract gating work on AgentReputation.

Nothing here is part of the reputation primitive; it shows the intended coupling
— a cheap deterministic view call, no LLM cost on the consumer side.
"""

from genlayer import *


class AgentJobBoard(gl.Contract):
    reputation: Address
    min_level: str
    jobs: TreeMap[str, str]  # job_id -> assigned agent_id

    def __init__(self, reputation: Address, min_level: str = "GOOD"):
        self.reputation = reputation
        self.min_level = min_level

    @gl.public.write
    def assign(self, job_id: str, agent_id: str) -> None:
        ok = gl.get_contract_at(self.reputation).view().is_trusted(
            agent_id, self.min_level
        )
        if not ok:
            raise Exception("agent is not trusted enough for this job")
        self.jobs[job_id] = agent_id

    @gl.public.view
    def assignee(self, job_id: str) -> str:
        return self.jobs.get(job_id, "")
