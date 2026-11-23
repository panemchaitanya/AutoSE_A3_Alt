> 22:24 IST: all five corrected-A1 A3 attempts failed requirements with provider HTTP503 UNAVAILABLE/high-demand responses. No corrected-contract complete issue. A corrected Alt trial continues; repeated identical failures will use bounded backoff. The incomplete snapshot remains usable while full-completion work continues. Hidden tests are still sealed.

> Correction at 22:13 IST: historical Alt COMMENT reviews were not fully independent because assignment README exposed pipeline reasoning. ADR016 closes that path; corrected-boundary reviews completed: zero. Earlier three verdicts remain real historical evidence, not full-compliance results. New probes on verified-free3.8-flash and4-hydrogen also returned503; no paid fallback used.

# AutoSE A3 working submission

**Working snapshot, 23 November 2026 21:59 IST. Not complete.** [Report](report.pdf) and [captioned recovery walkthrough](demo.mp4) preserve the current evidence. The video uses actual Alt issue3 across recovery attempts, not an uninterrupted A3 run. Hidden tests remain sealed while coding continues. Earlier requirements stages checked testability but did not establish full A1 artifact compliance; corrected full-skill output/validation reruns are required. See ADR015 and the report. Generated issue PRs stay unmerged.

# AutoSE A3 - Architecting an Agentic SDLC Workflow

AutoSE course, Assignment 3. A GitHub Actions workflow that turns an issue
into a tested, independently reviewed pull request.

- **Fork of:** https://github.com/msiemens/tinydb
- **Pinned commit:** `edff96aeb2616402e9489d46e90a592c05565621`
  (`edff96a`). All issues, runs and PRs start from this commit's
  code as it stands in this fork.
- **Models (free-tier Gemini API key, repo secret `GEMINI_API_KEY`):**
  gemini-3.5-flash-lite for SpecWriter / Designer / Tester / judge,
  gemini-3.5-flash for Developer / Reviewer (ADR-006). Total tokens per run are
  recorded from API usage metadata. `results/results.csv` distinguishes
  branch-cumulative counts from attempts and separate reviews; it is not yet
  the total usage ledger. Earlier recovery overrides requested 3.1-flash-lite with a
  3.5-flash-lite fallback. Current variables in both repos request
  3.5-flash-lite for every role. Defaults are not responding-model evidence. The key sits on a free-tier project with no billing
  attached, so spend is hard-capped at the free quota.

## How to trigger the workflow

1. Open an issue (see `experiment/issues/` for the five used in the
   experiments).
2. Add the label `autose` to it, or comment `/autose` on it.
3. Watch `.autose/artifacts/` on the branch `autose/issue-<N>`: every stage
   commits its artifact there (`spec.md`, `design.md`, `diff.patch`,
   `test_report.md`, `pr.md`, `review.md`) plus a transcript. Corrected requirements also require versioned A1
   SRS/REGISTER/VALIDATION and substantive validation; the same files
   are attached to the Actions run. `state.json` on the branch shows the
   pipeline's decisions.
4. The run ends with a PR reviewed by the independent reviewer. Only a human
   merges or closes - the workflow never merges.

Label/comment starts require the repository owner. Workflow dispatch requires
write access. `main` protection was configured, but owner/admin bootstrap
pushes occurred; do not read protection as proof that every change used a PR.

## Layout

```
README.md            # this file
report.pdf           # the report (max 8 pages + appendices)
demo.mp4             # demo video link (see results/runs.md)
ARCHITECTURE.md      # my A2 architecture document, feeds the Designer
architecture/
  views/             # component view, sequence view, stage map
  decisions/         # ADR-001.md ... ADR-015.md (Nygard format)
workflow/            # copy of .github/workflows/ + all agent code + prompts
experiment/
  issues/            # the 5 issue texts
  hidden_tests/      # hidden acceptance tests (kept out of the repo during runs)
  seeded_prs/        # the 5 reviewer-check PRs (diffs + labels)
  variants.md        # what each decision-experiment variant changes
results/
  results.csv
  runs.md            # links to every Actions run, PR and review
```

The live workflows are in `.github/workflows/` (`autose.yml`,
`autose-review.yml`, `ci.yml`); `workflow/` holds a copy plus the agent
harness and prompts, as the brief asks.

## AI use (course policy)

An AI coding assistant provided substantial help with the workflow code,
prompts, architecture drafts, ADR drafts, experiments and report drafts.
The repository records actual runs and failures. The student discussed D1,
D2, D4 and D8, endorsed the assistant-proposed regression-test rationale,
and accepted the newer reasoning-review sheet choices. Other explanations
remain AI-drafted, not independently student-originated reasoning. This
disclosure does not claim unaided authorship or that every course authorship
requirement is met.

## Notes for maintainers

- `.autose/` on a PR branch is pipeline metadata; drop it when merging.
- Generated tests live in `tests_autose/` and are part of the reviewed diff.

## Current evidence and prototype limits

Development started in AutoSE_A3_Alt. Submission target is AutoSE_A3.
At21:32IST the owner approved transferring partial work before Alt completion.
Protected bootstrap PR1 was merged under that direction; generated issue PRs
remain unmerged. A3 has its own real run attempts. The first failed at
requirements503. Do not treat transfer as completion.

Operational recovery preserves passed stages; multiple runs may contribute
to one issue. COMMENT reviews carry explicit verdicts but are not formal
GitHub approvals. Hidden tests stay outside both repositories until final
runs in both finish. E1's intended model-quality comparison is incomplete
and confounded; E2 has ten local single-model reviews with authored context.
Python shell access is arbitrary execution: path/prefix checks are not a
sandbox. This prototype is not suitable for hostile repositories/secrets.
