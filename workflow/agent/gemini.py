"""Minimal Gemini REST client (stdlib only).

Why no SDK (ADR-005): the harness must run anywhere with zero install, and a
hand-rolled client makes retries, fallbacks and token accounting explicit.

The API key is read from the GEMINI_API_KEY environment variable and is never
printed, logged or embedded in a URL (it travels in the x-goog-api-key
header). Token usage is taken from the API's own usageMetadata so the cost
reporting required by the assignment is measured, not estimated.
"""

import json
import http.client
import os
import time
import urllib.error
import urllib.request

import config

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_LAST_REQUEST = 0.0


class QuotaExhausted(Exception):
    """Raised when every retry and the fallback tier are rate-limited."""


class BudgetExhausted(Exception):
    """Raised when the per-run token budget (ADR-009) would be exceeded."""


class Usage:
    """Cumulative token accounting for one workflow run."""

    def __init__(self, prior=None):
        prior = prior or {}
        self.prompt_tokens = prior.get("prompt_tokens", 0)
        self.completion_tokens = prior.get("completion_tokens", 0)
        self.total_tokens = prior.get("total_tokens", 0)
        self.calls = prior.get("calls", 0)
        self.fallbacks = prior.get("fallbacks", 0)
        self.models = prior.get("models", {})

    def record(self, metadata):
        self.prompt_tokens += metadata.get("promptTokenCount", 0)
        self.completion_tokens += metadata.get("candidatesTokenCount", 0)
        self.total_tokens += metadata.get("totalTokenCount", 0)
        self.calls += 1

    def as_dict(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
            "fallbacks": self.fallbacks,
            "models": self.models,
        }


def _post(model, payload, api_key):
    global _LAST_REQUEST
    time.sleep(max(0.0, 5.0 - (time.monotonic() - _LAST_REQUEST)))
    _LAST_REQUEST = time.monotonic()
    url = f"{API_BASE}/{model}:generateContent"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        if e.code == 429:
            raise _RateLimited(body)
        if 500 <= e.code < 600:
            raise _Transient(f"Gemini API error {e.code}: {body}")
        raise RuntimeError(f"Gemini API error {e.code}: {body}")
    except (TimeoutError, ConnectionError, urllib.error.URLError,
            http.client.RemoteDisconnected) as e:
        raise _Transient(f"transport failure: {type(e).__name__}: {e}") from e


class _RateLimited(Exception):
    pass


class _Transient(Exception):
    """Retryable 5xx from the API, or an empty/candidate-less reply."""



def response_schema(system_prompt):
    """Constrain JSON-as-data actions; no native provider tools are used."""
    string = {"type": "STRING"}
    strings = {"type": "ARRAY", "items": string}
    boolean = {"type": "BOOLEAN"}
    def obj(properties, required=()):
        return {"type": "OBJECT", "properties": properties,
                "required": list(required)}
    if '"pass": true|false' in system_prompt:
        return obj({"pass": boolean, "reasons": strings}, ("pass", "reasons"))
    finding = obj({"file": string, "line": {"type": "INTEGER"},
                   "issue": string, "severity": string})
    failure = obj({"criterion": string, "error": string})
    result = obj({
        "summary": string, "files": strings, "files_changed": strings,
        "acceptance_criteria": strings, "assumptions": strings,
        "blocked": boolean, "reason": string, "notes_for_tester": string,
        "tests_written": strings, "all_pass": boolean,
        "failures": {"type": "ARRAY", "items": failure},
        "criteria_untestable": strings, "verdict": string,
        "findings": {"type": "ARRAY", "items": finding},
        "classification": {"type": "STRING", "nullable": True},
    })
    if "You are the Reviewer agent" in system_prompt:
        result = obj({
            "verdict": {"type": "STRING", "enum": ["approve", "request_changes"]},
            "findings": {"type": "ARRAY", "items": obj({
                "file": string, "line": {"type": "INTEGER"}, "issue": string,
                "severity": {"type": "STRING", "enum": ["blocker", "major", "minor"]}},
                ("file", "line", "issue", "severity"))},
            "classification": {"type": "STRING", "nullable": True},
            "summary": string,
        }, ("verdict", "findings", "classification", "summary"))
    def action(name, fields):
        return obj({"action": {"type": "STRING", "enum": [name]},
                    **fields}, ("action", *fields))
    return {"anyOf": [
        action("list_files", {"path": string}),
        obj({"action": {"type":"STRING","enum":["read_file"]}, "path":string,
             "start_line":{"type":"INTEGER"},"end_line":{"type":"INTEGER"}},
            ("action","path")),
        action("write_file", {"path": string, "content": string}),
        action("edit_file", {"path": string, "old_text": string, "new_text": string}),
        action("run_shell", {"command": string}),
        action("finish", {"result": result}),
    ]}



def generate(model, system_prompt, contents, usage, temperature=0.2):
    """One generateContent call with retries, fallback and budget checks.

    contents: list of {"role": "user"|"model", "parts": [{"text": ...}]}
    Returns the reply text. Raises BudgetExhausted / QuotaExhausted.
    """
    if usage.total_tokens >= config.MAX_TOKENS_PER_RUN:
        raise BudgetExhausted(
            f"token budget {config.MAX_TOKENS_PER_RUN} reached "
            f"({usage.total_tokens} used)"
        )
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": config.MAX_OUTPUT_TOKENS,
            # Agent replies are JSON objects by contract (TOOL_CONTRACT);
            # without this, gemini-3.5-flash-lite answers with
            # finishReason=MALFORMED_FUNCTION_CALL and an empty text part.
            "responseMimeType": "application/json",
            "responseSchema": response_schema(system_prompt),
        },
    }

    # Try the primary model, then one tier down (ADR-006), each with retries.
    models_to_try = [model]
    if model != config.MODEL_FALLBACK:
        models_to_try.append(config.MODEL_FALLBACK)

    last_err = None
    for active_model in models_to_try:
        for attempt in range(config.API_RETRIES + 1):
            try:
                data = _post(active_model, payload, api_key)
                usage.record(data.get("usageMetadata", {}))
                usage.models[active_model] = usage.models.get(active_model, 0) + 1
                if active_model != model:
                    usage.fallbacks += 1
                candidates = data.get("candidates") or []
                if not candidates:
                    raise _Transient(
                        f"Gemini returned no candidates: {str(data)[:300]}"
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                if not text.strip():
                    finish_reason = candidates[0].get("finishReason", "unknown")
                    raise _Transient(
                        f"empty model reply (finishReason={finish_reason})"
                    )
                return text
            except (_RateLimited, _Transient) as e:
                last_err = e
                if attempt < config.API_RETRIES:
                    time.sleep(
                        config.API_BACKOFF_SECONDS[
                            min(attempt, len(config.API_BACKOFF_SECONDS) - 1)
                        ]
                    )
        # primary exhausted its retries: fall through to the fallback tier
    raise QuotaExhausted(
        f"model retries exhausted; last error type={type(last_err).__name__}: {last_err}"
    )
