# AgentReputation — a GenLayer Intelligent Contract

A **reusable AI-agent reputation primitive** for GenLayer. Not an app, not a frontend:
one contract that any protocol can embed to answer a single question —

> *Can this agent be trusted with this job?*

Built for **GenVM `v0.2.16`** and deployable as-is in **GenLayer Studio**.

```
contracts/agent_reputation.py     <- the entire primitive (single file, no imports beyond the SDK)
```

---

## WHAT THIS IS

Anyone may register an AI agent and attach **evidence URLs** — completed tasks, failed
tasks, disputes, reviews, on-chain transactions, audits. Calling `assess(agent_id)`
makes the **network** fetch and read that evidence and produce a structured reputation
verdict. There is no privileged backend and no single LLM call deciding the outcome.

The result:

| field | meaning |
| --- | --- |
| `score` | 0–100 |
| `level` | `NEW`, `LOW`, `FAIR`, `GOOD`, `TRUSTED` |
| `strengths` | short, evidence-grounded positives |
| `risk_flags` | machine-comparable flag codes (see below) |
| `evidence_used` | exactly which documents were actually read |
| `reasoning` | a few sentences of justification |
| `status` | `UNVERIFIED`, `ASSESSED`, `STALE` |

Reputation is **not review count**. Volume is capped in the rubric; quality,
consistency, recency and source credibility dominate. Thin evidence can never become a
good score — below `min_evidence`, or when validators judge the evidence insufficient,
the verdict stays `NEW` / `UNVERIFIED`.

## WHY IT IS REUSABLE

The contract hardcodes no domain and no business logic. The evidence allowlist, the
minimum evidence count and the extra rubric guidance are **constructor parameters**, so
the same code serves:

- autonomous agent registries and agent-to-agent payment gating
- freelance / task marketplaces
- DAO grant and delegate committees
- counterparty checks for RWA and NFT flows

Other contracts integrate through one cheap call:

```python
if reputation.is_trusted(agent_id, "GOOD"):
    assign_job(agent_id)
```

`is_trusted` returns `False` unless the agent is `ASSESSED`, carries **no major risk
flag**, and meets the requested level. The consensus core (`_assess_with_consensus`) is
written so it can be lifted into another contract with the storage layer swapped out.

## CONSENSUS PATTERNS DEMONSTRATED

This is the point of the contract. The LLM is the easy part; the consensus design
around it is the contribution.

1. **Comparable fields, free reasoning.** A verdict is reduced to `level`, `score`,
   `risk_flags` (codes, not prose) and `evidence_sufficient`. Validators may disagree in
   wording but must agree on the *decision*.
2. **Custom validator via `gl.vm.run_nondet`.** Each validator independently fetches the
   evidence and forms its own assessment, then compares it against the leader's.
3. **Tiered tolerance ladder.** Attempt 1 is strict and cheap (`±8` score). Each
   re-assessment widens tolerance one band (`±16`, `±25`) and adds an **LLM-judged
   comparison of the reasoning itself**. Escalation is part of the on-chain consensus
   rule, not an off-chain retry loop. After `MAX_ATTEMPTS` the contract records
   disagreement instead of forcing a fake verdict.
4. **`gl.eq_principle.strict_eq` for time.** Wall-clock is bucketed into 1h windows so
   independent validators agree on "now" without a coordinator.
5. **`gl.nondet.web.render` for untrusted evidence**, fenced and length-capped.

### Consensus comparison rule

```
agree  ==  level equal
       and |score_leader - score_mine| <= TOLERANCE_LADDER[attempt-1]
       and major risk flags equal (as a set)
       and evidence_sufficient equal
       and (attempt == 1 or reasoning judged compatible by an LLM)
```

## Hostile-input handling

External evidence is treated as an attack surface, not as data:

- **Deterministic domain allowlist** checked *before* any fetch. Off-allowlist URLs are
  rejected at submission time, in ordinary Python — never by the model.
- **Fenced untrusted region.** Fetched bodies are wrapped in
  `<<<UNTRUSTED_EVIDENCE_BEGIN/END>>>` markers, existing fence tokens in the body are
  stripped, and the prompt states the region is data to be *analysed*, never instructions
  to be obeyed.
- **Caps:** `MAX_BODY_CHARS = 6000` per document, `MAX_EVIDENCE_FETCHED = 8` per
  assessment, `MAX_EVIDENCE_PER_AGENT = 24`, `MAX_URL_LEN`, `MAX_NOTE_LEN`.
- **`PROMPT_INJECTION_ATTEMPT` and `SUSPECTED_MANIPULATION` are risk flags.** A page that
  tries to steer the assessor lowers the agent's reputation instead of raising it.
- Self-published or unverifiable sources earn `SELF_REPORTED_ONLY`; recycled/duplicate
  praise earns `INCONSISTENT_QUALITY` or `SUSPECTED_MANIPULATION`.

Risk flag vocabulary:

```
SELF_REPORTED_ONLY   DISPUTE_HISTORY        ABANDONED_TASKS
INCONSISTENT_QUALITY IDENTITY_UNCLEAR       SUSPECTED_MANIPULATION
PROMPT_INJECTION_ATTEMPT  THIN_EVIDENCE     STALE_ACTIVITY
```

Major flags (any one of which blocks `is_trusted`): `SUSPECTED_MANIPULATION`,
`PROMPT_INJECTION_ATTEMPT`, `ABANDONED_TASKS`, `DISPUTE_HISTORY`.

---

## State design

```
allowed_domains : DynArray[str]          # constructor allowlist
criteria        : str                    # extra trusted rubric guidance
min_evidence    : u8
deployer        : Address

agents          : TreeMap[str, Agent]    # agent_id -> record
agent_ids       : DynArray[str]          # enumeration

Agent  = agent_id, label, status, score:u8, level:u8, strengths, risk_flags,
         evidence_used, reasoning, attempts:u8, assessed_bucket:u256,
         evidence: DynArray[Evidence]
Evidence = url, kind, note, submitter: Address, bucket: u256
```

Storage is flat and string-packed on purpose: multi-value fields are newline or
comma joined so the Studio schema reflector stays happy and views return plain JSON.

## Public API

| method | kind | description |
| --- | --- | --- |
| `register_agent(agent_id, label)` | write | create a registry entry (`UNVERIFIED`) |
| `submit_evidence(agent_id, url, kind, note)` | write | attach allowlisted evidence |
| `assess(agent_id)` | write | run the consensus assessment, store the verdict |
| `reset_assessment(agent_id)` | write | clear a verdict / attempt counter for re-run |
| `get_reputation(agent_id)` | view | full structured verdict |
| `get_evidence(agent_id)` | view | evidence list with submitters |
| `is_trusted(agent_id, min_level="GOOD")` | view | integration gate |
| `list_agents()` | view | all registered agent ids |
| `config()` | view | allowlist, thresholds, ladder, flag & level vocabulary |

Constructor:

```python
AgentReputation(
    allowed_domains = "github.com,gitlab.com,etherscan.io,...",  # comma separated, defaulted
    criteria        = "",                                        # extra rubric guidance
    min_evidence    = 2,
)
```

Deploys with **zero arguments** — the default allowlist is used when the field is empty.

## Failure handling

| situation | behaviour |
| --- | --- |
| unknown `agent_id` | reverts with a clear message |
| duplicate registration | reverts |
| URL off the allowlist / malformed / too long | rejected at `submit_evidence` |
| fewer than `min_evidence` documents | `assess` records `NEW` + `THIN_EVIDENCE`, no score inflation |
| every fetch fails | `NEW`, `evidence_sufficient = false` |
| validators disagree at attempt *n* | tolerance widens, attempt counter increments |
| disagreement after `MAX_ATTEMPTS` | no verdict written; state stays `UNVERIFIED`/`STALE` |

## Deploying in GenLayer Studio

1. Open [studio.genlayer.com](https://studio.genlayer.com) (or a local Studio).
2. **Contracts → new file**, paste `contracts/agent_reputation.py`.
3. Keep the first two lines intact — the version tag and `Depends` pragma must be the
   first lines of the file or the schema will not load:
   ```python
   # v0.2.16
   # { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
   ```
4. **Deploy** with no constructor arguments (or supply your own allowlist).
5. Walk through `examples/marketplace_flow.md`.

`scripts/deploy.py` does the same thing headlessly with `genlayer-py`.

## Repository layout

```
contracts/agent_reputation.py    the Intelligent Contract
tests/test_pure_helpers.py       pure-function tests (no GenVM needed)
examples/marketplace_flow.md     end-to-end call walkthrough
examples/integration_snippet.py  how another contract consumes is_trusted
scripts/deploy.py                headless deploy via genlayer-py
docs/CONSENSUS.md                the consensus rule in detail
```

No frontend, no server, no AI gateway, no simulator — contracts, tests, docs and
deployment tooling only.

## License

MIT.
