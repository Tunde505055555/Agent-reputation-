# Marketplace flow

A freelance/agent marketplace gating jobs on reputation. All calls are ordinary
contract calls — Studio UI, `genlayer-py`, or another contract.

## 1. Deploy

```python
AgentReputation(
    allowed_domains="github.com,upwork.com,etherscan.io",
    criteria="Prioritise delivery on paid engagements over unpaid demos.",
    min_evidence=3,
)
```

## 2. Register the agent

```python
register_agent("agent:solver-7", "Solver-7 (autonomous data-cleaning agent)")
```

## 3. Attach evidence (anyone may submit; submissions are claims)

```python
submit_evidence("agent:solver-7", "https://github.com/acme/etl/pull/412",
                "task", "Delivered ETL migration, merged by maintainer")
submit_evidence("agent:solver-7", "https://www.upwork.com/freelancers/~01abc",
                "review", "12 contracts, 4.9 average")
submit_evidence("agent:solver-7", "https://etherscan.io/tx/0xabc...",
                "tx", "Escrow released on completion")
```

Rejected at submit time: non-https URLs, hosts outside the allowlist, duplicate
URLs, and anything past `MAX_EVIDENCE_PER_AGENT`.

## 4. Assess under consensus

```python
assess("agent:solver-7")
```

Leader and validators each fetch the documents and reason independently; the
network agrees on level, score (within the attempt's tolerance), major risk
flags, and evidence sufficiency.

## 5. Read the verdict

```json
{
  "agent_id": "agent:solver-7",
  "status": "ASSESSED",
  "score": 72,
  "level": "GOOD",
  "strengths": [
    "Merged upstream work verified by a third-party repository",
    "Escrow released on-chain, consistent with the claimed outcome"
  ],
  "risk_flags": ["INCONSISTENT_QUALITY"],
  "major_risk_flags": [],
  "evidence_used": [
    "https://github.com/acme/etl/pull/412",
    "https://etherscan.io/tx/0xabc..."
  ],
  "reasoning": "Two independently verifiable outcomes ...",
  "evidence_count": 3,
  "open_attempts": 0,
  "assessed_bucket": 484512
}
```

## 6. Gate the job

```python
if is_trusted("agent:solver-7", "GOOD"):
    award_contract(...)
```

`is_trusted` is false unless the status is `ASSESSED` and no major risk flag is
present.

## Failure paths

- Fewer than `min_evidence` items → `NEW` / `THIN_EVIDENCE`, no LLM call spent.
- Validators disagree → the attempt fails; call `assess` again to run one rung up
  the tolerance ladder. After the last rung, add stronger evidence (or call
  `reset_assessment`).
- New evidence after an assessment → status becomes `STALE`; re-run `assess`.
