# Component view

Model names in the original diagram are historical committed defaults. Current repo variables select3.5-flash-lite for all roles. Full A1 output/validation correction is ADR015; old stage checkpoints are historical, not proof of full compliance.

The system is two GitHub Actions workflows, five LLM agent roles, one scripted
release step, a deterministic controller, and a state file on the work branch.

```mermaid
graph TD
    subgraph Triggers
        L[Maintainer adds label 'autose' to an issue]
        C[Maintainer comments /autose on an issue]
        F[Review workflow dispatches<br/>a continuation run + comments]
    end

    subgraph autose.yml [Main workflow: autose.yml]
        GATE[Gate job<br/>auth check, mode: start or continue,<br/>creates branch autose/issue-N]
        REQ[Job: requirements<br/>SpecWriter agent]
        DES[Job: design<br/>Designer agent]
        DEV[Job: develop<br/>Developer + Tester agents<br/>bounded fix loop, max 3 cycles]
        REL[Job: release<br/>scripted, no LLM<br/>push branch, open PR]
        GATE --> REQ --> DES --> DEV --> REL
    end

    subgraph review.yml [Review workflow: autose-review.yml]
        REV[Job: review<br/>Reviewer agent<br/>fresh context, contents-read token]
    end

    subgraph CI [ci.yml]
        TESTS[pytest on push and PR]
    end

    subgraph Agents [Agent roles and their tools]
        SW[SpecWriter<br/>gemini-3.5-flash-lite<br/>A1 requirements-ledger skill]
        DS[Designer<br/>gemini-3.5-flash-lite<br/>A2 ARCHITECTURE.md + file tree]
        DV[Developer<br/>gemini-3.5-flash<br/>read/write files, whitelisted shell]
        TS[Tester<br/>gemini-3.5-flash-lite<br/>write tests, run pytest]
        RW[Reviewer<br/>gemini-3.5-flash<br/>read repo at PR head, run tests<br/>no write, no push, no pipeline context]
    end

    subgraph State [State and hand-offs]
        ST[.autose/state.json on the branch<br/>stage status, budgets, token usage]
        AR[.autose/artifacts/<stage>.md on the branch<br/>+ GitHub Actions artifacts]
    end

    L --> GATE
    C --> GATE
    F --> GATE
    REQ --> SW --> AR
    DES --> DS --> AR
    DEV --> DV --> AR
    DEV --> TS --> AR
    REL -->|opens PR| TESTS
    TESTS -->|CI green| REV
    REV --> RW --> AR
    RW -->|changes requested, rounds left| F
    F -->|workflow_dispatch: issue, entry| GATE
    RW -->|approve, or 2 rounds used| H[Human decides merge or close]
    GATE <--> ST
    REQ <--> ST
    DES <--> ST
    DEV <--> ST
    REL <--> ST
    REV <--> ST
```

## What each piece is

| Component | Kind | Responsibility |
| --- | --- | --- |
| Gate job | Scripted | Authenticate the trigger (only the repo owner), decide start vs continue, create or reuse the work branch, load `state.json`. |
| SpecWriter | LLM agent (lite default) | Turn the issue into `spec.md` with testable acceptance criteria, using my A1 requirements-ledger skill. |
| Designer | LLM agent (lite default) | Turn the spec into `design.md`: approach plus the exact files and functions to change, guided by my A2 `ARCHITECTURE.md`. |
| Developer | LLM agent (flash default) | Edit the code on the work branch following the design; produces `diff.patch`. |
| Tester | LLM agent (lite default) | Write one test per acceptance criterion, run the full suite, produce `test_report.md`; on failure hand back to the Developer inside the same job, at most 3 cycles. |
| Release | Scripted `gh` calls | Commit artifacts, push the branch, open the pull request, write `pr.md`. |
| Reviewer | LLM agent (flash default) | Review the PR seeing only the issue, the diff and the repo at the PR head; approve or request changes with a classification (approach vs code). |
| Controller (`controller.py`) | Scripted | The state machine: which stage runs next, whether a check passed, when budgets are exhausted. LLMs never decide flow. |
| `state.json` | File on branch | Stage status, review rounds, fix cycles, cumulative token usage. Supports recovery of passed checkpoints; earlier failed-stage edits were not always retained. |

## Trust boundaries and measured gaps

- Issue/comment text is untrusted input and is delimited in prompts. That
  is a prompt-level defense, not containment.
- File-write tools refuse protected paths; shell commands use prefix checks.
  Python and shell composition still permit arbitrary execution, including
  network access. These controls are not a sandbox (ADR013).
- Gate, stage commit and release steps push only to the owned fork. Agents
  lack an explicit push tool; arbitrary execution remains a security gap.
- The reviewer has contents-read permission, review/comment writes and
  continuation dispatch permission. Its clean source copy excludes stored
  pipeline reasoning and git history, and has no explicit file-write tool.
  This is not a hardened runtime security boundary.
- Default model names above describe committed configuration. Recovery
  overrides and responding-model counts must be read from actual usage.
- No automatic merge exists. A person retains the merge decision.
- CI is rerun directly in the release job before dispatching review; some
  separate ci.yml events were action_required rather than passing.
