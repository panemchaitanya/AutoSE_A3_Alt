"""Stage-level correction recovery: durable pending-correction records,
bound resume, fail-closed rejection, attempt bound, usage retention.

All offline: agent.run_agent, checks, a1_checks and judge are stubbed.
Run: python3 workflow/tests/test_stage_checkpoint.py
"""

import json
import os
import pathlib
import sys
import tempfile

AGENT = pathlib.Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT))

import a1_checks
import agent
import checks
import config
import controller
import gemini
import run_stage

ISSUE = {"number": 3, "title": "Add TTL index", "body": "Sessions expire."}
SPEC = "# spec\n\n## acceptance criteria\n- AC-1: x\n"


def make_repo(tmp):
    root = pathlib.Path(tmp)
    (root / config.ARTIFACTS_DIR).mkdir(parents=True)
    skill = root / "workflow" / "prompts"
    skill.mkdir(parents=True)
    (skill / "requirements-ledger-skill.md").write_text("SKILL")
    return str(root)


def fresh_state():
    return controller.init_state(3, "autose/issue-3")


class Stubs:
    """Swap the external seams; restore with .close()."""

    def __init__(self):
        self.saved = {}
        self.run_calls = []
        self.run_script = []
        self.checks_ok = (False, ["AC-2 needs a boundary"])
        self.a1 = (True, [], {})
        self.judge_reply = (True, "ok")
        self._orig_run = agent.run_agent
        self._orig_lint = checks.lint_spec
        self._orig_a1 = a1_checks.check_a1_bundle
        self._orig_judge = run_stage.judge
        agent.run_agent = self._run
        checks.lint_spec = lambda spec: self.checks_ok
        a1_checks.check_a1_bundle = lambda root: self.a1
        run_stage.judge = lambda *a, **k: self.judge_reply

    def _run(self, role, model, system, task, repo_root, usage, **kw):
        self.run_calls.append({"task": task, "usage": usage, "kw": kw})
        behavior = self.run_script.pop(0) if self.run_script else "finish_ok"
        if callable(behavior):
            return behavior(task, usage, kw)
        spec = os.path.join(repo_root, config.ARTIFACTS_DIR, "spec.md")
        with open(spec, "w") as fh:
            fh.write(SPEC)
        return {"summary": "done"}, [{"step": 0}], None

    def close(self):
        agent.run_agent = self._orig_run
        checks.lint_spec = self._orig_lint
        a1_checks.check_a1_bundle = self._orig_a1
        run_stage.judge = self._orig_judge


def run_stage_req(repo_root, state):
    return run_stage.stage_requirements(repo_root, state, ISSUE)


def test_correction_record_saved_then_resumed_after_kill():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            # Attempt 1 finishes, checks fail, record is saved, then the
            # job is killed mid-correction (attempt 2 raises).
            def killed(task, usage, kw):
                raise KeyboardInterrupt("simulated SIGTERM")
            stubs.run_script = ["finish_ok", killed]
            try:
                run_stage_req(root, fresh_state())
                raise AssertionError("kill must propagate")
            except KeyboardInterrupt:
                pass
            rec = run_stage.load_correction(root, "requirements")
            assert rec is not None
            assert rec["attempt"] == 2
            assert "failed its checks" in rec["task"]
            assert rec["issue"] == 3

            # Rerun: same issue/system/harness/input -> resume the exact
            # recorded correction task at attempt 2; checks still run.
            stubs.checks_ok = (True, [])
            state2 = fresh_state()
            assert run_stage_req(root, state2) is True
            assert stubs.run_calls[-1]["task"] == rec["task"]
            assert len(stubs.run_calls) == 3  # no attempt-1 redo
            assert run_stage.load_correction(root, "requirements") is None
            assert state2["stages"]["requirements"]["status"] == "passed"
            assert any("resuming persisted correction attempt 2" in
                       h["event"] for h in state2["history"])
        finally:
            stubs.close()


def test_changed_input_rejects_record_fail_closed():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            def killed(task, usage, kw):
                raise KeyboardInterrupt("simulated SIGTERM")
            stubs.run_script = ["finish_ok", killed]
            try:
                run_stage_req(root, fresh_state())
            except KeyboardInterrupt:
                pass
            assert run_stage.load_correction(root, "requirements")

            changed = dict(ISSUE, body="DIFFERENT issue body")
            stubs.checks_ok = (True, [])
            state2 = fresh_state()
            n = len(stubs.run_calls)
            assert run_stage.stage_requirements(root, state2, changed) is False
            assert len(stubs.run_calls) == n
            assert "recovery refused" in state2["stages"]["requirements"]["reason"]
        finally:
            stubs.close()


def test_attempt_bound_never_exceeds_max():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            def killed(task, usage, kw):
                raise KeyboardInterrupt("simulated SIGTERM")
            stubs.run_script = ["finish_ok", killed]
            try:
                run_stage_req(root, fresh_state())
            except KeyboardInterrupt:
                pass
            rec = run_stage.load_correction(root, "requirements")
            assert rec["attempt"] == 2

            # Rerun resumes at attempt 2; checks fail again -> stage
            # fails, record cleared, NO third attempt.
            calls_before = len(stubs.run_calls)
            state2 = fresh_state()
            assert run_stage_req(root, state2) is False
            assert len(stubs.run_calls) == calls_before + 1
            assert "failed its checks" in stubs.run_calls[-1]["task"]
            assert run_stage.load_correction(root, "requirements")["exhausted"] is True
            n = len(stubs.run_calls)
            assert run_stage_req(root, fresh_state()) is False
            assert len(stubs.run_calls) == n
            assert state2["stages"]["requirements"]["status"] == "failed"
        finally:
            stubs.close()


def test_unknown_record_fails_closed():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            path = pathlib.Path(root) / config.ARTIFACTS_DIR / \
                "correction_requirements.json"
            path.write_text(json.dumps({"schema": "other/9", "task": "x"}))
            stubs.checks_ok = (True, [])
            state = fresh_state()
            assert run_stage_req(root, state) is False
            assert not stubs.run_calls
            path.write_text("{not json")
            assert run_stage_req(root, fresh_state()) is False
            assert not stubs.run_calls
        finally:
            stubs.close()


def test_usage_retained_when_killed_after_progress():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            def progress_then_kill(task, usage, kw):
                usage.calls = 5
                usage.total_tokens = 1234
                kw["on_progress"]()  # the seam run_agent uses per action
                raise KeyboardInterrupt("simulated SIGTERM")
            stubs.run_script = [progress_then_kill]
            state = fresh_state()
            try:
                run_stage_req(root, state)
            except KeyboardInterrupt:
                pass
            on_disk = controller.load_state(root)
            assert on_disk["usage"]["calls"] == 5
            assert on_disk["usage"]["total_tokens"] == 1234
        finally:
            stubs.close()


def test_kill_between_finish_and_checks_loses_no_claim():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_repo(tmp)
        stubs = Stubs()
        try:
            def boom(spec):
                raise KeyboardInterrupt("killed during checks")
            orig_lint = checks.lint_spec
            checks.lint_spec = boom
            stubs.run_script = ["finish_ok"]
            state = fresh_state()
            try:
                run_stage_req(root, state)
                raise AssertionError("kill must propagate")
            except KeyboardInterrupt:
                pass
            # No correction record: checks never completed, nothing is
            # claimed; usage up to the kill IS on disk.
            assert run_stage.load_correction(root, "requirements") is None
            assert controller.load_state(root) is not None
            checks.lint_spec = orig_lint

            # Rerun with failing checks now records the correction.
            def killed(task, usage, kw):
                raise KeyboardInterrupt("simulated SIGTERM")
            stubs.run_script = ["finish_ok", killed]
            state2 = fresh_state()
            try:
                run_stage_req(root, state2)
            except KeyboardInterrupt:
                pass
            rec = run_stage.load_correction(root, "requirements")
            assert rec and rec["attempt"] == 2
        finally:
            stubs.close()


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
