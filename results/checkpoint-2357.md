# Submission checkpoint: 23 November 2026, 23:57 IST target

This is a preservation checkpoint for incomplete work, not a completion declaration. Times below are observations, not invented run chronology. Later updates retain their true commit dates. The student submitted the repository URL to Moodle and explicitly approved continuing after midnight as late work.

## Current implementation

The source and hosted workflow cover the six-stage issue-to-reviewed-PR process. The corrected full A1 skill is active, with mandatory SRS/REGISTER/VALIDATION artifacts, structural checks, a semantic judge and old-checkpoint invalidation. The reviewer copy excludes pipeline reasoning and the assignment README. Generated issue pull requests remain unmerged.

## Latest local validation

At about 23:46 IST, `python -m pytest tests workflow/tests -q --disable-warnings` passed **241 tests**. Coverage reported **94% aggregate**. Output: [final-offline-validation.txt](final-offline-validation.txt). This includes offline harness/stub checks and baseline tests. It is not autonomous feature completion and does not use the hidden tests.

## Real late recovery attempts

- Alt trial [45234868390](https://github.com/panemchaitanya/AutoSE_A3_Alt/actions/runs/45234868390): gate passed, one real requirements list-files reply, then actual provider HTTP 503 UNAVAILABLE/high-demand failure. Downstream stages skipped.
- Alt alternate-free-route trial [45236463146](https://github.com/panemchaitanya/AutoSE_A3_Alt/actions/runs/45236463146): dispatched at approximately 23:45:37 IST with `gemini-3.8-flash` requirements/judge overrides. At 23:51:42 IST, live requirements logs showed two real `run_shell` actions, cumulative branch accounting 41 calls / 363,904 tokens. The job was still running at that observation. It subsequently failed at **23:51:48 IST** after those two replies, exhausting retries with the actual provider HTTP 503 UNAVAILABLE/high-demand body. Downstream jobs were skipped. These cumulative counters are not this trial's isolated usage and are not added to previous snapshots.

No corrected-compliant full end-to-end issue outcome is established by these observations. Consult the actual run for subsequent state.

## Preserved deliverables

- README reorganized as final submission documentation: overview, architecture, setup, run/recovery, evidence matrix, experiment status, limits and authorship.
- `demo.mp4` replaced with a genuine continuous 76-second browser recording of actual historical GitHub pages, not the earlier slideshow. Captions distinguish historical evidence from corrected compliance and explicitly state incomplete status. The previous slideshow is superseded, not evidence of a live run.
- Seven-page `report.pdf` remains the earlier honestly qualified report. Its evidence snapshot is older than these late attempts; this checkpoint supplements rather than silently rewrites it.
- Hidden acceptance tests remain outside both repositories and have not been run or revealed.

## Remaining work

1. Complete corrected A1 requirements and all downstream autonomous stages on five issues in each repository.
2. Obtain new hosted reviews under the corrected context boundary, without merging generated issue PRs.
3. Complete a valid controlled E1 model-quality comparison. Short connectivity probes are not a substitute.
4. Finalize experiment analysis and recover usage without double counting overlapping cumulative snapshots.
5. Only after final autonomous runs in both repositories finish, reveal/run the sealed hidden evaluation.
6. Produce a genuine successful issue-to-posted-review recording if and when such a corrected run exists, then revise the report from real outcomes.

Provider failures and earlier setup mistakes both contributed to the gap. No expected grade or completion guarantee is claimed.
