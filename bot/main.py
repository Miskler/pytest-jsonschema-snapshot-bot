import os
from pathlib import Path
from diff import find_changes
from pr import pr_link

CI_PATH = os.environ.get("CI_PATH", "tests/__snapshots__/ci.cd")
BASE_PATH = os.environ.get("BASE_PATH", "tests/__snapshots__")
BRANCH = os.environ.get("GITHUB_HEAD_REF", "snapshot-bot/update-snapshots")

def main():
    if not Path(CI_PATH).exists():
        print(f"No CI snapshots found at {CI_PATH}. Exiting.")
        return

    changes = find_changes(CI_PATH, BASE_PATH)

    if changes:
        link = pr_link(BRANCH)
        print(f"::notice file=main.py::Snapshots changed! Create PR: {link}")
    else:
        print("No snapshot changes detected.")

if __name__ == "__main__":
    main()