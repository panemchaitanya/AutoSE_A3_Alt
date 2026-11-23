# AutoSE Assignment 3 - Architecting an Agentic SDLC Workflow

**Roll number:** 2025204023
**Repository:** https://github.com/panemchaitanya/AutoSE_A3
(fork of https://github.com/msiemens/tinydb, pinned at `edff96a`)

## 1. Architecture

![Component flow, bounded loops](component.png)

The three views are in `architecture/views/`.

The system turns a labeled issue into a tested, reviewed pull
request. A maintainer starts it by adding the label `autose` to an issue or
commenting `/autose`; the workflow ends after an independent review, and a
human always makes the merge decision.

The component view separates five LLM roles and a scripted release behind
a deterministic controller. `.autose/state.json` on the work branch stores
checkpoints; artifacts preserve prompts/results and failures. Develop-stage
incremental evidence is now committed even on failure. Earlier failures
lost some uncommitted work. The sequence view below follows an actual
recovery, not an idealized uninterrupted run.

Models below are committed defaults, not responding-model claims. Earlier recovery runs requested 3.1-flash-lite but successful responses fell back to 3.5-flash-lite. Both repositories now request 3.5-flash-lite for every role; newer usage records count responding models. The stage map retains the original tier design for comparison.

**Historical committed-default stage map, current roles all request gemini-3.5-flash-lite** (`architecture/views/stage-map.md`): which agent handles each
of the six stages, what inputs it sees, which artifact it writes, and which
check gates the hand-over:

| # | Stage | Agent (model) | Artifact | Check |
| --- | --- | --- | --- | --- |
| 1 | Requirements | SpecWriter (gemini-3.5-flash-lite) | `spec.md` | AC lint + LLM judge: every criterion testable |
| 2 | Design | Designer (gemini-3.5-flash-lite) | `design.md` | Named files exist or marked NEW; names functions |
| 3 | Implementation | Developer (gemini-3.5-flash) | `diff.patch` | Real tinydb source diff + compile + import |
| 4 | Testing | Tester (gemini-3.5-flash-lite) | `test_report.md` | New/full tests pass; baseline regression contrast |
| 5 | Release | scripted, no LLM | `pr.md` + PR | PR open, CI green |
| 6 | Review | Reviewer (gemini-3.5-flash) | `review.md` + PR review | Verdict schema with per-finding evidence |

Prompts carry declared inputs; ordinary agents retain repository read access. The reviewer gets a filtered fresh checkout excluding pipeline reasoning. Code decides transitions. These are prototype controls, not a security sandbox.

### Historical sequence: issue 3 across recovery attempts, boundary flawed

![Observed issue 3 sequence](sequence.png)

Pipeline 45197403640 and historical review 45199274608 are real separate runs, linked in results/runs.md. The reviewer saw assignment README context, so this was NOT fully independent. Corrected-boundary rerun is required. The posted verdict is COMMENT approve, not formal approval. No merge.

## 2. Design decisions

Full ADR text is in `architecture/decisions/`. Superseded decisions remain in history.

| ADR | Decision | Chosen | Main rejected option | Main reason | Status |
| --- | --- | --- | --- | --- | --- |
| 001 | Splitting work | 5 LLM roles + scripted release | One agent for everything | Second perspective can catch missed mistakes | Accepted |
| 002 | Control flow | Deterministic state machine, 2 workflows | LLM orchestrator | Allowed transitions explicit | Accepted |
| 003 | Hand-offs | Declared minimal inputs per agent | Full shared context | Context is influence; reviewer must not see intent | Provisional (local E2 measured) |
| 004 | State | `state.json` + artifacts on the branch | Workflow artifacts only | Survives across runs; branch is the audit trail | Accepted |
| 005 | Tools | Stdlib harness with shell-prefix checks | GitHub MCP server | Small interface, not a sandbox | Superseded by ADR-013 |
| 006 | Models | Flash/lite tier split | Strongest model everywhere | Intended quota/capability tradeoff | Superseded by ADR-012 |
| 007 | Checks | Mechanical decisive, LLM judge advisory veto | LLM judge everywhere | Runnable claims must be run, not believed | Accepted |
| 008 | Reviewer independence | Own workflow, fresh context, no push rights | Same-job "be objective" prompt | Instructions can't remove seen information | Accepted |
| 009 | Safety | Budgets and untrusted-input delimiters | Rely on model refusals | Limits help, arbitrary Python remains unsafe | Superseded by ADR-013 |
| 010 | Triggers | Owner label/comment; write-authorized dispatch | Anyone triggers | Limit starts | Superseded by ADR-011 |
| 011 | Quota queue | One issue workflow at a time, request pacing | Parallel issue calls | Measured 15-RPM bucket shared | Accepted, recovery-tested |
| 012 | Model recovery | Lite overrides | Keep flash primary | Flash transport failures | Provisional; comparison confounded |
| 013 | Safety correction | State shell limits honestly | Treat whitelist as sandbox | Python is arbitrary execution | Accepted limitation |
| 014 | Bounded context |160-line reads, four recent pairs | Unbounded full conversation | Short probes worked; long runs failed | Provisional, no completed trial |
| 015 | A1 adaptation | Restore full mandatory outputs/checks | Compact omission | Reuse cannot silently remove required behavior | Compact rejected, correction unverified |
| 016 | Reviewer input | Exclude assignment README | Leave README in filtered copy | It exposes pipeline reasoning | Corrected, hosted review unverified |

### The three decisions that mattered most

**Deterministic control (ADR-002).** A state machine makes allowed transitions explicit. An LLM planner could still have enforced tool boundaries, but this implementation avoids asking it to choose transitions. With a state machine, the run's *behavior* is reviewable
code and the LLMs' *output* is data at boundaries. It also made the loops
cheap: the implement-test cycle runs inside one job, and only the review
loop pays for a new workflow run. The cost was real - the review workflow
cannot push branch state (contents-read token), so the continuation protocol
(dispatch + gate-side round counting) is more intricate than a prompt
saying "go back to design". The intricacy is the point: it is where the
reviewer's intended input boundary is implemented.

**Minimal inputs (ADR-003), especially the reviewer's exclusion list.**
Passing every prior artifact risks weakening stage separation: the reviewer anchors on the implementer's claims, the designer
re-litigates the raw issue instead of the checked spec, and every stage
pays for every earlier stage's tokens. Experiment E2 tests a context contrast on seeded defects. It does not identify a causal anchoring effect.

**Mechanical checks decide, judges veto (ADR-007).** "All acceptance
criteria are testable" and "the plan names real files" are exactly the kind
of claim an agent asserts confidently and wrongly. Wherever a check could
be executed (compile, import, pytest exit code, path existence, schema), it
is executed, and the agent's own claim is never consulted. The LLM judge
exists only for the two semantic properties, and it can only fail a stage,
never pass one.

## 3. Decision experiments

Design and deviations are in `experiment/variants.md`. E1 remains incomplete and confounded; E2 is a completed local pilot, not a hosted validation.

### E1 - Developer model tier (tests ADR-006)

Original plan: compare flash and lite Developer roles on issues 3 and 4
with identical prompts and harness. That controlled comparison is not yet
complete. The attempts instead exposed availability as a prerequisite.

| Condition | Observed outcome | What it does not show |
| --- | --- | --- |
| Flash Developer, early client | Issues 1-5 stopped on transport timeout/disconnection | Not a measure of code quality |
| Lite with schema/transport fixes | Issue 1 implementation/testing passed; issue 2 later completed on the recovery path | Harness and model changed together |
| Parallel lite issue runs | HTTP 429, provider reported 15 requests/minute | Not evidence of daily quota exhaustion |
| Serial paced recovery | Issue 1 and 2 reached posted independent verdicts across attempts; later calls still returned 503 | Not a guarantee that queueing solves availability |

ADR-006 is superseded by ADR-012: use available lite overrides provisionally,
not because lite was proved a better programmer. ADR-010's concurrency
choice is superseded by ADR-011 after the shared 15-RPM bucket was measured.
These are negative operational findings, not a clean causal model-tier A/B.
A valid quality comparison still needs the same issue, client revision,
prompt, limits and repetitions under both models. Requested defaults,
responding models and fallbacks are reported separately where evidence
exists. The later ORION key route was verified free-tier before use; it is
an account change within the same provider, not a paid fallback.

### E1b - Exploratory matched availability probe (not original E1)

After the original E1 failed to isolate model quality, the identical Developer system prompt, JSON schema, 512-output-token cap, temperature 0.2 and one read-file probe task were submitted serially to two newly verified-free model routes on the same ORION project. This was an exploratory follow-up, not a preregistered replacement or full coding comparison. No fallback was allowed.

| Requested model | HTTP outcome | Measured response seconds | Completed action |
| --- | --- | --- | --- |
| gemini-3.8-flash |503 UNAVAILABLE|0.35|none|
| gemini-4-hydrogen |503 UNAVAILABLE|0.52|none|

Evidence: `results/probes/new-free-model-probes.json`. One trial per route cannot measure general availability, quality or relative speed. The observed result supports bounded backoff rather than further immediate model rotation for this incident. Original E1 quality comparison remains incomplete. No usage metadata was returned for these error responses, so zero charged tokens is not inferred from missing metadata.

### E2 - Reviewer context isolation (tests ADR-003/ADR-008)

Setup: five local seeded PR-style diffs, each carrying one planted defect (`experiment/seeded_prs/`, ground truth in each `expected.json`). Initial behavioral probes were not retained; a reproducible verification script was added and run after E2. All five defect demonstrations passed then. This is post-experiment validation, not a preserved pre-experiment record. The Reviewer role used its system prompt and then-current harness to review each seed twice, locally. Later hosted isolation/schema fixes mean this is not a full validation of the final hosted boundary:

- **A (isolated, the ADR-008 design):** issue + diff + a checkout at the PR
  head. Nothing else.
- **B (context leaked):** A plus an authored pipeline-context block in which
  spec, design, test report and Developer summary all assert the change is
  verified and correct. The stimulus is authored, not captured from a real
  run, because the seeded PRs have no pipeline artifacts; that is a
  limitation, carried into section 6.

All 10 reviews ran on gemini-3.5-flash-lite with the real API key;
transcripts, verdicts and usage are preserved per run.

| Seed | A verdict (isolated) | B verdict (context) | Flipped? |
|------|----------------------|---------------------|----------|
| sp1  | request_changes      | request_changes     | no - but B needed 25 calls / 255k tokens where A used 5 / 26k |
| sp2  | request_changes      | approve             | **yes** |
| sp3  | approve (miss)       | approve (miss)      | no - defect missed under both |
| sp4  | request_changes      | approve             | **yes** |
| sp5  | request_changes      | approve             | **yes** |

Correct final verdicts: **A 4/5, B 1/5.** In three of five seeds the leaked
pipeline context flipped a correct rejection into an approval. The
mechanism is the uncomfortable part: in the flipped B runs the reviewer
frequently still wrote the planted defect into its own findings - and then
approved anyway. Those outputs are consistent with influence from the asserted context,
but one run per condition does not isolate a causal mechanism. Token usage moved the same direction: 121,609 total
tokens isolated vs 475,933 with context (3.9x), The transcripts include repeated inspection under condition B; this does not prove why the extra calls occurred. (Token counts here
are API usage metadata, not monetary charges; every run used the free
tier.)

Failed-attempt evidence, kept: the first sp2/B attempt crashed mid-run when
its scratch checkout disappeared beneath the agent (cause undiagnosed; the
exception is described in NOTES, but its raw attempt record was not retained. The runner now records per-variant exceptions
instead of aborting the set). The variant was re-run once, cleanly. The
crash and the single re-run are part of the record, not edited out.

This supports retaining the required fresh-context reviewer. It suggests
a risk worth testing with more seeds, repetitions and realistic artifacts,
not a general guarantee about reviewer behavior.
sp3 was missed under both conditions; that defect class (a subtle
behavioral drift the diff made look intentional) is a reviewer limitation,
recorded in section 6 rather than explained away.

## 4. Results

Working evidence snapshot at 22:24 IST, 23 November 2026. Incomplete, not a final-completion claim. Hidden tests remain sealed while valid autonomous runs continue.

| Stage reached across recoveries | Alt issues passed /5 | A3 issues passed /5 |
| --- | --- | --- |
| Requirements, historical contract |5/5|1/5|
| Design, historical contract |5/5|1/5|
| Implementation |3/5|0/5|
| Testing |3/5|0/5|
| Release |3/5|0/5|
| Historical posted verdict, boundary flawed |3/5|0/5|

These are per-issue achieved-stage counts, not per-attempt success rates or uninterrupted passes. Alt issues 1-3 reached COMMENT approve reviews on PRs 6-8, unmerged. Hosted issue 3 release recorded 230 passed,1 skipped; a separate local replay recorded 231 passed. No unexplained substitution between environments is made. These reviews were not fully independent: assignment README carried pipeline reasoning into the filtered checkout. ADR016 now excludes it, but all three need corrected-boundary reruns. The historical reviewer found no defects on these three real changes; narrow generated-test audits passed, but hidden acceptance remains unmeasured. E2 sp3 was missed in both conditions.

Alt issue 4's earlier implementation checkpoint was invalidated: no source diff and a syntax-invalid test stub. Subsequent real-diff gates rejected read-only Developer runs despite claimed file changes. Issue 5 also exhausted 40 steps reading without editing. These are execution failures, not only provider outages. Exact-block editing and baseline-regression checks were added afterward, with no completed issue trial yet.

At 21:32 the student authorized transfer before Alt completion. Protected owner-directed setup PR 1 imported the partial authored tree into A3; PR 7 transferred support corrections. Generated issue PRs were never merged. A3 issues 2-6 correspond to Alt 1-5. Its first four own runs failed requirements. Issue 6 then passed requirements and, on recovery, design; implementation then failed 503. All five corrected-contract A3 requirements attempts failed actual provider HTTP 503 UNAVAILABLE/high-demand. Some successful responses preceded failure. A corrected Alt issue 1 attempt is queued. After that trial, repeated identical failures will receive bounded 20-minute backoff, not rapid issue rotation. The earlier requirement/design passes used the historical single-output contract and are not verified full-A1 compliance. Alt successes are not A3 results. Links and attempt logs are in `results/runs.md` and repository-specific CSVs.

The terminal evidence distinguishes provider unavailability from earlier harness defects: all five corrected failures include provider HTTP 503 bodies; none has a terminal local schema-validation error. Two additional verified-free model schema probes also returned 503. This does not prove request shape is irrelevant, but there is no new client defect signal justifying another speculative rewrite.

Token accounting is incomplete. Latest Alt branch cumulative snapshots total 1,520,509 tokens across 208 calls. This is not lifetime usage: it excludes superseded attempts and independent reviewer increments. E2's 10 successful local review records total 597,542 tokens; these are separate local calls. Earlier interrupted/probe usage is not fully retained. Neither summing repeated artifact snapshots nor calling these values a complete total is valid. Free-tier use only; no paid billing was enabled.

### Additional check after the gate defect

Generated tests for issues 1/2/3 fail on unchanged pinned code (2/3/3 failures) and pass on changed heads (2/3/3 passes). These are not hidden tests. Future hosted gates require the same behavioral contrast, followed by a passing full suite. The assistant proposed this rationale and the student endorsed it at 21:09; it is not claimed as independently student-originated. Issue 2's spec incorrectly mentions an increment(field,n) argument; the real API/test uses increment(field), and this remains a spec-quality limitation.

### A1 compliance correction

A later audit found that the full A1 skill was loaded but the role prompt requested only spec.md, conflicting with mandatory SRS/REGISTER/VALIDATION outputs. Historical requirements testability passes do not prove full A1 compliance. An unused compact adaptation was rejected (ADR-015). Full skill loading is restored; all three versioned outputs plus handoff spec are required. Mechanical structure/check-result validation and a complete-document semantic audit now gate requirements. Existing downstream checkpoints are invalidated when corrected requirements first run. No corrected-contract issue has yet completed. This is an unresolved rubric gap, not a cosmetic change.

### Reviewer boundary correction

The filtered reviewer checkout still included assignment README.md, containing pipeline reasoning/results. Excluding artifact directories alone was insufficient. ADR016 excludes that README from both diff and checkout while preserving upstream README.rst. Historical COMMENT verdicts are real, but not fully compliant independent reviews. Corrected-boundary reviews completed: zero. The working video shows historical evidence, not proof of corrected independence.

## 5. Hindsight



Hindsight below is assistant-drafted for student review, not claimed as independently authored reasoning. If starting again tomorrow, the first decision to change is ADR-006
(models) - not the tiering itself, but how it was validated. I chose models
from the provider's rate-limit page and quota buckets, and twice that was
not enough: the initially selected 2.5-generation endpoints returned 404 responses indicating unavailability, and
gemini-3.5-flash-lite then answered the agents' JSON tool-contract prompts
with an empty text part (finishReason MALFORMED_FUNCTION_CALL) until the
client used explicit action-specific required-field JSON schemas. JSON mode alone was not enough. A live generation probe
per role - one real prompt through the real client before committing the
ADR - would have caught both for a handful of tokens. The general lesson:
for an agentic pipeline, "the model exists" is a behavioral claim about
your actual prompt shape, not a catalog entry, and it belongs in the
stage's checks, not in an assumption.

Second, the initial design under-planned reruns. The first rerun of the same issue
failed in the gate because the fresh branch was pushed over the previous
attempt's branch (non-fast-forward). Restarts are not an edge case in this
system - they are the normal path while iterating - and the gate now treats
"start over" as a first-class mode: refuse non-bot tips, archive the
superseded tip under a durable ref, force-with-lease only against the
validated SHA.

## 6. Limitations and threats to validity

1. **Five issues, one repository.** All evidence is from small, well-scoped
   changes to a pure-Python library with a fast test suite. Nothing here
   shows the pipeline survives a large codebase, a slow suite, or a
   genuinely ambiguous feature.
2. **Model availability constrained the assignment.** Initial 2.5 endpoints returned 404; flash transport and lite 429/503 failures dominated later runs;
   results are specific to the 3.x flash family and its free-tier rate
   limits. Model choice (ADR-006) is the most fragile decision.
3. **Hidden tests remain withheld. The tests and issues were AI-assisted.** A grader-written test
   could interpret an issue differently (e.g. whether `update` with string
   ids should coerce or reject); my pipeline's spec stage resolves such
   ambiguity with stated assumptions, which may not match the grader's.
4. **E2 is a local, single-model, authored-stimulus experiment.** Five
   seeds, one model (gemini-3.5-flash-lite, not necessarily the responding model of each hosted review), and an AI-assisted authored pipeline-context block rather than
   captured from a real run, executed locally rather than on hosted
   runners. The observed verdict contrast is consistent with anchoring; it does
   not establish causality or measure its size in production, and the catch metric is
   keyword-based over the verdict object.
5. **LLM judges check requirements, A1 substance and design.** Although they can only veto, a
   miscalibrated judge can block a good stage; the judge/model agreement
   data in the transcripts is the evidence offered.
6. **The reviewer is from the same model family as the implementer.**
   Independence is intended through context isolation and permissions, subject to the documented README flaw, not by
   model diversity; correlated blind spots remain possible (future work:
   cross-provider reviewer).

7. **Execution safety is incomplete.** Shell prefix checks allow arbitrary Python. Reviewer filtering removes stored reasoning but is not a hardened security boundary. Do not run hostile repositories with these credentials.
8. **Reasoning provenance.** The student discussed D1, D2, D4 and D8, endorsed the assistant-proposed regression-test rationale at 21:09, and accepted the newer review sheet choices at 21:23. Other explanations remain assistant-drafted; no individual answers or independently authored reasoning are invented. AI assistance is disclosed.

## Appendix

- A. Full ADR texts: `architecture/decisions/ADR-001.md` ... `ADR-016.md`.
- B. Run links: `results/runs.md`.
- C. AI-use disclosure: see `README.md` (course policy).
