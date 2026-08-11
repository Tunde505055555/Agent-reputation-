# AgentReputation — a GenLayer Intelligent Contract

A contract-only repository. No frontend, no server, no AI gateway, no simulator.

```
contracts/agent_reputation.py   the Intelligent Contract (GenVM v0.2.16)
docs/CONSENSUS.md               the consensus design in detail
tests/                          unit tests over the pure, security-critical helpers
examples/                       marketplace walkthrough + consumer-contract snippet
scripts/deploy.py               headless deploy via genlayer-py
```

## WHAT THIS IS

A reusable **reputation primitive** for AI agents. Anyone registers an agent and
attaches *evidence URLs* — completed tasks, failed tasks, disputes, reviews,
on-chain transactions, audits. `assess(agent_id)` makes the network fetch that
evidence and produce a structured verdict:

- `score` (0–100)
- `level` — `NEW` | `LOW` | `FAIR` | `GOOD` | `TRUSTED`
- `strengths`
- `risk_flags` (canonical codes, not prose)
- `evidence_used` (the URLs actually read)
- `reasoning` (short)

`is_trusted(agent_id, min_level)` is the cheap read other contracts gate on.

## WHY IT IS REUSABLE

Nothing about a vertical is hardcoded. The evidence allowlist, minimum evidence
count, and the extra assessment criteria are constructor parameters, so the same
code serves agent registries, agent-to-agent payment gating, freelance
marketplaces, DAO grant committees, and RWA/NFT counterparty checks. The
consensus core (`_assess_with_consensus`) can be lifted into another contract
with only the storage layer swapped.

## CONSENSUS PATTERNS DEMONSTRATED

| Pattern | Where |
| --- | --- |
| `gl.eq_principle.strict_eq` | agreeing on a coarse wall-clock time bucket |
| `gl.vm.run_nondet` | the custom tiered validator (leader + independent validators) |
| `gl.nondet.web.render` | untrusted evidence fetch, fenced and length-capped |
| `gl.nondet.exec_prompt` | validator-local reasoning + an LLM-judged reasoning comparison on escalated attempts |

Validators do **not** need identical prose. Agreement is required only on the
comparable decision fields: `evidence_sufficient`, `level`, `score` (within the
attempt's tolerance), the set of *major* risk flags, and which documents were
readable.

### GenVM lint compliance

Every non-deterministic call (`gl.nondet.web.render`, `gl.nondet.exec_prompt`)
appears **directly inside** the closures handed to `gl.vm.run_nondet`. GenVM's
lint rejects nondet calls reached indirectly through shared helper functions, so
`leader_fn` and `validator_fn` each inline their own fetch + prompt sequence and
call only deterministic helpers (`_as_doc`, `_readable_urls`,
`_normalize_assessment`, `_unwrap_leader`) around them. No `gl.nondet` reference
exists anywhere outside an equivalence-principle block.

## State design

```
allowed_domains : DynArray[str]        config: evidence hosts (https only)
criteria        : str                  config: trusted extra guidance
min_evidence    : u8                   config: docs required for any rating > NEW
deployer        : Address
agents          : TreeMap[str, Agent]
agent_ids       : DynArray[str]

Agent    = agent_id, label, owner, status, level, score, strengths,
           risk_flags, reasoning, evidence_used, attempts,
           assessed_bucket, evidence: DynArray[Evidence]
Evidence = url, kind, note, submitter, bucket
```

Statuses: `UNVERIFIED` (never assessed or insufficient evidence), `ASSESSED`,
`STALE` (new evidence arrived after the last assessment).

## Public API

| Method | Kind | Purpose |
| --- | --- | --- |
| `register_agent(agent_id, label)` | write | register; ids are unique |
| `submit_evidence(agent_id, url, kind, note)` | write | attach allowlisted https evidence; dedup + caps |
| `assess(agent_id)` | write | run the consensus assessment |
| `reset_assessment(agent_id)` | write | clear a stuck escalation ladder |
| `get_reputation(agent_id)` | view | the structured verdict |
| `get_evidence(agent_id)` | view | submitted evidence |
| `is_trusted(agent_id, min_level="GOOD")` | view | gate for other contracts |
| `list_agents()` | view | registered ids |
| `config()` | view | allowlist, thresholds, flag codes, levels |

## Handling failure

- **Insufficient evidence** — below `min_evidence`, `assess` answers on-chain
  with `NEW` / `THIN_EVIDENCE` and spends no LLM call. If validators judge
  evidence insufficient, the level is forced to `NEW` and the score capped.
- **Consensus disagreement** — the attempt fails; `attempts` is already
  incremented, so the next `assess` runs one rung up the tolerance ladder
  (±8 → ±16 → ±25, plus the reasoning-compatibility check from attempt 2). After
  `MAX_ATTEMPTS` the contract refuses and asks for stronger evidence;
  `reset_assessment` clears the ladder.
- **Hostile evidence** — https-only + domain allowlist checked before any fetch
  and again inside the sandbox, no credentials or explicit ports in the host,
  fence markers stripped from bodies, bodies capped, and the model is told the
  fenced region is untrusted data. Injection attempts are graded, not obeyed
  (`PROMPT_INJECTION_ATTEMPT`).
- **Not review-count** — the rubric caps volume, requires
  `SELF_REPORTED_ONLY` for agent-authored claims, and prefers the less
  flattering reading when sources contradict.

## Deploy on GenLayer Studio

1. Studio → Contracts → new file, paste `contracts/agent_reputation.py`.
   Keep the first two lines (`# v0.2.16` and the `Depends` pragma) intact and first.
2. Deploy. All constructor args are optional:
   `allowed_domains=""` (falls back to a default allowlist), `criteria=""`,
   `min_evidence=2`.
3. `register_agent` → `submit_evidence` (≥ `min_evidence` items) → `assess` →
   `get_reputation`.

Headless: `python scripts/deploy.py` (see the file for env vars).

## Tests

```
pip install -r requirements-dev.txt
pytest -q
```

The tests import the contract with a small SDK stub, so no GenVM is needed. They
cover the security-critical pure helpers: https-only host parsing, allowlist
lookalike domains, fence-token stripping, risk-flag whitelisting, score
normalization, and the thin-evidence clamp.

## License

MIT — see `LICENSE`.
