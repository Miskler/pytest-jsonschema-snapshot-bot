# bot/pr.py
import os
import requests
from typing import List, Tuple

TITLE = "Update jsonschema snapshots"


def _compose_body(changes: List[Tuple[str, str]]) -> str:
    lines = ["Automated snapshot update by snapshot-bot.", "", "Changed files:"]
    for typ, path in changes:
        lines.append(f"- {typ}: {path}")
    return "\n".join(lines)


def create_pr(branch: str, changes: List[Tuple[str, str]]):
    """
    Create or update PR for `branch`.
    - If an open PR with head owner:branch exists -> PATCH update title/body.
    - Otherwise -> POST create new PR.
    Requires env:
      - GITHUB_REPOSITORY (owner/repo)
      - GITHUB_TOKEN (PAT or GITHUB_TOKEN with sufficient perms)
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN must be set in env")

    owner, repo_name = repo.split("/", 1)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # find existing open PR with this head
    params = {"head": f"{owner}:{branch}", "state": "open"}
    r = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/pulls", headers=headers, params=params)
    if r.status_code != 200:
        print("Failed to list PRs:", r.status_code, r.text)
        r.raise_for_status()

    existing = r.json()
    body = _compose_body(changes)

    if existing:
        pr = existing[0]
        pr_number = pr["number"]
        patch_payload = {"title": TITLE, "body": body}
        r2 = requests.patch(f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}", headers=headers, json=patch_payload)
        if r2.status_code == 200:
            print(f"Updated PR #{pr_number}: {r2.json().get('html_url')}")
            return r2.json()
        # detailed debug on failure
        print("Failed to update PR:", r2.status_code)
        print("Response body:", r2.text)
        r2.raise_for_status()

    # create new PR
    post_payload = {"title": TITLE, "head": f"{owner}:{branch}", "base": "main", "body": body}
    r3 = requests.post(f"https://api.github.com/repos/{owner}/{repo_name}/pulls", headers=headers, json=post_payload)
    if r3.status_code in (201,):
        print("Created PR:", r3.json().get("html_url"))
        return r3.json()

    # debug info for failures (403/422 etc)
    print("Create PR failed:", r3.status_code)
    print("Response headers:", r3.headers)
    print("Response body:", r3.text)
    r3.raise_for_status()
