# Consensus design

The LLM is not the interesting part of this contract. This is.

## Problem

An assessment produced by a language model is non-deterministic prose. Validators
running the same prompt over the same documents will not produce identical bytes, so a
naive equality principle can never finalise. Loosening equality until it always passes
is worse: it means the network is no longer checking anything.

## Rule

Every assessment is normalised (`_normalize_assessment`) into a small set of
**programmatically comparable decision fields**:

```
level                 one of NEW | LOW | FAIR | GOOD | TRUSTED
score                 0..100
risk_flags            codes from a fixed vocabulary, not free text
evidence_sufficient   bool
```

Free-form output (`strengths`, `reasoning`, `evidence_used`) is retained for humans but
**excluded from equality** except as described below.

A validator accepts the leader's assessment when:

```
level_mine == level_leader
and abs(score_mine - score_leader) <= TOLERANCE_LADDER[attempt - 1]
and major_flags(mine) == major_flags(leader)          # set equality
and evidence_sufficient_mine == evidence_sufficient_leader
and (attempt == 1 or reasoning_compatible(leader, mine))
```

## Tiered tolerance ladder

```
attempt 1   ±8    strict, cheap, no extra LLM call
attempt 2   ±16   plus LLM-judged reasoning compatibility
attempt 3   ±25   plus LLM-judged reasoning compatibility
```

Escalation is written into the consensus rule itself, not delegated to an off-chain
retry loop. Two properties matter:

- **The gates that protect the user never loosen.** `level`, major risk flags and
  `evidence_sufficient` must match exactly at every attempt. Only the numeric score
  band widens — and only within one level.
- **Failure is a valid outcome.** After `MAX_ATTEMPTS` the contract does *not* write a
  verdict. The agent stays `UNVERIFIED` / `STALE` with the attempt count visible.
  Persistent validator disagreement is itself information: the evidence is ambiguous.

## Reasoning compatibility

From attempt 2, a validator additionally asks the model whether the leader's reasoning
and its own are *compatible explanations of the same evidence* — not whether they are
worded alike. This catches the case where two validators land on the same numbers for
contradictory reasons, which strict field equality would silently accept.

## Agreeing on "now"

Recency affects the score, so validators must share a clock. `_now_bucket` reads
wall-clock inside `gl.eq_principle.strict_eq` and floors it into `TIME_BUCKET_SECONDS`
(1 hour) buckets. Strict equality is safe on a coarse bucket and gives every validator
the same notion of "recent" with no coordinator.

## Untrusted evidence in a consensus context

Evidence is fetched by **each validator independently** with `gl.nondet.web.render`, so
a page that serves different content per requester causes disagreement rather than a
quietly poisoned verdict. Before the model sees anything:

1. The domain is checked against the deterministic allowlist (ordinary Python, no model
   involvement) — off-list URLs never reach a fetch.
2. Fence markers occurring inside the fetched body are replaced, so the document cannot
   close the untrusted region and impersonate contract instructions.
3. The body is capped at `MAX_BODY_CHARS`, and at most `MAX_EVIDENCE_FETCHED` documents
   are read per assessment — bounding both cost and injection surface.
4. The prompt states that the fenced region is data to be analysed and that any
   instructions inside it are themselves evidence of manipulation, to be reported as
   `PROMPT_INJECTION_ATTEMPT`.

## Why not just count reviews

Review counts are the cheapest thing on the internet to fabricate, and they are
trivially consistent across validators — which makes a count-based score *look* like
strong consensus while measuring nothing. The rubric therefore caps volume, requires
independent corroboration, caps self-reported claims at 45 with
`SELF_REPORTED_ONLY`, prefers the less flattering reading when sources contradict, and
forces `NEW` whenever validators agree the evidence is insufficient.
