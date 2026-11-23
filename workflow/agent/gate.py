"""Gate job (ADR-010): authorize the trigger, choose start/continue, prep the
branch and state.json. Runs in the workflow, not inside an agent.

Environment it expects: GITHUB_EVENT_NAME, GITHUB_EVENT_PATH,
GITHUB_REPOSITORY, GITHUB_REPOSITORY_OWNER, GITHUB_OUTPUT, GH_TOKEN.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import controller

TRIGGER_LABEL = "autose"
TRIGGER_COMMAND = "/autose"


def sh(*args, check=True):
    return subprocess.run(list(args), check=check, capture_output=True,
                          text=True)


def gh_api(path):
    out = sh("gh", "api", path).stdout
    return json.loads(out)


def output(name, value):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def main():
    event_name = os.environ["GITHUB_EVENT_NAME"]
    with open(os.environ["GITHUB_EVENT_PATH"], "r", encoding="utf-8") as f:
        payload = json.load(f)
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]
    repo = os.environ["GITHUB_REPOSITORY"]

    issue_number = None
    entry = None
    actor = None

    if event_name == "issues":
        if payload.get("label", {}).get("name") != TRIGGER_LABEL:
            return skip(f"label is not '{TRIGGER_LABEL}'")
        actor = payload["sender"]["login"]
        issue_number = payload["issue"]["number"]
        if actor != owner:
            return skip(f"sender {actor} is not the repository owner")
    elif event_name == "issue_comment":
        body = payload["comment"]["body"].strip()
        if not body.startswith(TRIGGER_COMMAND):
            return skip("comment does not start with /autose")
        if "pull_request" in payload["issue"]:
            return skip("/autose on a PR is handled by the review round, "
                        "not a fresh start")
        actor = payload["sender"]["login"]
        issue_number = payload["issue"]["number"]
        if actor != owner:
            return skip(f"sender {actor} is not the repository owner")
    elif event_name == "workflow_dispatch":
        # Only reachable from the review workflow (GITHUB_TOKEN) or a human
        # with write access; the Actions permission model enforces that.
        issue_number = int(os.environ["INPUT_ISSUE"])
        entry = os.environ.get("INPUT_ENTRY", "").strip() or None
        actor = os.environ.get("GITHUB_ACTOR", "?")
        if entry not in (None, "design", "implementation", "resume"):
            return skip(f"unknown entry stage {entry}")
    else:
        return skip(f"unsupported event {event_name}")

    branch = f"autose/issue-{issue_number}"
    issue = gh_api(f"repos/{repo}/issues/{issue_number}")
    issue_json = {
        "number": issue["number"],
        "title": issue.get("title", ""),
        "body": issue.get("body", "") or "",
    }

    prior_tip = None
    if entry is None:
        # start mode: fresh branch from main, fresh state
        sh("git", "fetch", "origin", "main")
        sh("git", "fetch", "origin", branch, check=False)
        prior = sh("git", "ls-remote", "--heads", "origin",
                   branch).stdout.split()
        if prior:
            prior_tip = prior[0]
            author = sh("git", "show", "-s", "--format=%ae",
                        prior_tip).stdout.strip()
            if author != "autose-bot@users.noreply.github.com":
                print(f"gate REFUSED: remote {branch} tip {prior_tip} was "
                      f"written by {author}, not the autose bot. A fresh "
                      "start would supersede human or parallel work; "
                      "resolve the branch manually.")
                sys.exit(1)
        sh("git", "checkout", "-B", branch, "origin/main")
        state = controller.init_state(issue_number, branch)
        controller.record(state, f"triggered by {actor} via {event_name}")
        if prior_tip:
            # the old tip stays reachable in git history and on its
            # Actions runs; record exactly what this restart supersedes
            controller.record(state, f"fresh start supersedes {prior_tip}")
    else:
        # continue mode: a review round sends us back to design/implementation
        sh("git", "fetch", "origin", branch)
        sh("git", "checkout", branch)
        # Preserve completed artifacts/code, but execute the current reviewed
        # harness revision rather than a stale copy on the work branch.
        sh("git", "fetch", "origin", "main")
        sh("git", "checkout", "origin/main", "--", "workflow/agent")
        sh("git", "add", "workflow/agent")
        state = controller.load_state(".")
        if state is None:
            return skip(f"no state on {branch}; cannot continue")
        if entry == "resume":
            # Operational retries are not reviewer-requested change rounds.
            # Repair counts previously assigned before any review existed.
            if not state["stages"]["review"].get("verdict"):
                controller.record(state, "operational recovery: no reviewer verdict exists")
                state["review_rounds"] = 0
        else:
            state["review_rounds"] = state.get("review_rounds", 0) + 1
            controller.entry_stage_for_continue(state,
                "approach" if entry == "design" else "code")

    os.makedirs(".autose", exist_ok=True)
    with open(".autose/issue.json", "w", encoding="utf-8") as f:
        json.dump(issue_json, f, indent=2)
    controller.save_state(".", state)
    sh("git", "add", ".autose", "workflow/agent")
    sh("git", "-c", "user.name=autose-bot", "-c",
       "user.email=autose-bot@users.noreply.github.com",
       "commit", "-m", f"autose: gate ({'start' if entry is None else 'continue -> ' + entry}) for issue #{issue_number}",
       check=False)
    if prior_tip:
        # durable retention BEFORE any rewrite: archive the superseded tip
        # under its own ref so the attempt stays fetchable forever,
        # independent of Actions-run linkage (which is not git retention)
        sh("git", "push", "origin",
           f"{prior_tip}:refs/autose-archive/{branch}-{prior_tip[:12]}")
        # explicit lease: the push only lands if the remote tip is still
        # the bot commit we validated above, so a racing push by anyone
        # else makes the gate fail instead of being overwritten
        sh("git", "push", "-u",
           f"--force-with-lease=refs/heads/{branch}:{prior_tip}",
           "origin", branch)
    else:
        sh("git", "push", "-u", "origin", branch)

    output("ok", "true")
    output("issue", str(issue_number))
    output("branch", branch)
    print(f"gate OK: issue #{issue_number}, branch {branch}, "
          f"mode {'start' if entry is None else 'continue -> ' + entry}")


def skip(reason):
    print(f"gate: skipping - {reason}")
    output("ok", "false")
    output("issue", "0")
    output("branch", "")


if __name__ == "__main__":
    main()
