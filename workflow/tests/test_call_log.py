"""Tests for per-call provenance logging (schema autose-call/1).

Provider is stubbed: no network, no real key. Run:
    python3 -m pytest workflow/tests/test_call_log.py
or  python3 workflow/tests/test_call_log.py
"""

import json
import os
import pathlib
import sys
import tempfile

AGENT = pathlib.Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT))

import call_log
import config
import gemini
import run_stage


def setup_env(tmp):
    os.environ["GEMINI_API_KEY"] = "test-key-not-real"
    config.API_RETRIES = 1
    config.API_BACKOFF_SECONDS = [0]
    call_log._branch_head_cache.clear()
    return tmp


def read_log(repo_root):
    path = pathlib.Path(repo_root) / config.ARTIFACTS_DIR / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def ok_payload(model_version=None, response_id=None):
    data = {
        "candidates": [{"content": {"parts": [{"text": "{\"action\": \"finish\", \"result\": \"done\"}"}]},
                        "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5,
                          "totalTokenCount": 15},
    }
    if model_version:
        data["modelVersion"] = model_version
    if response_id:
        data["responseId"] = response_id
    return data


def test_success_record_complete():
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)
        calls = []

        def fake_post(model, payload, key):
            calls.append(model)
            return ok_payload(model_version="gemini-3.5-flash-001",
                              response_id="resp-1")

        orig = gemini._post
        gemini._post = fake_post
        try:
            usage = gemini.Usage({})
            text = gemini.generate(
                "gemini-3.5-flash", "SYSTEM PROMPT SECRET",
                [{"role": "user", "parts": [{"text": "TASK SECRET"}]}], usage,
                context={"role": "Developer", "stage": "implementation",
                         "repo_root": tmp,
                         "task_sha256": call_log.sha256_text("TASK SECRET")})
            assert "finish" in text
        finally:
            gemini._post = orig
        recs = read_log(tmp)
        assert len(recs) == 1
        r = recs[0]
        assert r["schema"] == "autose-call/1"
        assert r["status"] == "success"
        assert r["role"] == "Developer"
        assert r["stage"] == "implementation"
        assert r["requested_model"] == "gemini-3.5-flash"
        assert r["attempted_model"] == "gemini-3.5-flash"
        assert r["fallback"] is False
        assert r["provider_model_version"] == "gemini-3.5-flash-001"
        assert r["response_id"] == "resp-1"
        assert r["usage"]["totalTokenCount"] == 15
        assert r["call_id"] and r["ts"]
        # no raw prompts anywhere in the log file
        raw = (pathlib.Path(tmp) / config.ARTIFACTS_DIR /
               "calls.jsonl").read_text()
        assert "SYSTEM PROMPT SECRET" not in raw
        assert "TASK SECRET" not in raw


def test_failure_records_without_token_zeros_and_fallback_marked():
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)

        def fake_post(model, payload, key):
            if model == "gemini-3.5-flash":
                raise gemini._RateLimited("503 high demand")
            return ok_payload()

        orig = gemini._post
        gemini._post = fake_post
        try:
            usage = gemini.Usage({})
            gemini.generate(
                "gemini-3.5-flash", "sys",
                [{"role": "user", "parts": [{"text": "task"}]}], usage,
                context={"role": "Developer", "stage": "implementation",
                         "repo_root": tmp})
        finally:
            gemini._post = orig
        recs = read_log(tmp)
        errs = [r for r in recs if r["status"] == "error"]
        oks = [r for r in recs if r["status"] == "success"]
        assert len(errs) == 2  # API_RETRIES=1 -> 2 attempts on primary
        assert len(oks) == 1
        for r in errs:
            assert r["usage"] is None  # no invented zero tokens
            assert set(r["error"]) == {"category", "http_status",
                                       "finish_reason"}
            assert r["provider_model_version"] is None
        assert oks[0]["attempted_model"] == config.MODEL_FALLBACK
        assert oks[0]["fallback"] is True
        # unique call ids across every attempt
        ids = [r["call_id"] for r in recs]
        assert len(set(ids)) == len(ids)
        # provider error bodies must never reach the log
        raw = (pathlib.Path(tmp) / config.ARTIFACTS_DIR /
               "calls.jsonl").read_text()
        assert "503 high demand" not in raw


def test_model_version_null_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)
        orig = gemini._post
        gemini._post = lambda m, p, k: ok_payload()
        try:
            gemini.generate("gemini-3.5-flash-lite", "sys",
                            [{"role": "user", "parts": [{"text": "t"}]}],
                            gemini.Usage({}),
                            context={"role": "Tester", "repo_root": tmp})
        finally:
            gemini._post = orig
        r = read_log(tmp)[0]
        assert r["provider_model_version"] is None  # never the env pin


def test_judge_marked_explicitly():
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)
        orig = gemini._post
        gemini._post = lambda m, p, k: {
            "candidates": [{"content": {"parts": [
                {"text": "{\"pass\": true, \"reasons\": [\"ok\"]}"}]}}],
            "usageMetadata": {"totalTokenCount": 3},
        }
        try:
            ok, reason = run_stage.judge(tmp, gemini.Usage({}), "q", "doc",
                                         stage="requirements")
            assert ok
        finally:
            gemini._post = orig
        r = read_log(tmp)[0]
        assert r["role"] == "Judge"
        assert r["stage"] == "requirements"


def test_secret_in_exception_message_never_logged():
    """str(exception) can echo API keys or provider bodies: the log must
    carry only category/status/reason codes, never the exception text."""
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)

        def fake_post(model, payload, key):
            err = RuntimeError(
                "Gemini API error 403: leaked body key=SECRETKEY123")
            err.http_status = 403
            raise err

        orig = gemini._post
        gemini._post = fake_post
        try:
            try:
                gemini.generate(
                    "gemini-3.5-flash", "sys",
                    [{"role": "user", "parts": [{"text": "t"}]}],
                    gemini.Usage({}),
                    context={"role": "Developer", "repo_root": tmp})
                raise AssertionError("non-retryable error must propagate")
            except RuntimeError:
                pass
        finally:
            gemini._post = orig
        recs = read_log(tmp)
        assert len(recs) == 1  # recorded even though never retried
        r = recs[0]
        assert r["status"] == "error"
        assert r["error"] == {"category": "http_client_error",
                              "http_status": 403, "finish_reason": None}
        raw = (pathlib.Path(tmp) / config.ARTIFACTS_DIR /
               "calls.jsonl").read_text()
        assert "SECRETKEY123" not in raw
        assert "leaked body" not in raw


def test_empty_reply_preserves_returned_facts():
    """An empty-reply call still returns usage/modelVersion/responseId;
    those facts belong in the error record."""
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)

        def fake_post(model, payload, key):
            return {"candidates": [{"content": {"parts": [{"text": ""}]},
                                    "finishReason": "MAX_TOKENS"}],
                    "usageMetadata": {"totalTokenCount": 99},
                    "modelVersion": "gemini-3.5-flash-001",
                    "responseId": "resp-empty"}

        orig = gemini._post
        gemini._post = fake_post
        try:
            try:
                gemini.generate(
                    "gemini-3.5-flash", "sys",
                    [{"role": "user", "parts": [{"text": "t"}]}],
                    gemini.Usage({}),
                    context={"role": "Developer", "repo_root": tmp})
                raise AssertionError("must fail after retries")
            except Exception:
                pass
        finally:
            gemini._post = orig
        errs = [r for r in read_log(tmp) if r["status"] == "error"]
        # primary + fallback tiers, 2 attempts each; facts kept on every one
        assert len(errs) == 4
        for r in errs:
            assert r["error"]["category"] == "empty_reply"
            assert r["error"]["finish_reason"] == "MAX_TOKENS"
            assert r["usage"]["totalTokenCount"] == 99
            assert r["provider_model_version"] == "gemini-3.5-flash-001"
            assert r["response_id"] == "resp-empty"


def test_harness_digest_is_content_not_env():
    """Harness identity comes from executing file contents; GITHUB_SHA is
    informational only and must not influence the digest."""
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)
        call_log._harness_digest_cache = None
        orig_sha = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "deadbeef" * 5
        try:
            orig = gemini._post
            gemini._post = lambda m, p, k: ok_payload()
            try:
                gemini.generate("gemini-3.5-flash", "sys",
                                [{"role": "user", "parts": [{"text": "t"}]}],
                                gemini.Usage({}),
                                context={"role": "Developer", "repo_root": tmp})
            finally:
                gemini._post = orig
        finally:
            if orig_sha is None:
                del os.environ["GITHUB_SHA"]
            else:
                os.environ["GITHUB_SHA"] = orig_sha
        r = read_log(tmp)[0]
        d1 = r["harness_digest"]
        assert d1 and len(d1) == 64
        call_log._harness_digest_cache = None
        assert call_log.harness_digest() == d1


def test_merge_into_dedupes_by_call_id():
    with tempfile.TemporaryDirectory() as tmp:
        setup_env(tmp)
        src = pathlib.Path(tmp) / "src"
        dst = pathlib.Path(tmp) / "dst"
        for root in (src, dst):
            (root / config.ARTIFACTS_DIR).mkdir(parents=True)
        def write(root, recs):
            p = root / config.ARTIFACTS_DIR / "calls.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in recs) + "\n")
        write(src, [{"call_id": "a", "status": "success"},
                    {"call_id": "b", "status": "error"}])
        write(dst, [{"call_id": "b", "status": "error"},
                    {"call_id": "c", "status": "success"}])
        call_log.merge_into(str(src), str(dst))
        recs = read_log(dst)
        assert [r["call_id"] for r in recs] == ["b", "c", "a"]
        assert len(recs) == 3


def test_usage_state_backwards_compatible():
    usage = gemini.Usage({"prompt_tokens": 1, "completion_tokens": 2,
                          "total_tokens": 3, "calls": 1, "fallbacks": 0,
                          "models": {"m": 1}})
    d = usage.as_dict()
    assert d["total_tokens"] == 3 and d["models"] == {"m": 1}
    again = gemini.Usage(d)
    assert again.total_tokens == 3


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


def test_failed_merge_is_not_silently_accepted(monkeypatch, tmp_path):
    src=tmp_path/'src'; dst=tmp_path/'dst'
    (src/config.ARTIFACTS_DIR).mkdir(parents=True)
    (src/config.ARTIFACTS_DIR/'calls.jsonl').write_text('{"call_id":"a"}\n')
    dst.write_text('not a directory')
    import pytest
    with pytest.raises(RuntimeError, match='provenance merge failed'):
        call_log.merge_into(str(src),str(dst))


def test_review_copy_uses_finally():
    import ast
    tree=ast.parse((pathlib.Path(__file__).parents[1]/'agent'/'run_stage.py').read_text())
    review=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='stage_review')
    guards=[n for n in ast.walk(review) if isinstance(n,ast.Try) and n.finalbody]
    assert any(any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='merge_into' for x in ast.walk(n)) for g in guards for n in g.finalbody)
