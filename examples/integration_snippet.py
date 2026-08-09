# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""
Integration example (illustrative, not part of the primitive).

How another Intelligent Contract consumes AgentReputation as a trust gate. The
reputation contract is called as a plain read, so the consumer pays nothing for the
LLM work — the assessment already happened in its own consensus round.
"""

from genlayer import *


class JobBoard(gl.Contract):
    reputation: Address
    required_level: str
    assignments: TreeMap[str, str]  # job_id -> agent_id

    def __init__(self, reputation: str, required_level: str = "GOOD"):
        self.reputation = Address(reputation)
        self.required_level = required_level

    @gl.public.write
    def assign(self, job_id: str, agent_id: str) -> None:
        assert job_id not in self.assignments, "job already assigned"

        # Read-only view call into the reputation primitive.
        ok = gl.get_contract_at(self.reputation).view().is_trusted(
            agent_id, self.required_level
        )
        assert ok, f"agent {agent_id} is not trusted at level {self.required_level}"

        self.assignments[job_id] = agent_id

    @gl.public.view
    def assignee(self, job_id: str) -> str:
        return self.assignments.get(job_id, "")
