# Decision experiments - what each variant changes

The report's section 3. E2 completed ten local reviews. E1 remains an incomplete, confounded operational comparison. Negative results
count as much as positive ones (brief's rule) and are reported as found.

## E1 - tests ADR-006 (model tiers): Developer on flash-lite vs flash

- **Question:** does the Developer's model tier actually matter, or is the
  cheaper tier good enough when the stage is mechanically checked?
- **Variant A (control):** Developer = gemini-3.5-flash (the ADR's choice).
- **Variant B (treatment):** Developer = gemini-3.5-flash-lite, everything
  else identical (same issues, prompts, checks, budgets).
- **Issues used:** #3 (search limit) and #4 (get default) - the two feature
  issues, comparable in size.
- **Measurements:** build-pass on first implementation, tests-pass within
  fix cycle 1, fix cycles used, total tokens, wall time, and whether the run
  completed at all.
- **Decision rule:** if flash-lite matches flash on pass outcomes, ADR-006 is
  amended to move the Developer down a tier (cost win); if it does not, the
  ADR stands with measured evidence.

## E2 - tests ADR-003/ADR-008 (reviewer isolation): with vs without pipeline context

- **Question:** does hiding the pipeline's artifacts from the reviewer
  actually change what it catches - or is isolation ceremony?
- **Material:** the five seeded PRs in `experiment/seeded_prs/` - authored diffs
  against the pinned repository, each with one defect planted by hand (see the label
  file per seeded PR).
- **Variant A (control, my design):** reviewer sees issue + diff + repo at
  the PR head only.
- **Variant B (treatment):** reviewer additionally receives spec.md,
  design.md and test_report.md from the pipeline that produced the PR.
- **Measurements:** planted-defect catch rate (out of 5) per variant, false
  positives raised, verdict distribution.
- **Decision rule:** if the context-fed reviewer catches fewer planted
  defects (anchoring on the pipeline's own claims), isolation stays. If the
  catch rate is equal, ADR-003's exclusion list is re-examined - giving the
  reviewer the spec might be free.

### As-run deviation (recorded, not hidden)

The seeded PRs predate any pipeline run, so no real spec/design/test_report
artifacts exist for them. Variant B therefore received an AUTHORED
pipeline-context block (spec/design/test-report/developer summary all
asserting the change is verified correct) instead of captured artifacts.
Run locally on gemini-3.5-flash-lite. Both deviations are carried into the
report's limitations. Result: correct verdicts A 4/5, B 1/5; three verdict
flips to approve under context; isolation stays (see report section 3).

### E1 as-run deviation

The intended same-harness two-model quality comparison did not complete.
Flash attempts failed on transport; lite attempts changed schemas, retry
logic and pacing as availability failures were diagnosed. Later serial
recoveries reached review for issues1/2, but this cannot isolate model
quality. ADR006 is superseded provisionally by012 for availability, not
proved quality. Preserve all failed runs and distinguish responding model
from requested primary and fallback.

## E1b exploratory matched availability follow-up,22:12 IST

Identical Developer prompt/schema/task,512output cap and temperature0.2,
same ORION free project, serial one-trial calls, no fallback. Requested
3.8-flash and4-hydrogen both returned actual HTTP503 UNAVAILABLE in0.35s
and0.52s. This is an exploratory availability contrast, not a completed
replacement for original E1 coding-quality experiment. It supports bounded
backoff for this incident, not a model-quality conclusion. Raw sanitized
responses in results/probes/new-free-model-probes.json; verified-free source
https://ai.google.dev/gemini-api/docs/pricing read22:10 IST.
