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
import json
import os
import subprocess
import shutil
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent
import checks
import config
import controller
import gemini
import prompts


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


def judge(repo_root, usage, question, document):
    """Advisory LLM judge for the two semantic checks (ADR-007)."""
    task = (f"Property to verify: {question}\n\n"
            f"Document under review:\n```markdown\n{document[:20000]}\n```\n\n"
            f"Answer with one JSON object.")
    try:
        reply = gemini.generate(config.MODEL_JUDGE, prompts.JUDGE_SYSTEM,
                                [{"role": "user", "parts": [{"text": task}]}],
                                usage)
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


# ---------------------------------------------------------------- stage 1
def stage_requirements(repo_root, state, issue):
    stage = "requirements"
    if state["stages"][stage]["status"] == "passed":
        print(f"[{stage}] already passed, skipping")
        return True
    controller.set_stage(state, stage, "running")
    usage = load_usage(state)
    skill = prompts.load_skill(repo_root)
    system = prompts.SPEC_SYSTEM + "\n\n--- REQUIREMENTS-LEDGER SKILL ---\n" + skill
    task = (f"Write the requirements specification for this GitHub issue "
            f"(issue #{issue['number']}).\n"
            + prompts.untrusted("ISSUE TITLE", issue.get("title", ""))
            + prompts.untrusted("ISSUE BODY", issue.get("body", "")))

    original_task = task
    for attempt in (1, 2):
        result, transcript, err = agent.run_agent(
            "SpecWriter", config.MODEL_SPEC, system, task, repo_root, usage)
        store_usage(state, usage)
        if err:
            return fail(repo_root, state, stage,
                        f"agent error: {err}", transcript)
        spec_path = os.path.join(config.ARTIFACTS_DIR, "spec.md")
        if not os.path.isfile(os.path.join(repo_root, spec_path)):
            task = ("You finished without writing .autose/artifacts/spec.md. "
                    "Write it now, then finish.")
            problems = ["agent finished without writing spec.md"]
            continue
        spec = read_file(repo_root, spec_path)
        ok, problems = checks.lint_spec(spec)
        jok, jreason = judge(repo_root, usage,
                             "Every acceptance criterion in this spec is "
                             "testable: a developer who did not write it can "
                             "turn it into a pass/fail test.",
                             spec)
        store_usage(state, usage)
        if ok and jok:
            write_transcript(repo_root, stage, transcript)
            controller.set_stage(state, stage, "passed", artifact=spec_path,
                                 summary=result.get("summary", ""))
            return True
        problems = problems + ([f"judge: {jreason}"] if not jok else [])
        task = (original_task + "\nThe specification failed its checks. Read the existing spec.md, fix it, and finish."
                "\nProblems:\n- " + "\n- ".join(problems))
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

    original_task = task
    for attempt in (1, 2):
        result, transcript, err = agent.run_agent(
            "Designer", config.MODEL_DESIGN, system, task, repo_root, usage)
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
                             design)
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
            if feedback:
                task += ("\n--- PREVIOUS ATTEMPT FAILED TESTING - fix it ---\n"
                         + feedback)
            result, transcript, err = agent.run_agent(
                "Developer", config.MODEL_DEVELOP, prompts.DEVELOP_SYSTEM,
                task, repo_root, usage)
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
            usage)
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
        report = (f"# Test report\n\nTests written: "
                  f"{', '.join(test_files)}\n\nVerdict: "
                  f"{'PASS' if ok else 'FAIL'}\n\n```\n{msg}\n```\n")
        if result.get("criteria_untestable"):
            report += ("\n## Untestable criteria (reported by Tester)\n- "
                       + "\n- ".join(result["criteria_untestable"]) + "\n")
        write_artifact(repo_root, "test_report.md", report)
        write_artifact(repo_root, "pytest_full_output.txt", full_out)
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
        ":(exclude)report.pdf", ":(exclude)demo.mp4"],
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
            "architecture", ".github", "report.pdf", "demo.mp4",
            "__pycache__", ".pytest_cache"))
        result, transcript, err = agent.run_agent(
            "Reviewer", config.MODEL_REVIEW, prompts.REVIEW_SYSTEM, task,
            review_root, usage, read_only=True)
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
