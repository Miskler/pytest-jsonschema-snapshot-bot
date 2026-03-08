import os
import requests


def create_pr(branch, changes):

    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # проверить существующий PR
    r = requests.get(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=headers,
        params={"head": f"{repo.split('/')[0]}:{branch}", "state": "open"},
    )

    if r.json():
        return

    body = {
        "title": "Update jsonschema snapshots",
        "head": branch,
        "base": "main",
        "body": "\n".join(f"{t}: {p}" for t, p in changes),
    }

    requests.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=headers,
        json=body,
    ).raise_for_status()
