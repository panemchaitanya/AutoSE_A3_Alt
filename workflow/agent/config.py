"""Central configuration for the AutoSE A3 agentic SDLC pipeline.

Every budget and model choice lives here (see ADR-006 and ADR-009), so a
quota or pricing change is a one-file edit and the numbers in the report
trace back to one place.
"""

import os

# --- Models (ADR-006). Overridable via repo variables / env. ---
MODEL_SPEC = os.environ.get("MODEL_SPEC", "gemini-3.5-flash-lite")
MODEL_DESIGN = os.environ.get("MODEL_DESIGN", "gemini-3.5-flash-lite")
MODEL_DEVELOP = os.environ.get("MODEL_DEVELOP", "gemini-3.5-flash")
MODEL_TEST = os.environ.get("MODEL_TEST", "gemini-3.5-flash-lite")
MODEL_REVIEW = os.environ.get("MODEL_REVIEW", "gemini-3.5-flash")
MODEL_JUDGE = os.environ.get("MODEL_JUDGE", "gemini-3.5-flash-lite")
# Fallback tier used once when a call is rate-limited past its retries.
MODEL_FALLBACK = os.environ.get("MODEL_FALLBACK", "gemini-3.5-flash-lite")

# --- Budgets (ADR-009) ---
MAX_AGENT_STEPS = int(os.environ.get("MAX_AGENT_STEPS", "40"))
MAX_TOKENS_PER_RUN = int(os.environ.get("MAX_TOKENS_PER_RUN", "1500000"))
MAX_FIX_CYCLES = int(os.environ.get("MAX_FIX_CYCLES", "3"))
MAX_REVIEW_ROUNDS = int(os.environ.get("MAX_REVIEW_ROUNDS", "2"))
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "4096"))

# --- Retry/backoff for the model API ---
API_RETRIES = 2
API_BACKOFF_SECONDS = [15, 30]

# --- Paths (relative to the work-branch checkout) ---
STATE_PATH = os.environ.get("AUTOSE_STATE_PATH", ".autose/state.json")
ARTIFACTS_DIR = os.environ.get("AUTOSE_ARTIFACTS_DIR", ".autose/artifacts")

# Directories an agent may never write to (ADR-005): the workflow that runs
# it and the agent code itself.
PROTECTED_WRITE_PREFIXES = (".github/", "workflow/", ".autose/state")

# Shell command whitelist for the agent's run_shell tool (ADR-005).
SHELL_WHITELIST = (
    "pytest", "python", "python3",
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git diff", "git status", "git show", "git log",
)
