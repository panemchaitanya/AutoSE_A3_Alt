# Stage map

Model labels below are original committed defaults. Current variables request3.5-flash-lite for all roles. ADR015 requires full A1 SRS/REGISTER/VALIDATION plus handoff spec, substantive validation and downstream checkpoint invalidation. Earlier requirements passes were testability-only evidence.

| # | Stage | Agent (model) | Inputs the agent sees | Artifact | Check before moving on | Who decides pass/fail |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Requirements | SpecWriter (gemini-3.5-flash-lite) | Prompt: issue title + body; repo read tools remain | `spec.md` plus full A1 bundle | A1 structure + semantic audit; AC lint: every acceptance criterion is given/when/then or measurable, no vague words; LLM judge agrees all criteria are testable | Mechanical lint + judge, recorded in `state.json` |
| 2 | Design | Designer (gemini-3.5-flash-lite) | `spec.md`, `ARCHITECTURE.md`, repo tools | `design.md` | Every file the plan names exists in the repo or is explicitly marked NEW; plan names files and functions | Mechanical path check + judge |
| 3 | Implementation | Developer (gemini-3.5-flash) | `design.md`, acceptance criteria, full repo read/write tools | `diff.patch` | `python -m compileall` on changed files + package imports | Mechanical (exit codes) |
| 4 | Testing | Tester (gemini-3.5-flash-lite) | `spec.md` criteria, `diff.patch`, repo; writes tests, runs pytest | `test_report.md` | New tests and full suite pass (`pytest` exit 0); on failure back to stage 3, max 3 cycles | Mechanical (pytest exit code) |
| 5 | Release | none (scripted `gh` CLI) | `diff.patch` applied on branch, all prior artifacts | `pr.md` + PR link | PR is open and release job reruns full pytest and posts ci/pytest status | Mechanical (pytest exit + gh API) |
| 6 | Review | Reviewer (gemini-3.5-flash) | Issue text, `diff.patch`, repo at PR head. Never the pipeline artifacts or agent logs | `review.md` + PR review | Approve, or changes requested classified as approach/code; max 2 rounds | Reviewer verdict JSON with mandatory evidence; human merges |

## Inputs and actual exclusions

- SpecWriter prompt starts from issue text; its file-read tools can still
  inspect the repository. This is not a read-permission exclusion.
- Designer prompt starts from checked spec and architecture, but source
  access can expose other repository content.
- Developer/Tester never receive hidden acceptance tests during runs.
- Reviewer runs against a filtered fresh copy excluding `.autose`, git
  history, workflow, experiment, results, architecture and report/demo.
  The diff is similarly filtered. Source comments themselves may contain
  influence; shell execution is not sandboxed (ADR013).
- Models are committed defaults. Recovery overrides differ; actual model
  response counters in newer usage records are the evidence.
- Posted reviews are COMMENT reviews carrying an explicit verdict, not
  formal GitHub approvals. GitHub rejected bot self-approval.
