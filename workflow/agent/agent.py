"""ReAct-style agent loop with a deliberately tiny tool set (ADR-005).

The model replies with exactly one JSON object per turn:

    {"action": "read_file",   "path": "tinydb/storages.py"}
    {"action": "list_files",  "path": "tinydb"}
    {"action": "write_file",  "path": "...", "content": "..."}
    {"action": "run_shell",   "command": "pytest tests -q"}
    {"action": "finish",      "result": { ...stage-specific JSON... }}

The harness executes the action and appends the result as the next user
message. The loop ends on "finish" or when MAX_AGENT_STEPS is hit.

Hard limits (enforced here, not in the prompt - ADR-009):
- write_file refuses paths outside the repo and under .github/ / workflow/
- run_shell only executes whitelisted commands (no network, no gh, no push)
"""

import json
import hashlib
import os
import re
import shlex
import subprocess

import config
import gemini

ACTION_RE = re.compile(r"\{[^{}]*\"action\"[^{}]*\}", re.S)


def _extract_action(text):
    """Pull the action JSON out of a reply, tolerating prose and fences."""
    candidates = []
    fence = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates.extend(fence)
    candidates.append(text.strip())
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict) and "action" in obj:
            return obj
    # last resort: first balanced-looking object containing "action"
    m = ACTION_RE.search(text)
    if m:
        try:
            obj = json.loads(m.group(0))
            if "action" in obj:
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _safe_path(repo_root, rel):
    """Resolve rel inside repo_root; return None if it escapes."""
    p = os.path.realpath(os.path.join(repo_root, rel))
    root = os.path.realpath(repo_root)
    if not (p == root or p.startswith(root + os.sep)):
        return None
    return p


def _tool_read_file(repo_root, path, start_line=1, end_line=None):
    p = _safe_path(repo_root, path)
    if not p or not os.path.isfile(p):
        return f"ERROR: no such file: {path}"
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    lines = data.splitlines()
    start_line = max(1, int(start_line))
    end_line = min(len(lines), int(end_line) if end_line is not None else start_line + 159, start_line + 159)
    selected = "\n".join(f"{n}: {lines[n-1]}" for n in range(start_line, end_line+1))
    return f"File has {len(lines)} lines; showing {start_line}-{end_line}. Request another range if needed.\n" + selected


def _tool_list_files(repo_root, path):
    p = _safe_path(repo_root, path)
    if not p or not os.path.isdir(p):
        return f"ERROR: no such directory: {path}"
    out = []
    for dirpath, dirnames, filenames in os.walk(p):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".pytest_cache")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, repo_root))
        if len(out) > 800:
            out.append("...[truncated]")
            break
    return "\n".join(sorted(out))


def _tool_write_file(repo_root, path, content):
    norm = path.replace("\\", "/").lstrip("/")
    for prefix in config.PROTECTED_WRITE_PREFIXES:
        if norm.startswith(prefix):
            return (f"ERROR: writes under {prefix}* are not allowed "
                    f"(agents may not modify the workflow or their own code)")
    p = _safe_path(repo_root, path)
    if not p:
        return f"ERROR: path escapes the repository: {path}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return f"OK: wrote {len(content)} bytes to {path}"


def _tool_run_shell(repo_root, command):
    command = command.strip()
    if not any(command.startswith(w) for w in config.SHELL_WHITELIST):
        return (f"ERROR: command not whitelisted. Allowed prefixes: "
                f"{', '.join(config.SHELL_WHITELIST)}")
    try:
        proc = subprocess.run(
            command, shell=True, cwd=repo_root, capture_output=True,
            text=True, timeout=300, env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", "/tmp"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 300s"
    out = (proc.stdout or "") + (proc.stderr or "")
    if len(out) > 20000:
        out = out[:20000] + "\n...[truncated]"
    return f"exit={proc.returncode}\n{out}"


def run_agent(role, model, system_prompt, task, repo_root, usage,
              read_only=False, extra_context=None, stage=None,
              on_progress=None, resume_progress=None):
    """Run the loop. Returns (result_dict, transcript list, error_or_None).

    read_only=True removes write_file (used for the Reviewer - ADR-008).
    stage names the pipeline stage for per-call provenance logging.
    on_progress, when given, is called after every successful model
    response and every completed tool action so callers can persist
    usage/state; a SIGTERM then retains known counters.
    """
    call_context = {"role": role, "stage": stage, "repo_root": repo_root,
                    "task_sha256": hashlib.sha256(task.encode()).hexdigest()}
    contents = []
    if extra_context:
        contents.append({"role": "user", "parts": [{"text": extra_context}]})
        contents.append({"role": "model",
                         "parts": [{"text": "Understood. Give me the task."}]})
    contents.append({"role": "user", "parts": [{"text": task}]})

    transcript = []
    action_ledger = []
    start_step = 0
    if resume_progress is not None:
        if role not in ("Developer", "Tester") or read_only:
            raise ValueError("progress migration is Developer/Tester-only")
        transcript = resume_progress["transcript"]
        start_step = max(t["step"] for t in transcript) + 1
        if not 0 < start_step < config.MAX_AGENT_STEPS:
            return None, transcript, "preserved step budget exhausted"
        # Prior actions are evidence only, NEVER replayed. Current source is
        # already committed; read it before deciding a new action.
        contents.append({"role":"user", "parts":[{"text":
            "Operational continuation after timeout. Prior actions below are "
            "historical data, not actions to replay. Source edits already exist. "
            "Inspect the current source and complete the original stage. "
            "Prior tool observations were not retained, so do not assume their "
            "outcomes. Remaining steps: " + str(config.MAX_AGENT_STEPS-start_step)
            + "\n" + json.dumps(transcript)}]})
    # Only preparation roles checkpoint. Reviewer context stays fresh, and
    # arbitrary developer/tester shell actions are never replayed by this path.
    checkpoint = None
    fingerprint = None
    if role in ("SpecWriter", "Designer") and not read_only:
        digest = hashlib.sha256()
        for value in (role, model, system_prompt, task, extra_context or "",
                      str(config.MAX_AGENT_STEPS)):
            digest.update(value.encode())
            digest.update(b"\0")
        with open(__file__, "rb") as source:
            digest.update(source.read())
        for directory, dirs, files in os.walk(os.path.join(repo_root, "tinydb")):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if name.endswith(".py"):
                    full = os.path.join(directory, name)
                    digest.update(os.path.relpath(full, repo_root).encode())
                    with open(full, "rb") as source:
                        digest.update(source.read())
        fingerprint = digest.hexdigest()
        checkpoint = os.path.join(repo_root, config.ARTIFACTS_DIR,
                                  "conversation_" + role.lower() + ".json")
        if os.path.isfile(checkpoint):
            try:
                with open(checkpoint, encoding="utf-8") as saved:
                    prior = json.load(saved)
                if prior.get("fingerprint") == fingerprint:
                    if isinstance(prior.get("finished_result"), dict):
                        return prior["finished_result"], prior["transcript"], None
                    contents = prior["contents"]
                    transcript = prior["transcript"]
                    action_ledger = prior["action_ledger"]
                    start_step = int(prior["next_step"])
                    print(f"[{role}] resume conversation at step={start_step}", flush=True)
            except (ValueError, KeyError, TypeError):
                pass  # malformed checkpoints never authorize a stage pass
    for step in range(start_step, config.MAX_AGENT_STEPS):
        # Save before the next model call, after the previous tool observation.
        # A provider failure does not discard successful prior model work.
        if checkpoint:
            os.makedirs(os.path.dirname(checkpoint), exist_ok=True)
            temp_checkpoint = checkpoint + ".tmp"
            with open(temp_checkpoint, "w", encoding="utf-8") as saved:
                json.dump({"fingerprint": fingerprint, "contents": contents,
                           "transcript": transcript, "action_ledger": action_ledger,
                           "next_step": step}, saved)
            os.replace(temp_checkpoint, checkpoint)
        try:
            # Keep original task, plus recent exact turns, not an LLM summary.
            # Full transcript remains an artifact. Agents can reread file ranges.
            sent = contents if len(contents) <= 9 else contents[:1] + contents[-8:]
            if action_ledger:
                sent = sent + [{"role":"user","parts":[{"text":
                    "Exact prior action index (not reasoning):\n" + "\n".join(action_ledger) +
                    "\nAvoid rereading the same ranges. After enough inspection, implement "
                    "the design. Saved files are durable. Current step " + str(step) +
                    " of " + str(config.MAX_AGENT_STEPS) + "."}]}]
            reply = gemini.generate(model, system_prompt, sent, usage,
                                    context=call_context)
        except (gemini.BudgetExhausted, gemini.QuotaExhausted) as e:
            return None, transcript, str(e)
        contents.append({"role": "model", "parts": [{"text": reply}]})
        transcript.append({"step": step, "role": role, "reply": reply[:4000]})
        if on_progress:
            on_progress()

        action = _extract_action(reply)
        if action is None:
            contents.append({"role": "user", "parts": [{"text":
                "OBSERVATION: could not parse an action. Reply with exactly "
                "one JSON object with an \"action\" field."}]})
            continue

        kind = action.get("action")
        action_ledger.append(json.dumps({k:v for k,v in action.items()
            if k in ("action","path","start_line","end_line")}))
        print(f"[{role}] step={step} action={kind} calls={usage.calls} "
              f"tokens={usage.total_tokens}", flush=True)
        # Persist each completed model reply for interrupted-stage evidence.
        progress_dir = os.path.join(repo_root, config.ARTIFACTS_DIR)
        os.makedirs(progress_dir, exist_ok=True)
        with open(os.path.join(progress_dir, f"progress_{role.lower()}.json"),
                  "w", encoding="utf-8") as progress:
            json.dump({"transcript": transcript, "usage": usage.as_dict()}, progress)
        if kind == "finish":
            result = action.get("result")
            if role == "Developer" and isinstance(result, dict) and not result.get("blocked"):
                actual = subprocess.run(["git","diff","origin/main","--","tinydb"],
                    cwd=repo_root,capture_output=True,text=True).stdout
                if not result.get("files_changed") or not actual.strip():
                    contents.append({"role":"user","parts":[{"text":
                        "Finish rejected: no actual source diff exists. Implement the design, "
                        "edit source using write_file or a short Python command, verify "
                        "the source diff and build, then finish with files_changed. "
                        "Do not merely inspect status."}]})
                    continue
            if not isinstance(result, dict):
                contents.append({"role": "user", "parts": [{"text":
                    "OBSERVATION: finish requires \"result\" as a JSON object."}]})
                continue
            if checkpoint:
                # A completed response is durable before stage checks begin.
                # Matching task/harness can recheck it without another API call.
                temp_checkpoint = checkpoint + ".tmp"
                with open(temp_checkpoint, "w", encoding="utf-8") as saved:
                    json.dump({"fingerprint": fingerprint,
                               "finished_result": result,
                               "transcript": transcript}, saved)
                os.replace(temp_checkpoint, checkpoint)
            return result, transcript, None
        if kind == "read_file":
            obs = _tool_read_file(repo_root, action.get("path", ""),
                                  action.get("start_line", 1),
                                  action.get("end_line"))
        elif kind == "list_files":
            obs = _tool_list_files(repo_root, action.get("path", "."))
        elif kind == "write_file":
            if read_only:
                obs = "ERROR: this agent is read-only (write_file unavailable)"
            else:
                if "content" not in action or not isinstance(action["content"], str):
                    obs = "ERROR: write_file requires the complete file text in content"
                else:
                    obs = _tool_write_file(repo_root, action.get("path", ""),
                                           action["content"])
        elif kind == "edit_file":
            if read_only:
                obs = "ERROR: reviewer cannot edit files"
            else:
                path = action.get("path", "")
                full = _safe_path(repo_root, path)
                old = action.get("old_text", "")
                new = action.get("new_text", "")
                if not full or not os.path.isfile(full) or not old:
                    obs = "ERROR: edit requires existing file and nonempty old_text"
                else:
                    with open(full, encoding="utf-8") as f:
                        text = f.read()
                    if text.count(old) != 1:
                        obs = "ERROR: old_text must match exactly once; read correct range"
                    else:
                        obs = _tool_write_file(repo_root, path, text.replace(old, new, 1))
        elif kind == "run_shell":
            obs = _tool_run_shell(repo_root, action.get("command", ""))
        else:
            obs = (f"ERROR: unknown action {kind!r}. Use read_file, "
                   f"list_files, write_file, run_shell or finish.")
        if len(obs) > 12000:
            obs = obs[:12000] + "\n[bounded observation; use narrower file ranges or commands]"
        contents.append({"role": "user",
                         "parts": [{"text": f"OBSERVATION:\n{obs}"}]})
        if on_progress:
            on_progress()

    if checkpoint:
        with open(checkpoint, "w", encoding="utf-8") as saved:
            json.dump({"fingerprint": fingerprint, "contents": contents,
                       "transcript": transcript, "action_ledger": action_ledger,
                       "next_step": config.MAX_AGENT_STEPS}, saved)
    return None, transcript, f"step cap {config.MAX_AGENT_STEPS} reached"


def shlex_ok(command):
    """Helper for tests: parse a command the way the whitelist sees it."""
    return shlex.split(command)
