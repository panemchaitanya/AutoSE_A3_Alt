"""Stage runner - the piece the GitHub Actions jobs call.

Usage:
    python workflow/agent/run_stage.py --stage requirements|design|develop|review \
        --repo . --issue-file issue.json

Reads/writes controller state (.autose/state.json) and stage artifacts
(.autose/artifacts/). Exit code 0 = stage passed (or was already passed and
skipped); exit code 1 = stage failed or stopped; the reason is always in the
stage's artifact and in state.json (ADR-002, ADR-004).
"""

import argparse
import hashlib
import json
import os
import subprocess
import shutil
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent
import checks
import call_log
import a1_checks
import config
import controller
import gemini
import prompts
import review_feedback


def read_file(repo_root, rel):
    path = os.path.join(repo_root, rel)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_artifact(repo_root, name, content):
    path = os.path.join(repo_root, config.ARTIFACTS_DIR, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.join(config.ARTIFACTS_DIR, name)


def git_changed_files(repo_root):
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root,
                          capture_output=True, text=True)
    files = []
    for line in proc.stdout.splitlines():
        rel = line[3:].strip()
        if rel and not rel.startswith((".autose/", "tests_autose/")):
            files.append(rel)
    return sorted(files)


def make_diff(repo_root, base_ref=None):
    if base_ref:
        proc = subprocess.run(["git", "diff", f"{base_ref}...HEAD"],
                              cwd=repo_root, capture_output=True, text=True)
    else:
        proc = subprocess.run(["git", "diff", "HEAD"], cwd=repo_root,
                              capture_output=True, text=True)
    return proc.stdout


def judge(repo_root, usage, question, document, stage=None):
    """Advisory LLM judge for the two semantic checks (ADR-007)."""
    task = (f"Property to verify: {question}\n\n"
            f"Document under review:\n```markdown\n{document}\n```\n\n"
            f"Answer with one JSON object.")
    context = {"role": "Judge", "stage": stage, "repo_root": repo_root,
               "task_sha256": hashlib.sha256(task.encode()).hexdigest()}
    try:
        reply = gemini.generate(config.MODEL_JUDGE, prompts.JUDGE_SYSTEM,
                                [{"role": "user", "parts": [{"text": task}]}],
                                usage, context=context)
    except Exception as e:  # a judge outage must not pass a stage
        return False, f"judge unavailable: {e}"
    try:
        start = reply.find("{")
        obj = json.loads(reply[start:reply.rfind("}") + 1])
        return bool(obj.get("pass")), "; ".join(obj.get("reasons", []))
    except Exception:
        return False, f"judge reply unparsable: {reply[:300]}"


def load_usage(state):
    return gemini.Usage(state.get("usage") or {})


def store_usage(state, usage):
    state["usage"] = usage.as_dict()


# ---------------------------------------------------- correction recovery
# A stage's self-correction runs the agent with a NEW task (original task
# plus the failed checks), so the agent-level checkpoint fingerprint
# legitimately changes. Without a durable stage-level record, a SIGTERM /
# job timeout during correction loses the attempt index and the exact
# correction task, and a rerun restarts the correction from step 0 until
# the job times out again. The record below makes the pending correction
# durable in .autose/artifacts/ (committed / uploaded with the stage's
# other artifacts). Resume restores it ONLY when every binding matches;
# anything unknown discards the record and starts at attempt 1. A resume
# never skips checks and never invents a pass.
CORRECTION_SCHEMA = "autose-correction/1"
CORRECTION_MAX_ATTEMPTS = 2


def _sha(text):
    return hashlib.sha256((text or "").encode()).hexdigest()


def _correction_path(repo_root, stage):
    return os.path.join(repo_root, config.ARTIFACTS_DIR,
                        f"correction_{stage}.json")


def save_correction(repo_root, record):
    path = _correction_path(repo_root, record["stage"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def load_correction(repo_root, stage):
    path = _correction_path(repo_root, stage)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"schema": "invalid"}


def clear_correction(repo_root, stage):
    path = _correction_path(repo_root, stage)
    if os.path.isfile(path):
        os.remove(path)


def correction_binds(record, stage, issue_number, system, original_task):
    """(True, "") only when the record proves it belongs to THIS stage,
    issue, system prompt, input task and executing harness. Unknown or
    missing fields fail closed with a reason."""
    if not isinstance(record, dict):
        return False, "correction record is not an object"
    if record.get("schema") != CORRECTION_SCHEMA:
        return False, f"unknown correction schema {record.get('schema')!r}"
    if record.get("stage") != stage:
        return False, "record is for a different stage"
    if record.get("issue") != issue_number:
        return False, "record is for a different issue"
    if record.get("system_sha256") != _sha(system):
        return False, "system prompt changed since the correction ran"
    if record.get("original_task_sha256") != _sha(original_task):
        return False, "stage input changed since the correction ran"
    if record.get("harness_sha256") != call_log.harness_digest():
        return False, "harness code changed since the correction ran"
    attempt = record.get("attempt")
    if not isinstance(attempt, int) or not 2 <= attempt <= \
            CORRECTION_MAX_ATTEMPTS:
        return False, f"attempt {attempt!r} is outside the resumable bound"
    if not isinstance(record.get("task"), str) or not record["task"]:
        return False, "record carries no correction task"
    return True, ""


# ---------------------------------------------------------------- stage 1
def stage_requirements(repo_root, state, issue):
    stage = "requirements"
    if state["stages"][stage]["status"] == "passed" and state.get("a1_bundle_verified"):
        print(f"[{stage}] already passed with verified A1 bundle, skipping")
        return True
    # A corrected requirements contract invalidates dependent checkpoints.
    if not state.get("a1_bundle_verified"):
        for dependent in ("design", "implementation", "testing", "release", "review"):
            state["stages"][dependent] = {"status": "pending"}
        controller.record(state, "A3-profile A1 validation required; downstream checkpoints invalidated")
    controller.set_stage(state, stage, "running")
    usage = load_usage(state)
    skill = prompts.load_skill(repo_root)
    system = prompts.SPEC_SYSTEM + "\n\n--- REQUIREMENTS-LEDGER SKILL ---\n" + skill
    task = (f"Write the requirements specification for this GitHub issue "
            f"(issue #{issue['number']}).\n"
            + prompts.untrusted("ISSUE TITLE", issue.get("title", ""))
            + prompts.untrusted("ISSUE BODY", issue.get("body", "")))

    original_task = task
    # Durable correction recovery: a prior run killed during
    # self-correction left a bound record; resume its exact task and
    # attempt index. Anything unknown discards the record (fail closed).
    start_attempt = 1
    pending = load_correction(repo_root, stage)
    if pending is not None:
        binds, why = correction_binds(pending, stage, issue["number"],
                                      system, original_task)
        if binds:
            start_attempt = pending["attempt"]
            task = pending["task"]
            controller.record(
                state, f"{stage}: resuming persisted correction "
                       f"attempt {start_attempt}")
        else:
            # An unknown record does not grant another pair of attempts.
            return fail(repo_root, state, stage,
                        "correction recovery refused: " + why)
        controller.save_state(repo_root, state)

    def persist():
        # After every successful response/tool action and before every
        # judge call, counters hit disk: a SIGTERM retains known usage.
        store_usage(state, usage)
        controller.save_state(repo_root, state)

    for attempt in range(start_attempt, CORRECTION_MAX_ATTEMPTS + 1):
        result, transcript, err = agent.run_agent(
            "SpecWriter", config.MODEL_SPEC, system, task, repo_root, usage,
            stage=stage, on_progress=persist)
        persist()
        # Every attempt's transcript is preserved under its own artifact
        # name; later attempts never overwrite a prior attempt's record.
        transcript_text = json.dumps(transcript, indent=2)[:200000]
        transcript_id = _sha(transcript_text)[:16]
        execution_id = os.environ.get("GITHUB_RUN_ID", "local")
        execution_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        write_artifact(repo_root,
                       f"transcript_{stage}_attempt{attempt}_"
                       f"{execution_id}_{execution_attempt}_{transcript_id}.json",
                       transcript_text)
        if err:
            return fail(repo_root, state, stage,
                        f"agent error: {err}", transcript)
        spec_path = os.path.join(config.ARTIFACTS_DIR, "spec.md")
        if not os.path.isfile(os.path.join(repo_root, spec_path)):
            problems = ["agent finished without writing spec.md"]
            task = ("You finished without writing .autose/artifacts/spec.md. "
                    "Write it now, then finish.")
            if attempt < CORRECTION_MAX_ATTEMPTS:
                save_correction(repo_root, {
                    "schema": CORRECTION_SCHEMA, "stage": stage,
                    "issue": issue["number"], "attempt": attempt + 1,
                    "task": task,
                    "original_task_sha256": _sha(original_task),
                    "system_sha256": _sha(system),
                    "harness_sha256": call_log.harness_digest()})
            continue
        spec = read_file(repo_root, spec_path)
        ok, problems = checks.lint_spec(spec)
        aok, aproblems, adocs = a1_checks.check_a1_bundle(repo_root)
        problems += aproblems
        ok = ok and aok
        persist()
        ajok, ajreason = judge(repo_root, usage,
            prompts.A3_REUSE_PROFILE + "\nAudit A3-profile A1 compliance, not just file presence. Require all C1-C4, K1-K3, "
            "R-1 to R-3, F1-F2, T1-T4, E1-E5 checks to be substantively justified. "
            "Every requirement must link real source statements; ASSUMED/INFERRED items "
            "cannot be READY. No invented priorities, numbers or source evidence. "
            "Every ambiguity, question and conflict needs affected IDs/default provenance. "
            "Coverage topics must be covered/open/N-A with reason. Validation needs basis/gate "
            "counts, actual tool outcomes and human next steps when needed. "
            "Do not reject solely for absent MCP invocation or MCP-gap boilerplate. "
            "Reject unsupported readiness or superficial PASS claims. An honest NOT READY "
            "verdict can meet documentation integrity if uncertainty is kept explicit.",
            "\n\n".join(k+":\n"+v for k,v in adocs.items()), stage=stage) if aok else (False, 'A1 structural checks failed')
        if not ajok:
            ok = False
            problems.append('A1 semantic validation: ' + ajreason)
        persist()
        jok, jreason = judge(repo_root, usage,
                             "Every acceptance criterion in this spec is "
                             "testable: a developer who did not write it can "
                             "turn it into a pass/fail test.",
                             spec, stage=stage)
        persist()
        if ok and jok:
            state["a1_bundle_verified"] = True
            clear_correction(repo_root, stage)
            write_transcript(repo_root, stage, transcript)
            controller.set_stage(state, stage, "passed", artifact=spec_path,
                                 summary=result.get("summary", ""))
            return True
        problems = problems + ([f"judge: {jreason}"] if not jok else [])
        task = (original_task + "\nThe specification failed its checks. Read the existing spec.md, fix it, and finish."
                "\nProblems:\n- " + "\n- ".join(problems))
        if attempt < CORRECTION_MAX_ATTEMPTS:
            save_correction(repo_root, {
                "schema": CORRECTION_SCHEMA, "stage": stage,
                "issue": issue["number"], "attempt": attempt + 1,
                "task": task,
                "original_task_sha256": _sha(original_task),
                "system_sha256": _sha(system),
                "harness_sha256": call_log.harness_digest()})
    save_correction(repo_root, {
        "schema": CORRECTION_SCHEMA, "stage": stage,
        "issue": issue["number"], "attempt": CORRECTION_MAX_ATTEMPTS + 1,
        "task": task, "original_task_sha256": _sha(original_task),
        "system_sha256": _sha(system),
        "harness_sha256": call_log.harness_digest(), "exhausted": True})
    write_transcript(repo_root, stage, transcript)
    return fail(repo_root, state, stage,
                "checks failed after self-correction: " + "; ".join(problems),
                transcript)


# ---------------------------------------------------------------- stage 2
def stage_design(repo_root, state, issue):
    stage = "design"
    if state["stages"][stage]["status"] == "passed":
        print(f"[{stage}] already passed, skipping")
        return True
    controller.set_stage(state, stage, "running")
    usage = load_usage(state)
    spec = read_file(repo_root, os.path.join(config.ARTIFACTS_DIR, "spec.md"))
    arch = read_file(repo_root, "ARCHITECTURE.md")
    system = prompts.DESIGN_SYSTEM
    task = ("Design the change for this approved specification.\n\n"
            f"--- spec.md ---\n{spec}\n\n"
            f"--- ARCHITECTURE.md ---\n{arch}\n\n"
            "Explore the repo with list_files/read_file, then write "
            ".autose/artifacts/design.md and finish.")

    task += review_feedback.task_feedback(repo_root)
    original_task = task
    for attempt in (1, 2):
        result, transcript, err = agent.run_agent(
            "Designer", config.MODEL_DESIGN, system, task, repo_root, usage,
            stage=stage)
        store_usage(state, usage)
        if err:
            return fail(repo_root, state, stage, f"agent error: {err}",
                        transcript)
        design_path = os.path.join(config.ARTIFACTS_DIR, "design.md")
        if not os.path.isfile(os.path.join(repo_root, design_path)):
            task = "You finished without writing .autose/artifacts/design.md. Write it now."
            problems = ["agent finished without writing design.md"]
            continue
        design = read_file(repo_root, design_path)
        ok, problems = checks.check_design(design, repo_root)
        jok, jreason = judge(repo_root, usage,
                             "This design names the concrete files and "
                             "functions to change and respects the "
                             "architecture constraints it cites.",
                             design, stage=stage)
        store_usage(state, usage)
        if ok and jok:
            write_transcript(repo_root, stage, transcript)
            controller.set_stage(state, stage, "passed", artifact=design_path,
                                 summary=result.get("summary", ""))
            return True
        problems = problems + ([f"judge: {jreason}"] if not jok else [])
        task = (original_task + "\nThe design failed its checks. Read the existing design.md, fix it, and finish."
                "\nProblems:\n- " + "\n- ".join(problems))
    write_transcript(repo_root, stage, transcript)
    return fail(repo_root, state, stage,
                "checks failed after self-correction: " + "; ".join(problems),
                transcript)


# ------------------------------------------------------------- stages 3+4
def stage_develop(repo_root, state, issue):
    """Implementation + testing with the bounded fix loop (ADR-002)."""
    for stage in ("implementation", "testing"):
        if state["stages"][stage]["status"] == "passed":
            print(f"[{stage}] already passed, skipping")
    usage = load_usage(state)
    spec = read_file(repo_root, os.path.join(config.ARTIFACTS_DIR, "spec.md"))
    design = read_file(repo_root, os.path.join(config.ARTIFACTS_DIR,
                                               "design.md"))
    feedback = None

    while True:
        if state["stages"]["implementation"]["status"] != "passed" or feedback:
            controller.set_stage(state, "implementation", "running")
            task = ("Implement this design.\n\n"
                    f"--- design.md ---\n{design}\n\n"
                    f"--- acceptance criteria (from spec.md) ---\n{spec}\n")
            task += review_feedback.task_feedback(repo_root)
            prior_reason = state["stages"]["implementation"].get("reason")
            if prior_reason:
                task += "\nPREVIOUS IMPLEMENTATION FAILURE: " + prior_reason
            task += ("\nYou must actually change source to implement the design. "
                     "A status check is not completion. Do not finish with an "
                     "empty files_changed list. Use a short Python editing command "
                     "if writing an entire large source file would be wasteful. "
                     "Preserve unrelated code and verify the resulting diff.")
            if feedback:
                task += ("\n--- PREVIOUS ATTEMPT FAILED TESTING - fix it ---\n"
                         + feedback)
            result, transcript, err = agent.run_agent(
                "Developer", config.MODEL_DEVELOP, prompts.DEVELOP_SYSTEM,
                task, repo_root, usage, stage="implementation")
            store_usage(state, usage)
            write_transcript(repo_root, "implementation", transcript)
            if err:
                return fail(repo_root, state, "implementation",
                            f"agent error: {err}", transcript)
            if result.get("blocked"):
                return fail(repo_root, state, "implementation",
                            f"developer blocked: {result.get('reason')}",
                            transcript)
            changed = git_changed_files(repo_root)
            # A successful import of unchanged code is not implementation.
            source_diff = subprocess.run(
                ["git", "diff", "origin/main", "--", "tinydb"],
                cwd=repo_root, capture_output=True, text=True, check=True).stdout
            if not source_diff.strip():
                return fail(repo_root, state, "implementation",
                            "no source change under tinydb compared with main; "
                            "build of unchanged code is insufficient", transcript)
            ok, msg = checks.check_build(repo_root, changed)
            if not ok:
                feedback = f"The code does not build:\n{msg}"
                if bump_cycle(repo_root, state):
                    return fail(repo_root, state, "implementation",
                                "build still failing after max fix cycles",
                                transcript)
                continue
            controller.set_stage(state, "implementation", "passed",
                                 summary=result.get("summary", ""))
            diff = make_diff(repo_root)
            write_artifact(repo_root, "diff.patch", diff or "(no diff)")

        # ---- testing
        controller.set_stage(state, "testing", "running")
        diff = read_file(repo_root, os.path.join(config.ARTIFACTS_DIR,
                                                 "diff.patch"))
        task = ("Write tests for this specification's acceptance criteria and "
                "run the full suite.\n\n"
                f"--- acceptance criteria (from spec.md) ---\n{spec}\n\n"
                f"--- the change under test (diff) ---\n{diff[:20000]}\n"
                "If tests_autose already exists after a failed attempt, inspect "
                "and retain useful existing tests. Check every acceptance "
                "criterion, add missing tests, run the suite, then finish. "
                "Existing files are not proof that the tests pass.")
        result, transcript, err = agent.run_agent(
            "Tester", config.MODEL_TEST, prompts.TEST_SYSTEM, task, repo_root,
            usage, stage="testing")
        store_usage(state, usage)
        write_transcript(repo_root, "testing", transcript)
        if err:
            return fail(repo_root, state, "testing", f"agent error: {err}",
                        transcript)

        test_files = sorted(
            os.path.join("tests_autose", f)
            for f in os.listdir(os.path.join(repo_root, "tests_autose"))
            if f.endswith(".py")
        ) if os.path.isdir(os.path.join(repo_root, "tests_autose")) else []
        if not test_files:
            feedback = "The Tester wrote no tests under tests_autose/."
            if bump_cycle(repo_root, state):
                return fail(repo_root, state, "testing",
                            "no tests written after max fix cycles",
                            transcript)
            state["stages"]["implementation"]["status"] = "pending"
            continue

        ok, msg, full_out = checks.run_tests(repo_root, test_files)
        # Passing a subset is not passing the stage's every-criterion check.
        if result.get("criteria_untestable"):
            ok = False
        report = (f"# Test report\n\nTests written: "
                  f"{', '.join(test_files)}\n\nVerdict: "
                  f"{'PASS' if ok else 'FAIL'}\n\n```\n{msg}\n```\n")
        if result.get("criteria_untestable"):
            report += ("\n## Untestable criteria (reported by Tester)\n- "
                       + "\n- ".join(result["criteria_untestable"]) + "\n")
        write_artifact(repo_root, "test_report.md", report)
        write_artifact(repo_root, "pytest_full_output.txt", full_out)
        if result.get("criteria_untestable"):
            return fail(repo_root, state, "testing",
                        "acceptance criteria remain untested: "
                        + "; ".join(str(item) for item in result["criteria_untestable"])
                        + "; see test_report.md", transcript)
        if ok:
            baseline_ok, baseline_out = checks.baseline_regression_check(repo_root, test_files)
            write_artifact(repo_root, "baseline_regression_output.txt", baseline_out)
            if not baseline_ok:
                return fail(repo_root, state, "testing",
                            "new tests did not demonstrate behavioral failure on main baseline; "
                            "see baseline_regression_output.txt", transcript)
            controller.set_stage(state, "testing", "passed",
                                 artifact=os.path.join(config.ARTIFACTS_DIR,
                                                       "test_report.md"))
            return True
        feedback = (f"Tests are failing. Tester reported: "
                    f"{json.dumps(result.get('failures', []))[:2000]}\n"
                    f"pytest output:\n{msg}")
        if bump_cycle(repo_root, state):
            return fail(repo_root, state, "testing",
                        "tests still failing after max fix cycles; "
                        "see test_report.md", transcript)
        state["stages"]["implementation"]["status"] = "pending"


def bump_cycle(repo_root, state):
    state["fix_cycles"] = state.get("fix_cycles", 0) + 1
    controller.record(state, f"fix cycle {state['fix_cycles']}")
    controller.save_state(repo_root, state)
    return state["fix_cycles"] >= config.MAX_FIX_CYCLES


# ---------------------------------------------------------------- stage 6
def stage_review(repo_root, state, issue, pr_number):
    stage = "review"
    if state["stages"][stage]["status"] == "passed":
        print(f"[{stage}] already passed, skipping")
        return True
    controller.set_stage(state, stage, "running")
    usage = load_usage(state)
    # Pipeline artifacts are versioned for audit, not reviewer input.
    proc = subprocess.run([
        "git", "diff", "origin/main...HEAD", "--", ".",
        ":(exclude).autose", ":(exclude)experiment", ":(exclude)results",
        ":(exclude)workflow", ":(exclude)architecture", ":(exclude).github",
        ":(exclude)report.pdf", ":(exclude)demo.mp4", ":(exclude)README.md"],
        cwd=repo_root, capture_output=True, text=True, check=True)
    diff = proc.stdout
    task = ("Review this pull request.\n"
            + prompts.untrusted("ISSUE TITLE", issue.get("title", ""))
            + prompts.untrusted("ISSUE BODY", issue.get("body", ""))
            + f"\n--- PROPOSED DIFF ---\n{diff[:30000]}\n\n"
            "The repo checkout is at the PR head. Review, then finish with "
            "the verdict object.")
    with tempfile.TemporaryDirectory(prefix="autose-review-") as clean:
        review_root = os.path.join(clean, "repo")
        shutil.copytree(repo_root, review_root, ignore=shutil.ignore_patterns(
            ".git", ".autose", "experiment", "results", "workflow",
            "architecture", ".github", "report.pdf", "demo.mp4", "README.md",
            "__pycache__", ".pytest_cache"))
        try:
            result, transcript, err = agent.run_agent(
                "Reviewer", config.MODEL_REVIEW, prompts.REVIEW_SYSTEM, task,
                review_root, usage, read_only=True, stage=stage)
        finally:
            # Preserve partial and failed review attempts before cleanup too.
            call_log.merge_into(review_root, repo_root)
    store_usage(state, usage)
    write_transcript(repo_root, stage, transcript)
    if err:
        return fail(repo_root, state, stage, f"agent error: {err}", transcript)

    ok, problems = checks.validate_review_verdict(result)
    if not ok:
        return fail(repo_root, state, stage,
                    "verdict failed schema: " + "; ".join(problems),
                    transcript)

    review_md = render_review(result, pr_number)
    write_artifact(repo_root, "review.md", review_md)
    verdict_path = os.path.join(config.ARTIFACTS_DIR, "review_verdict.json")
    write_artifact(repo_root, "review_verdict.json", json.dumps(result,
                                                                  indent=2))
    controller.set_stage(state, stage, "passed",
                         artifact=os.path.join(config.ARTIFACTS_DIR,
                                               "review.md"),
                         verdict=result.get("verdict"))
    return True


def render_review(result, pr_number):
    lines = [f"# Review of PR #{pr_number}", "",
             f"Verdict: **{result.get('verdict')}**", ""]
    if result.get("summary"):
        lines += ["## Summary", "", result["summary"], ""]
    if result.get("findings"):
        lines += ["## Findings", ""]
        for f in result["findings"]:
            loc = f.get("file", "?")
            if f.get("line"):
                loc += f":{f['line']}"
            lines.append(f"- [{f.get('severity', '?')}] `{loc}` - "
                         f"{f.get('issue', '')}")
        lines.append("")
    if result.get("classification"):
        lines += [f"Classification: **{result['classification']}** "
                  f"(sends work back to "
                  f"{'design' if result['classification'] == 'approach' else 'implementation'})",
                  ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- helpers
def write_transcript(repo_root, stage, transcript):
    write_artifact(repo_root, f"transcript_{stage}.json",
                   json.dumps(transcript, indent=2)[:200000])


def fail(repo_root, state, stage, reason, transcript=None):
    """A stage that cannot pass explains why in its artifact (brief's rule)
    and the run stops."""
    write_artifact(repo_root, f"{stage}_FAILED.md",
                   f"# Stage {stage} failed\n\n{reason}\n")
    controller.set_stage(state, stage, "failed", reason=reason)
    controller.save_state(repo_root, state)
    print(f"[{stage}] FAILED: {reason}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["requirements", "design", "develop", "review"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--issue-file", required=True)
    ap.add_argument("--pr-number", default="0")
    args = ap.parse_args()

    repo_root = os.path.abspath(args.repo)
    with open(args.issue_file, "r", encoding="utf-8") as f:
        issue = json.load(f)

    state = controller.load_state(repo_root)
    if state is None:
        state = controller.init_state(issue["number"],
                                      f"autose/issue-{issue['number']}")

    exhausted = controller.budgets_exhausted(state)
    if exhausted and args.stage != "review":
        controller.save_state(repo_root, state)
        print(f"run stopped: {exhausted}")
        sys.exit(1)

    if args.stage == "requirements":
        ok = stage_requirements(repo_root, state, issue)
    elif args.stage == "design":
        ok = stage_design(repo_root, state, issue)
    elif args.stage == "develop":
        ok = stage_develop(repo_root, state, issue)
    else:
        ok = stage_review(repo_root, state, issue, args.pr_number)

    controller.save_state(repo_root, state)
    # Export cumulative state alongside artifacts for external evidence audit.
    # It is cumulative, never sum these snapshots across resumed runs.
    write_artifact(repo_root, "state_snapshot.json", json.dumps(state, indent=2))
    write_artifact(repo_root, "usage.json", json.dumps({
        "scope": "cumulative branch state including prior recovered stages",
        "stage": args.stage, "usage": state.get("usage", {}),
    }, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
