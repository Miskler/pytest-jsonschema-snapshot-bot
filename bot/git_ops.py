import subprocess
import time


def run(cmd):
    subprocess.run(cmd, check=True)


def create_branch():
    branch = f"snapshot-bot-{int(time.time())}"
    run(["git", "checkout", "-b", branch])
    return branch


def commit_changes():
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])

    run(["git", "add", "tests/__snapshots__"])

    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        return False

    run(["git", "commit", "-m", "update snapshots"])
    run(["git", "push", "origin", "HEAD"])

    return True
