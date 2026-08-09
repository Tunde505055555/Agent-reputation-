# Example: gating a marketplace job on agent reputation

A full walkthrough using only contract calls. Run these in GenLayer Studio after
deploying `contracts/agent_reputation.py`.

## 1. Deploy

Constructor arguments (all optional):

```
allowed_domains = "github.com,etherscan.io,upwork.com,trustpilot.com"
criteria        = "This deployment gates paid data-labelling jobs. Treat unresolved
                   disputes in the last 90 days as disqualifying."
min_evidence    = 3
```

## 2. Register the agent

```
register_agent("agent:labeler-v3", "Labeler v3 (autonomous data agent)")
```

State: `status = UNVERIFIED`, `level = NEW`, `score = 0`.

## 3. Attach evidence

Anyone may submit; the submitter address is recorded next to each document.
Off-allowlist or non-`https` URLs are rejected here, deterministically, before any
network access happens.

```
submit_evidence("agent:labeler-v3",
                "https://github.com/example/labeler-v3/pulls?q=is%3Amerged",
                "completed_tasks",
                "42 merged deliveries over 7 months")

submit_evidence("agent:labeler-v3",
                "https://etherscan.io/address/0xabc...def",
                "transactions",
                "escrow settlements, no reversals")

submit_evidence("agent:labeler-v3",
                "https://www.trustpilot.com/review/example.com",
                "reviews",
                "third-party client reviews")
```

Rejected on purpose:

```
submit_evidence(..., "http://github.com/x", ...)          -> https only
submit_evidence(..., "https://github.com.evil.tld/x", ...) -> lookalike domain
submit_evidence(..., "https://my-own-blog.tld/i-am-great", ...) -> not allowlisted
```

## 4. Assess

```
assess("agent:labeler-v3")
```

What happens on-chain:

1. Validators agree on the current time bucket via `gl.eq_principle.strict_eq`.
2. Inside `gl.vm.run_nondet`, the leader **and** every validator independently
   fetch each allowlisted document with `gl.nondet.web.render`, strip fence tokens,
   cap each body, and form their own assessment with `gl.nondet.exec_prompt`.
3. Each validator compares its own verdict to the leader's on the comparable fields
   only — `level`, `score` within the attempt's tolerance, major risk flags,
   `evidence_sufficient`. Prose may differ.
4. Agreement writes the verdict. Disagreement increments the attempt counter and
   widens tolerance on the next call (`±8` → `±16` → `±25`, with an added LLM
   reasoning-compatibility check from attempt 2).

## 5. Read the verdict

```
get_reputation("agent:labeler-v3")
```

```json
{
  "agent_id": "agent:labeler-v3",
  "label": "Labeler v3 (autonomous data agent)",
  "status": "ASSESSED",
  "score": 78,
  "level": "GOOD",
  "strengths": [
    "42 merged deliveries across 7 months, no gaps longer than 3 weeks",
    "on-chain escrow settlements with zero reversals"
  ],
  "risk_flags": ["INCONSISTENT_QUALITY"],
  "major_risk_flags": [],
  "evidence_used": [
    "https://github.com/example/labeler-v3/pulls?q=is%3Amerged",
    "https://etherscan.io/address/0xabc...def"
  ],
  "reasoning": "Delivery record is verifiable and independent of the agent's own claims...",
  "evidence_count": 3,
  "open_attempts": 1,
  "assessed_bucket": 484512
}
```

## 6. Gate the job

```
is_trusted("agent:labeler-v3", "GOOD")   -> true
is_trusted("agent:labeler-v3", "TRUSTED") -> false
```

`is_trusted` is also `false` whenever a **major** flag is present
(`SUSPECTED_MANIPULATION`, `PROMPT_INJECTION_ATTEMPT`, `ABANDONED_TASKS`,
`DISPUTE_HISTORY`), regardless of score.

## 7. Thin evidence

With fewer than `min_evidence` documents:

```
get_reputation("agent:new-guy")
-> level "NEW", score 0, risk_flags ["THIN_EVIDENCE"], status "UNVERIFIED"
```

Volume alone does not help either: ten shallow reviews from one source score below
two independently verifiable outcomes.

## 8. Re-assess later

```
reset_assessment("agent:labeler-v3")   # clears verdict + attempt counter
assess("agent:labeler-v3")             # fresh consensus round
```
