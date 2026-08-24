# Consensus design

## Why prose can't be the unit of agreement

Two validators reading the same evidence will never produce the same sentences.
So the assessment is reduced, deterministically, to comparable decision fields
before anything is compared:

```
evidence_sufficient : bool          exact match required
level               : 0..4          derived from the score, never independent;
                                    exact on attempt 1, ±1 band once escalated
score               : 0..100        within the attempt's tolerance, and always on
                                    the same side of the is_trusted threshold
risk_flags          : canonical codes; the MAJOR subset must match exactly
readable            : sorted URLs actually fetched with a non-empty body
```

`_normalize_assessment` does the reduction: clamps the score, drops any flag code
the model invented, and — if `evidence_sufficient=false` — caps the score into
the NEW band (≤19) and adds `THIN_EVIDENCE`. Thin evidence can therefore never
become a good score, no matter what the model says.

## Level is derived, never asserted

The model's `level` string is advisory. `_level_from_score` maps the accepted
score through `SCORE_BANDS` (0-19 NEW, 20-39 LOW, 40-59 FAIR, 60-79 GOOD, 80-100
TRUSTED) and that band is the level of record — used when storing the assessment
and re-derived inside `is_trusted`. A FAIR-band score can no longer be stored as
GOOD. The one thing a model's claim can do is *lower* the outcome: if it claims a
level below its own score's band, the score is pulled down to that band's ceiling.

Validators enforce this too: a leader payload whose `level` is not the band of its
own `score` is rejected outright.

## Tolerance may not flip the trust decision

The score tolerance and the escalated ±1 level slack exist to absorb honest
judgement differences, not to move an agent across the gate other contracts read.
So on every attempt the validator requires

```
_meets_trust_threshold(leader.score) == _meets_trust_threshold(mine.score)
```

where the threshold is `TRUST_THRESHOLD_LEVEL` (GOOD), the default `is_trusted`
minimum. A leader at 62 and a validator at 55 disagree even at ±16 tolerance,
because one would gate the job open and the other shut.

## The tiered tolerance ladder

`attempts` is stored per agent, so escalation is on-chain consensus policy rather
than an off-chain retry loop.

| Attempt | Score tolerance | Level slack | Reasoning compared |
| --- | --- | --- | --- |
| 1 | ±8 | 0 | no |
| 2 | ±16 | ±1 | yes |
| 3 | ±25 | ±1 | yes |

From attempt 2 the validator additionally asks the model whether the leader's
reasoning and its own are *compatible* — same overall read of reliability and
risk, wording irrelevant. Contradictory conclusions about the same facts are not
compatible, so widening the numeric tolerance does not let a disagreement slip
through. A successful consensus resets `attempts` to 0; exceeding
`MAX_ATTEMPTS` makes `assess` refuse until better evidence or
`reset_assessment` arrives.

## What is never negotiable

- `evidence_sufficient` — a mismatch is an immediate disagreement.
- The **major** flags: `SUSPECTED_MANIPULATION`, `PROMPT_INJECTION_ATTEMPT`,
  `DISPUTE_HISTORY`, `ABANDONED_TASKS`, `UNVERIFIABLE_EVIDENCE`. Escalation
  never softens a red flag.
- Evidence coverage — validators must have read the same document set, so a
  validator that silently failed to fetch cannot ratify the leader.

## Time bucketing

Recency matters to the rubric, but `time.time()` differs per node. `_now_bucket`
reads the clock inside `gl.eq_principle.strict_eq` and divides by
`TIME_BUCKET_SECONDS` (1h), so every validator sees the identical integer "now"
and the prompt stays reproducible.

## GenVM lint: nondet must be lexically inside the block

GenVM's lint tracks non-deterministic calls syntactically. A call reached through
a shared helper (`_fetch_all()` invoked by both closures) is reported as
*unreachable from an equivalence-principle block* and the contract is rejected.

Therefore `leader_fn` and `validator_fn` each contain their own fetch loop and
their own `gl.nondet.exec_prompt` call verbatim; the reasoning-comparison prompt
also sits inline in `validator_fn`. Everything factored out — `_as_doc`,
`_readable_urls`, `_extract_json`, `_normalize_assessment`, `_unwrap_leader`,
`_build_prompt` — is pure and deterministic. The only other nondet context is the
`strict_eq` clock read.

`_unwrap_leader` tolerates the VM's result wrapper: it pulls the payload out of
the returned object, requires valid JSON, and treats a rollback or malformed
result as disagreement rather than as consent.

## Untrusted evidence handling

1. `submit_evidence` accepts `https://` only, rejects hosts containing `@` or
   `:`, and requires an exact or subdomain match against the allowlist.
2. The allowlist is re-checked inside the sandbox before each fetch, so a config
   change between submission and assessment cannot be exploited.
3. Bodies have the fence markers replaced with `[redacted]` and are truncated to
   `MAX_BODY_CHARS`; at most `MAX_EVIDENCE_FETCHED` documents are read per
   assessment, bounding cost.
4. The prompt states that everything between the fences is untrusted data to be
   judged and that submitter notes are claims. A document trying to instruct the
   assessor earns `PROMPT_INJECTION_ATTEMPT`.
5. Only canonical flag codes survive `_clean_flags`, so a manipulated document
   cannot introduce a flag vocabulary of its own.
