"""Per-call provenance log for every model call (schema autose-call/1).

One JSON line per HTTP attempt in `.autose/artifacts/calls.jsonl` on the
work branch. This exists because the branch-level `usage.models` counter
mixes every role and records only the endpoint requested, so neither
per-role attribution nor responding-model evidence can be recovered from
it. Each record carries:

- call_id: uuid4, globally unique per attempt (dedupe key; a record is
  written exactly once per attempt, success or failure).
- ts: UTC timestamp of the attempt.
- run_id / run_attempt / job: GitHub Actions identity from the
  environment (null outside Actions).
- stage / role: pipeline context from the caller.
- requested_model: the endpoint the role was configured to use.
- attempted_model: the endpoint this attempt actually went to (differs
  from requested on a fallback attempt).
- provider_model_version: the response body's modelVersion when the
  provider returns one, else null. Never inferred from configuration:
  an env pin is a request, not a response.
- status: "success" or "error"; error carries the exception type and a
  short message (no key material ever appears: the key travels in a
  header and is never formatted into errors).
- fallback: attempted_model != requested_model.
- response_id: provider response id when present, else null.
- usage: token metadata from the provider on success; null on failure
  (failed attempts never record invented zero tokens).
- system_sha256 / task_sha256: hashes of the rendered system prompt and
  the role's initial task text. Raw prompts are never logged.
- harness_sha / branch_head: the workflow checkout commit (env) and the
  work branch HEAD at call time.

Backwards compatible: Usage/state.usage/usage.json are untouched; this
log is an additional artifact. No API keys and no raw prompt text are
ever written here.
"""

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone

import config

SCHEMA = "autose-call/1"

_branch_head_cache = {}
_harness_digest_cache = None


def categorize_error(exc):
    """Safe error identity: category + HTTP status + finish reason only.

    Exception MESSAGES are never recorded: provider error bodies can echo
    request content or key material, and truncation is not sanitization.
    """
    name = type(exc).__name__
    status = getattr(exc, "http_status", None)
    finish = getattr(exc, "finish_reason", None)
    if name == "_RateLimited":
        category = "rate_limited"
    elif name == "_Transient":
        category = getattr(exc, "category", None) or "transient"
    elif name == "RuntimeError" and status is not None:
        category = "http_client_error"
    else:
        category = "error"
    return {"category": category, "http_status": status,
            "finish_reason": finish}


def harness_digest():
    """SHA-256 over the EXECUTING harness file contents.

    Hashes every module next to this file (the trusted agent set, however
    it was assembled - full checkout or the reviewer's isolated copy) plus
    the autose workflow definitions when the repository layout is present.
    A runner env sha is a claim about a ref, not proof of the executing
    bytes; this digest is.
    """
    global _harness_digest_cache
    if _harness_digest_cache:
        return _harness_digest_cache
    here = os.path.dirname(os.path.abspath(__file__))
    entries = []
    for name in sorted(os.listdir(here)):
        if name.endswith(".py"):
            path = os.path.join(here, name)
            with open(path, "rb") as fh:
                entries.append(f"agent/{name} "
                               f"{hashlib.sha256(fh.read()).hexdigest()}")
    workflows = os.path.normpath(
        os.path.join(here, os.pardir, os.pardir, ".github", "workflows"))
    if os.path.isdir(workflows):
        for name in sorted(os.listdir(workflows)):
            if name.startswith("autose") and name.endswith(".yml"):
                with open(os.path.join(workflows, name), "rb") as fh:
                    entries.append(f"workflows/{name} "
                                   f"{hashlib.sha256(fh.read()).hexdigest()}")
    _harness_digest_cache = hashlib.sha256(
        "\n".join(sorted(entries)).encode()).hexdigest()
    return _harness_digest_cache


def merge_into(src_root, dst_root):
    """Append call records from src_root's log into dst_root's, deduped by
    call_id. Used when a stage ran against a temporary copy (the Reviewer's
    isolated checkout) whose directory is deleted afterwards."""
    try:
        src = os.path.join(src_root, config.ARTIFACTS_DIR, "calls.jsonl")
        if not os.path.isfile(src):
            return
        dst = os.path.join(dst_root, config.ARTIFACTS_DIR, "calls.jsonl")
        seen = set()
        if os.path.isfile(dst):
            with open(dst, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        seen.add(json.loads(line).get("call_id"))
                    except json.JSONDecodeError:
                        continue
        merged = 0
        with open(src, encoding="utf-8") as fh:
            lines = fh.readlines()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "a", encoding="utf-8") as out:
            for line in lines:
                try:
                    cid = json.loads(line).get("call_id")
                except json.JSONDecodeError:
                    continue
                if cid and cid not in seen:
                    out.write(line if line.endswith("\n") else line + "\n")
                    seen.add(cid)
                    merged += 1
        return merged
    except Exception as exc:
        raise RuntimeError("call provenance merge failed") from exc


def sha256_text(text):
    return hashlib.sha256((text or "").encode()).hexdigest()


def _branch_head(repo_root):
    if repo_root in _branch_head_cache:
        return _branch_head_cache[repo_root]
    head = None
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root,
            capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            head = out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        head = None
    _branch_head_cache[repo_root] = head
    return head


def base_record(context, requested_model):
    context = context or {}
    return {
        "schema": SCHEMA,
        "call_id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "job": os.environ.get("GITHUB_JOB"),
        "stage": context.get("stage"),
        "role": context.get("role"),
        "requested_model": requested_model,
        "system_sha256": context.get("system_sha256"),
        "task_sha256": context.get("task_sha256"),
        "request_contents_sha256": context.get("request_contents_sha256"),
        "harness_digest": harness_digest(),
        "runner_ref": os.environ.get("GITHUB_SHA"),
        "branch_head": _branch_head(context["repo_root"])
        if context.get("repo_root") else None,
    }


def record(context, requested_model, attempted_model, status,
           usage_metadata=None, error=None, provider_model_version=None,
           response_id=None):
    """Append one attempt record. Never raises: logging must not fail a run.

    error must come from categorize_error (category/status/finish reason);
    raw exception text is never accepted here.
    """
    try:
        if error is not None:
            error = {k: error.get(k) for k in
                     ("category", "http_status", "finish_reason")}
        rec = base_record(context, requested_model)
        rec.update({
            "attempted_model": attempted_model,
            "provider_model_version": provider_model_version,
            "status": status,
            "fallback": attempted_model != requested_model,
            "response_id": response_id,
            "usage": usage_metadata,
            "error": error,
        })
        repo_root = (context or {}).get("repo_root")
        if not repo_root:
            return
        path = os.path.join(repo_root, config.ARTIFACTS_DIR, "calls.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception as exc:
        raise RuntimeError("call provenance write failed") from exc
