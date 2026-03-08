import subprocess

BRANCH = "snapshot-bot/update-snapshots"


def run(cmd):
    subprocess.run(cmd, check=True)


def checkout_branch():
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])

    # создать или переключиться
    r = subprocess.run(["git", "ls-remote", "--heads", "origin", BRANCH], capture_output=True)

    if r.stdout:
        run(["git", "fetch", "origin", BRANCH])
        run(["git", "checkout", BRANCH])
    else:
        run(["git", "checkout", "-b", BRANCH])

    return BRANCH


def commit_push():
    run(["git", "add", "tests/__snapshots__"])

    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        return False

    run(["git", "commit", "-m", "update jsonschema snapshots"])

    run(["git", "push", "--force", "origin", BRANCH])

    return True