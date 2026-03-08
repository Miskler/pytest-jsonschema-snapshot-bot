import os
import requests


def create_pr(branch, changes):

    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]

    url = f"https://api.github.com/repos/{repo}/pulls"

    body = {
        "title": "Update jsonschema snapshots",
        "head": branch,
        "base": "main",
        "body": "\n".join(f"{t}: {p}" for t, p in changes),
    }

    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json=body,
    )

    r.raise_for_status()
