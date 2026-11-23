"""Mechanical stage checks (ADR-007).

These functions - never the agents - decide pass/fail. The LLM judge for
the two semantic stages lives in run_stage.py and can only veto.
"""

import os
import re
import subprocess

# Vague words banned from acceptance criteria (A1 skill, rule T3).
VAGUE_WORDS = [
    "fast", "quick", "easy", "user-friendly", "intuitive", "robust",
    "secure", "scalable", "flexible", "seamless", "modern",
    "enterprise-grade", "state-of-the-art", "as appropriate",
    "and so on", "minimal", "reasonable",
]

GWT_RE = re.compile(r"\b(given|when|then)\b", re.I)
MEASURE_RE = re.compile(r"\b\d+(\.\d+)?\s*(ms|s|sec|seconds|minutes|%|percent|"
                        r"times|rows|documents|bytes|calls|errors?)\b", re.I)
AC_RE = re.compile(r"^\s*(?:[-*]|\d+[.)]|AC-\S+[:.)])\s*(.+)$")


def extract_acceptance_criteria(spec_text):
    """Pull AC lines out of the spec's acceptance-criteria section."""
    lines = spec_text.splitlines()
    in_section = False
    acs = []
    for line in lines:
        if re.match(r"^#{1,4}\s", line):
            in_section = bool(re.search(r"acceptance criteria", line, re.I))
            continue
        if in_section:
            m = AC_RE.match(line)
            if m and m.group(1).strip():
                acs.append(m.group(1).strip())
    return acs


def lint_spec(spec_text):
    """Stage 1 check: every AC testable in form (given/when/then or a
    measurable threshold) and free of vague words."""
    problems = []
    acs = extract_acceptance_criteria(spec_text)
    if not acs:
        problems.append("no acceptance criteria found in spec.md")
        return False, problems
    for ac in acs:
        low = ac.lower()
        if not (GWT_RE.search(ac) or MEASURE_RE.search(ac)):
            problems.append(f"AC not in testable form: {ac[:90]}")
        for w in VAGUE_WORDS:
            if re.search(rf"\b{re.escape(w)}\b", low):
                problems.append(f"AC uses vague word '{w}': {ac[:90]}")
    return (not problems), problems


PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|txt|json|yml|yaml|cfg|toml))`")


def check_design(design_text, repo_root):
    """Stage 2 check: plan names files and functions; every named existing
    file exists (files may be explicitly marked NEW)."""
    problems = []
    paths = set(PATH_RE.findall(design_text))
    if not paths:
        problems.append("design.md names no files")
    new_marks = set(re.findall(r"`([A-Za-z0-9_./-]+\.\w+)`\s*\(?\s*NEW\s*\)?",
                               design_text, re.I))
    for rel in sorted(paths - new_marks):
        if rel.startswith((".github/", "workflow/")):
            problems.append(f"plan edits protected path {rel}")
            continue
        if not os.path.isfile(os.path.join(repo_root, rel)):
            problems.append(f"planned file does not exist and is not marked NEW: {rel}")
    if not re.search(r"def |function|method|class ", design_text, re.I):
        problems.append("design.md names no functions or classes to change")
    return (not problems), problems


def _run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=600)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def check_build(repo_root, changed_files):
    """Stage 3 check: changed files compile and the package imports."""
    py_files = [f for f in changed_files if f.endswith(".py")]
    if py_files:
        code, out = _run(["python", "-m", "compileall", "-q"] + py_files,
                         repo_root)
        if code != 0:
            return False, f"compileall failed:\n{out[-3000:]}"
    code, out = _run(["python", "-c", "import tinydb; print(tinydb.__version__)"],
                     repo_root)
    if code != 0:
        return False, f"package import failed:\n{out[-3000:]}"
    return True, "build OK"


def run_tests(repo_root, extra_paths=None):
    """Stage 4 check: run pytest (new tests first if given, then the suite)."""
    if extra_paths:
        code, out = _run(["python", "-m", "pytest", "-q"] + extra_paths,
                         repo_root)
        if code != 0:
            return False, f"new tests failed:\n{out[-4000:]}", out
    code, out = _run(["python", "-m", "pytest", "-q"], repo_root)
    if code != 0:
        return False, f"full suite failed:\n{out[-4000:]}", out
    return True, "all tests pass", out


def validate_review_verdict(obj):
    """Stage 6 check: the reviewer's verdict has the required schema, and
    every requested change cites a file."""
    problems = []
    if not isinstance(obj, dict):
        return False, ["verdict is not a JSON object"]
    if obj.get("verdict") not in ("approve", "request_changes"):
        problems.append("verdict must be 'approve' or 'request_changes'")
    findings = obj.get("findings")
    if not isinstance(findings, list):
        problems.append("findings must be a list")
        findings = []
    if obj.get("verdict") == "request_changes":
        if not findings:
            problems.append("request_changes with no findings")
        for f in findings:
            if not isinstance(f, dict) or not f.get("file") or not f.get("issue"):
                problems.append(f"finding lacks file/issue: {str(f)[:120]}")
        if obj.get("classification") not in ("approach", "code"):
            problems.append("classification must be 'approach' or 'code'")
    return (not problems), problems


def baseline_regression_check(repo_root, test_files):
    """Require generated behavior tests to fail against pinned baseline code.

    Tests run in a temporary git worktree, never with hidden acceptance tests.
    A collection/import error is not evidence of a behavioral regression.
    """
    import tempfile, shutil
    with tempfile.TemporaryDirectory(prefix="autose-baseline-") as root:
        base = os.path.join(root, "repo")
        subprocess.run(["git", "worktree", "add", "--detach", base, "origin/main"],
                       cwd=repo_root, check=True, capture_output=True)
        try:
            for rel in test_files:
                dest = os.path.join(base, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(os.path.join(repo_root, rel), dest)
            code, out = _run(["python", "-m", "pytest", "-q"] + test_files, base)
            ok = code == 1 and bool(re.search(r"\b[1-9]\d* failed\b", out))
            return ok, out
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", base],
                           cwd=repo_root, check=True, capture_output=True)
