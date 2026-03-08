import argparse
from pathlib import Path

from diff import collect_changes
from git_ops import create_branch, commit_changes
from pr import create_pr


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ci-path")
    parser.add_argument("--base-path")

    args = parser.parse_args()

    ci = Path(args.ci_path)
    base = Path(args.base_path)

    changes = collect_changes(ci, base)

    if not changes:
        print("No snapshot changes")
        return

    branch = create_branch()

    commit_changes()

    create_pr(branch, changes)


if __name__ == "__main__":
    main()