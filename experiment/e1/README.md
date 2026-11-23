# E1 - Developer model tier (tests ADR-006): de-confounded protocol

Status: PLANNED, not executed. The original E1 attempts are recorded in
`experiment/variants.md` and report section 3 as incomplete and
confounded (harness and model changed together; availability failures
dominated). This directory defines the smallest comparison that would
actually answer the ADR-006 question, plus the analysis script that turns
the run artifacts into the report's side-by-side table. Nothing here
fabricates the missing runs: cells stay PENDING until both variants have
completed under the controls below.

## Question

Does the Developer's model tier change outcomes when the stage is
mechanically checked, or is the cheaper tier good enough?

## Controls (the confounds that invalidated the first attempt)

1. Same client revision. Record the exact workflow commit SHA for every
   trial; any client fix between arms voids the comparison for those
   trials.
2. Same prompts. Record the SHA-256 of the rendered Developer system
   prompt and task prompt per trial.
3. Same issues. `experiment/issues/issue-3.md` (search limit) and
   `experiment/issues/issue-4.md` (get default), the two feature issues,
   comparable in size. Bug issues are excluded: a bug fix's diff shape
   differs from a feature's and would mix effects.
4. Recorded responding model, not requested model. The client must log
   the model that actually answered (fallbacks included) per call; an arm
   is labeled by what responded, and any trial with a cross-tier fallback
   is marked contaminated, not silently counted.
5. Serial execution, provider-state paired. Trials alternate A/B so a
   provider outage window hits both arms roughly equally; a trial that
   fails on provider 5xx is recorded as an availability failure, not a
   model-quality data point.
6. Repetitions. At least 2 completed trials per arm per issue. One trial
   per condition cannot separate model effect from prompt luck.

## Arms

- A (control, the ADR-006 choice): Developer = gemini-3.5-flash.
- B (treatment): Developer = gemini-3.5-flash-lite, everything else
  identical (same issues, prompts, checks, budgets, fix-cycle cap).

## Measurements per trial

- Build pass on first implementation (stage 3 check on first attempt).
- Tests pass within fix cycle 1 (stage 4 history in `state.json`).
- Fix cycles used (`fix_cycles` in `state.json`).
- Tokens and calls attributed to the trial only after verifying a clean initial counter and no carried usage. Otherwise report a cumulative snapshot, not a trial total.
- Wall time (first to last event timestamp in `state.json`).
- Completion (reached review vs stopped, with the stop reason).

## Decision rule (unchanged from variants.md)

If lite matches flash on pass outcomes across the completed trials,
ADR-006 is amended to move the Developer down a tier (cost win); if it
does not, the ADR stands with measured evidence. A trial set that cannot
complete under the controls is reported as a negative operational result,
not silently replaced by another availability probe (the E1b mistake this
protocol exists to avoid repeating).

## Analysis status

No controlled trial comparison is published yet. Before a result can be
counted, independently verify the same issue, client revision and prompt
hashes across arms, actual responding model, clean initial counters,
and the repetition requirement above. Merely pointing an analyzer at
two branch snapshots does not establish these controls. Cumulative usage
must not be labeled trial usage or a lower bound without lineage proof.
