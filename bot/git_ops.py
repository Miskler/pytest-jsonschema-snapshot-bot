import subprocess
import time


def run(cmd):
    subprocess.run(cmd, check=True)


def create_branch():

    branch = f"snapshot-bot-{int(time.time())}"

    run(["git", "checkout", "-b", branch])

    return branch


def commit_changes():

    run(["git", "add", "tests/__snapshots__"])
    run(["git", "commit", "-m", "update snapshots"])
    run(["git", "push", "origin", "HEAD"])