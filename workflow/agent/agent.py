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


def _tool_read_file(repo_root, path):
    p = _safe_path(repo_root, path)
    if not p or not os.path.isfile(p):
        return f"ERROR: no such file: {path}"
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    if len(data) > 60000:
        data = data[:60000] + "\n...[truncated]"
    return data


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
              read_only=False, extra_context=None):
    """Run the loop. Returns (result_dict, transcript list, error_or_None).

    read_only=True removes write_file (used for the Reviewer - ADR-008).
    """
    contents = []
    if extra_context:
        contents.append({"role": "user", "parts": [{"text": extra_context}]})
        contents.append({"role": "model",
                         "parts": [{"text": "Understood. Give me the task."}]})
    contents.append({"role": "user", "parts": [{"text": task}]})

    transcript = []
    for step in range(config.MAX_AGENT_STEPS):
        try:
            reply = gemini.generate(model, system_prompt, contents, usage)
        except (gemini.BudgetExhausted, gemini.QuotaExhausted) as e:
            return None, transcript, str(e)
        contents.append({"role": "model", "parts": [{"text": reply}]})
        transcript.append({"step": step, "role": role, "reply": reply[:4000]})

        action = _extract_action(reply)
        if action is None:
            contents.append({"role": "user", "parts": [{"text":
                "OBSERVATION: could not parse an action. Reply with exactly "
                "one JSON object with an \"action\" field."}]})
            continue

        kind = action.get("action")
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
            if not isinstance(result, dict):
                contents.append({"role": "user", "parts": [{"text":
                    "OBSERVATION: finish requires \"result\" as a JSON object."}]})
                continue
            return result, transcript, None
        if kind == "read_file":
            obs = _tool_read_file(repo_root, action.get("path", ""))
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
        elif kind == "run_shell":
            obs = _tool_run_shell(repo_root, action.get("command", ""))
        else:
            obs = (f"ERROR: unknown action {kind!r}. Use read_file, "
                   f"list_files, write_file, run_shell or finish.")
        contents.append({"role": "user",
                         "parts": [{"text": f"OBSERVATION:\n{obs}"}]})

    return None, transcript, f"step cap {config.MAX_AGENT_STEPS} reached"


def shlex_ok(command):
    """Helper for tests: parse a command the way the whitelist sees it."""
    return shlex.split(command)
