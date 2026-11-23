# AutoSE A3: Agentic SDLC Workflow

A GitHub Actions prototype that takes a TinyDB issue through requirements, design, implementation, testing, pull-request creation and a separate review job. The workflow does **not** merge generated pull requests.

> **Status: incomplete assignment, working prototype.** The pipeline and its offline checks are implemented. No issue has completed the entire corrected A1 requirements contract plus corrected independent-review boundary. Historical passes below are real, but are not equivalent to corrected end-to-end completion. This README is a project guide, not a completion certificate.

## Start here

| Item | Location |
| --- | --- |
| Assignment report, seven pages | [report.pdf](report.pdf) |
| Recorded browser walkthrough, about 76 seconds | [demo.mp4](demo.mp4) |
| Architecture and decisions | [ARCHITECTURE.md](ARCHITECTURE.md), [ADRs](architecture/decisions/) |
| Workflow and model-role implementation | [workflow/](workflow/), [.github/workflows/](.github/workflows/) |
| Experiment issues and definitions | [experiment/](experiment/) |
| Hosted run index, including failures | [results/hosted-index.md](results/hosted-index.md) |
| Results and measurement caveats | [results/](results/) |
| Latest checkpoint and remaining work | [results/checkpoint-2357.md](results/checkpoint-2357.md) |
| Original TinyDB documentation | [README.rst](README.rst), [docs/](docs/) |

The recording shows live navigation of historical GitHub evidence. It is not a recording of a newly completed corrected run. Its captions identify the earlier requirements gap and review-context leak.

## Repositories and baseline

- **Submission:** https://github.com/panemchaitanya/AutoSE_A3
- **Development:** https://github.com/panemchaitanya/AutoSE_A3_Alt
- **Upstream:** https://github.com/msiemens/tinydb
- **Pinned upstream baseline:** `edff96aeb2616402e9489d46e90a592c05565621`.

The two repositories have separate issue numbers, histories and autonomous attempts. Development results must not be counted as submission-repository outcomes. Issue 1 in Alt corresponds to issue 2 in A3 because A3's setup pull request consumed number 1.

## What the application does

```text
Owner issue / label / dispatch
             |
             v
Gate and isolated issue branch
             |
             v
SpecWriter + full A1 skill --> structural checks + semantic judge
             |
             v
Designer + architecture context --> design checks
             |
             v
Developer <--> Tester --> bounded repair loop
             |
             v
Release: open/update PR, never merge
             |
             v
Separate reviewer job --> COMMENT verdict and findings
             |
             v
Human decision; bounded continuation when changes are requested
```

Each stage records state, model usage, transcripts and artifacts. Guards invalidate old downstream checkpoints when the corrected A1 bundle has not been verified. Developer completion requires an actual source diff. Testing includes the baseline regression suite. The separate reviewer receives a cleaned copy without pipeline reasoning, assignment README, workflow code or experimental artifacts.

The reviewer is a separate role/job and context boundary, not a different provider or inherently independent model. Historical reviews before ADR016 did not have the corrected boundary.

## Local setup

Use Python 3.12, the version used by the hosted workflows. Git and GitHub CLI are needed for owner-operated hosted setup. The Gemini client uses Python's standard library; the project and tests still need their normal dependencies.

```bash
git clone https://github.com/panemchaitanya/AutoSE_A3.git
cd AutoSE_A3
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . pytest pytest-cov
python -m pytest tests workflow/tests -q
```

On Windows, activate `.venv\Scripts\activate` instead. The command above runs baseline and harness tests without model API calls. It does not run the sealed hidden acceptance tests or establish autonomous issue success.

Latest local combined validation: **241 tests passed**, with **94% measured aggregate coverage** in that invocation. See [results/final-offline-validation.txt](results/final-offline-validation.txt). These are local baseline/harness results, not five completed feature tasks.

## Configure a fork for hosted execution

1. Keep the repository public only if that matches the intended audience. Never commit API keys.
2. In **Settings > Secrets and variables > Actions**, add repository secret `GEMINI_API_KEY` from a free-tier Gemini project. Check current provider pricing and quota before use. No paid model or paid runner usage is authorized for this project.
3. Enable GitHub Actions, read/write workflow permissions and permission to create pull requests. The YAML declares its required contents, pull-request, issue, action and status scopes.
4. Protect `main`: require pull requests, include administrators, disallow force pushes and deletion. Support/artifact updates use protected pull requests. Generated issue PRs remain unmerged.
5. Set optional repository variables `MODEL_SPEC`, `MODEL_DESIGN`, `MODEL_DEVELOP`, `MODEL_TEST`, `MODEL_REVIEW` and `MODEL_JUDGE`. Defaults and fallback behavior are in [config.py](workflow/agent/config.py). Overrides are requests, not proof of which model answered.
6. Confirm that any selected model is available on the free tier. The late recovery trial uses `gemini-3.8-flash` for Alt requirements and judge, with the existing `gemini-3.5-flash-lite` fallback. Other role overrides remain `gemini-3.5-flash-lite`. A3 has its own settings.

Provider pricing reference: https://ai.google.dev/gemini-api/docs/pricing . Free-tier availability does not guarantee an individual request will succeed. Repeated HTTP 503 responses are recorded as failures, not passes.

## Run an issue

Create a concrete issue with behavior and acceptance criteria. The provided five experiment issue texts are under [experiment/issues/](experiment/issues/).

Choose one supported trigger:

- As repository owner, apply label `autose` to an issue.
- As repository owner, comment `/autose` on an issue.
- From **Actions > autose > Run workflow**, select `main`, enter the issue number and leave `entry` blank for a fresh attempt.

For recovery, dispatch the same issue with `entry=resume`. `design` and `implementation` are explicit continuation values. Resume preserves only checkpoints that remain valid under the current gates. It is not permission to bypass the corrected requirements checks.

The gate creates or updates `autose/issue-<number>`. Follow the `autose` run and, after release, the `autose-review` run. GitHub's same-repository token-trigger rules are handled through explicit review dispatch rather than assuming a generated PR event will always start another workflow.

Do not run multiple provider attempts in parallel. The main workflow has a concurrency group; cross-repository coordination still needs the operator to avoid parallel calls.

## Inspect the outputs

On an issue branch:

- `.autose/state.json`: stage state, history and cumulative usage.
- `.autose/artifacts/spec.md`: handoff requirements.
- Versioned A1 SRS, REGISTER and VALIDATION outputs, plus structural and semantic checks.
- `design.md`, implementation diff, `test_report.md`, `pr.md` and review outputs.
- Per-stage transcripts and progress snapshots, including failures where captured.
- Generated source changes and `tests_autose/` tests in the proposed PR.

Stage artifacts are also uploaded to their Actions runs. A green setup or offline CI job does not mean the autonomous workflow passed. A stage marked passed under the older contract does not prove corrected A1 compliance.

COMMENT reviews contain explicit verdicts; they are not formal human GitHub approvals. No automatic merge is implemented.

## Evidence and current results

| Area | Established | Not established |
| --- | --- | --- |
| Local application/harness | 241 local tests passed in the final offline invocation | Autonomous feature correctness or hidden-test results |
| Historical Alt issues 1-3 | Real generated PRs, tests, release stages and COMMENT verdicts across recovery attempts | Corrected A1 compliance or fully isolated historical reviews |
| Corrected requirements | Full original skill restored, three outputs required, checks and invalidation tested offline | Any full corrected end-to-end issue outcome |
| Reviewer boundary | README and pipeline artifacts excluded; offline regression coverage | New corrected-boundary hosted review outcome |
| A3 attempts | Separate real hosted attempts, including actual requirements 503 failures | Five successful submission-repository runs |
| E1 | Recorded attempts and exploratory availability probes | Valid completed controlled model-quality comparison |
| E2 | Ten local single-model reviews, five paired authored-context cases | Causal/general accuracy conclusion or hosted isolation proof |
| Hidden evaluation | Tests kept outside both repositories during final autonomous work | Final hidden-test evaluation, currently not run/revealed |

Historical Alt PRs: [#6](https://github.com/panemchaitanya/AutoSE_A3_Alt/pull/6), [#7](https://github.com/panemchaitanya/AutoSE_A3_Alt/pull/7), [#8](https://github.com/panemchaitanya/AutoSE_A3_Alt/pull/8). Historical issue 3 workflow: https://github.com/panemchaitanya/AutoSE_A3_Alt/actions/runs/45197403640 . Historical review: https://github.com/panemchaitanya/AutoSE_A3_Alt/pull/8#pullrequestreview-6023844081 . These are qualified historical evidence, not full-compliance results.

Late corrected trial on the alternate free route, failed at requirements after two real replies and provider 503: https://github.com/panemchaitanya/AutoSE_A3_Alt/actions/runs/45236463146 . Consult the checkpoint for its observed state; a queued or running job is not success.

## Budgets, costs and measurement

The harness enforces configurable limits: 40 agent steps, 1,500,000 cumulative tokens per run, three fix cycles and two review rounds by default. Calls use bounded retries/backoff and a named fallback. Usage is read from provider `usageMetadata`.

Saved usage snapshots can be cumulative and overlapping. Do **not** sum every snapshot as lifetime usage. A complete cross-attempt lifetime total is not recovered. Model configuration, requested model and responding-model evidence are separate facts. No paid fallback or paid-runner charges are authorized.

## Recovery and known limits

Late recovery improvement: [ADR017](architecture/decisions/ADR-017.md) checkpoints exact preparation-role conversations after completed observations, bound to the full contract/task/model/source fingerprint. Reviewer context stays fresh, total step caps survive restarts, and no checks are bypassed. New local baseline/harness invocation: **245 passed**, [recorded output](results/recovery-tests-0010.txt). This post-deadline work is not on-time evidence.

- **503 / UNAVAILABLE:** preserve failure artifacts, use bounded backoff and check provider availability. A short successful probe does not prove a full stage will recover.
- **429 / quota exhaustion:** stop or wait within free quota. Do not enable billing as a recovery step.
- **Old checkpoint:** corrected A1 validation invalidates downstream passes unless `a1_bundle_verified` is set by the current checks. Do not set it manually.
- **No source diff / invalid test:** implementation and regression guards must reject false completion.
- **Missing Actions artifact or log:** mark unavailable. Never replace it with invented evidence.
- **Unfinished experiment:** retain the actual partial observations and report the gap.

This is a research prototype, **not a secure sandbox for hostile repositories**. Allowed Python/shell commands can execute arbitrary code despite prefix/path checks. Reviewer context restrictions reduce information flow but do not make malicious source execution safe. Never run it with unrelated secrets or broad production credentials.

Hidden tests remain excluded until the final autonomous attempts in **both** repositories finish. The compact A1 adaptation is retained as an unused experiment artifact; it is not the active requirements skill.

## Documentation, chronology and authorship

The report, README and checkpoint state known gaps explicitly. They must not be read as evidence that every rubric item is complete. Work committed after the 23 November 2026 23:59 IST deadline is late work and must retain its real timestamps. No history is backdated.

An AI coding assistant contributed substantially to the workflow, prompts, architecture, ADRs, experiments and report. The student discussed selected design decisions and endorsed selected rationales; other explanations remain AI-drafted. This disclosure does not claim unaided authorship or that every course authorship requirement is met. See the report and decision records for limitations.

The upstream project license remains in [LICENSE](LICENSE). For TinyDB's own API, contribution process and documentation, use [README.rst](README.rst) and [CONTRIBUTING.rst](CONTRIBUTING.rst).
