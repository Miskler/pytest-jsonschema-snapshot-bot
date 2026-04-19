#!/usr/bin/env python3
"""
bot/main.py

Snapshot bot core that:
- switches to a persistent branch (creates if missing) while preserving working snapshot files,
- collects changes from CI snapshots (default: tests/__snapshots__/ci.cd) comparing with tests/__snapshots__
  using jsonschema-diff (falls back to bytewise compare),
- copies new/updated files into base snapshots folder,
- commits and force-pushes a single persistent branch,
- does NOT call GitHub REST API to create PRs; instead writes a prefilled PR "compare" URL to GITHUB_STEP_SUMMARY
  (and stdout) so a human can open the PR with title+body prefilled.

Usage:
  python snapshot_bot_single.py \
    --ci-path tests/__snapshots__/ci.cd \
    --base-path tests/__snapshots__

Environment:
  GITHUB_REPOSITORY should be set (owner/repo) for PR link generation (set automatically in GitHub Actions).
  If push requires authentication and you want to push via token, set GITHUB_TOKEN in env. If not present,
  bot will attempt to push to 'origin' (requires actions/checkout with credentials).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import List, Tuple

BRANCH_DEFAULT = os.environ.get("SNAPSHOT_BRANCH", "snapshot-bot/update-snapshots")
BASE_BRANCH_DEFAULT = os.environ.get("SNAPSHOT_BASE_BRANCH", "main")
COMMIT_MESSAGE = "update jsonschema snapshots"
TITLE = "Update jsonschema snapshots"
MAX_BODY_LEN = 3000  # to avoid too long URLs


def run(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def _save_paths(paths: List[Path]) -> Tuple[str | None, List[Tuple[Path, Path]]]:
    saved = []
    tmpdir = None
    for p in paths:
        if p.exists():
            if tmpdir is None:
                tmpdir = tempfile.mkdtemp(prefix="snapshot-bot-")
            dest = Path(tmpdir) / p.name
            # ensure unique dest
            if dest.exists():
                dest = Path(str(dest) + "-" + str(int(time.time())))
            shutil.move(str(p), str(dest))
            saved.append((p, dest))
    return tmpdir, saved


def _restore_paths(saved: List[Tuple[Path, Path]]):
    for orig, dest in saved:
        # remove any leftover orig
        if orig.exists():
            if orig.is_dir():
                shutil.rmtree(orig)
            else:
                orig.unlink()
        shutil.move(str(dest), str(orig))


def checkout_branch(branch: str, base_path: Path, ci_path: Path) -> str:
    """
    Ensure working tree is safe to checkout target branch:
    - save base_path and ci_path if they exist
    - fetch the latest base branch
    - checkout the snapshot branch from the fresh base branch tip
    - restore saved paths
    """
    if os.environ.get("SNAPSHOT_ALREADY_CHECKED_OUT") == "1":
        print(f"[INFO] Snapshot branch '{branch}' already checked out by workflow step.")
        return branch

    paths_to_save = [base_path, ci_path]
    _, saved = _save_paths(paths_to_save)

    try:
        # set author so commits won't fail
        run(["git", "config", "user.name", "github-actions[bot]"])
        run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])

        run(["git", "fetch", "origin", BASE_BRANCH_DEFAULT])
        run(["git", "checkout", "-B", branch, f"origin/{BASE_BRANCH_DEFAULT}"])

    except Exception:
        if saved:
            _restore_paths(saved)
        raise

    if saved:
        _restore_paths(saved)

    return branch


def schema_diff(old: Path, new: Path) -> bool:
    """
    Return True if schemas differ (using jsonschema-diff CLI if available).
    Compare old vs new (old first, new second).
    """
    try:
        r = subprocess.run(
            ["jsonschema-diff", "--no-color", "--exit-code", str(old), str(new)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        # jsonschema-diff returns non-zero if differences found
        return r.returncode != 0
    except FileNotFoundError:
        # fallback to binary compare
        with open(old, "rb") as f1, open(new, "rb") as f2:
            return f1.read() != f2.read()


def collect_changes(ci_dir: Path, base_dir: Path) -> List[Tuple[str, str]]:
    """
    Walk ci_dir and compare each file to base_dir counterpart.
    Copy new/updated files into base_dir.
    Return list of (typ, rel_path) where typ in ('added', 'updated').
    """
    changes: List[Tuple[str, str]] = []
    if not ci_dir.exists():
        print(f"[INFO] CI path '{ci_dir}' does not exist. Nothing to do.")
        return changes

    for file in ci_dir.rglob("*"):
        if not file.is_file():
            continue
        rel = file.relative_to(ci_dir)
        target = base_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        if not target.exists():
            shutil.copy2(str(file), str(target))
            changes.append(("added", str(rel)))
            print(f"[ADDED] {rel}")
            continue

        try:
            different = schema_diff(target, file)
        except Exception as e:
            print("schema_diff failed, falling back to byte compare:", e)
            with open(target, "rb") as f1, open(file, "rb") as f2:
                different = f1.read() != f2.read()

        if different:
            shutil.copy2(str(file), str(target))
            changes.append(("updated", str(rel)))
            print(f"[UPDATED] {rel}")

    print(f"[INFO] Total changes collected: {len(changes)}")
    return changes


def commit_push(branch: str, base_dir: Path, ci_dir: Path) -> bool:
    """
    Stage base_dir excluding ci_dir, commit if needed, and push branch.
    """
    # собираем все файлы base_dir, исключая ci_dir
    files_to_add = [
        str(p) for p in base_dir.rglob("*") 
        if p.is_file() and not str(p).startswith(str(ci_dir))
    ]
    if not files_to_add:
        print("[INFO] No files to add (excluding CI folder)")
        return False

    run(["git", "add"] + files_to_add)

    # check staged changes
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        print("No changes to commit")
        return False

    run(["git", "commit", "-m", COMMIT_MESSAGE])

    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")

    if token and repo:
        remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
        run(["git", "push", "--force", remote_url, f"HEAD:refs/heads/{branch}"])
    else:
        run(["git", "push", "--force", "origin", branch])

    print(f"Pushed branch {branch}")
    return True


def _compose_body(changes: List[Tuple[str, str]]) -> str:
    lines = ["Automated snapshot update by snapshot-bot.", "", "Changed files:"]
    for typ, path in changes:
        lines.append(f"- {typ}: {path}")
    return "\n".join(lines)


def _write_summary_link(url: str):
    md = "### Pull request\n\n- [Open PR with pre-filled fields](" + url + ")\n"
    print(md)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        try:
            with open(step_summary, "a", encoding="utf-8") as f:
                f.write(md)
        except Exception as e:
            print("Failed to write GITHUB_STEP_SUMMARY:", e)


def create_pr_link(branch: str, changes: List[Tuple[str, str]], base_branch: str):
    """
    Compose compare URL with quick_pull=1, title and body prefilled, write to summary.
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        print("GITHUB_REPOSITORY not set; cannot compose PR link.")
        return None

    body = _compose_body(changes)
    body_trunc = body if len(body) <= MAX_BODY_LEN else body[:MAX_BODY_LEN] + "\n[truncated...]"

    title_enc = urllib.parse.quote(TITLE, safe="")
    body_enc = urllib.parse.quote(body_trunc, safe="")

    owner, repo_name = repo.split("/", 1)
    cmp_url = f"https://github.com/{owner}/{repo_name}/compare/{base_branch}...{branch}?quick_pull=1&title={title_enc}&body={body_enc}"
    _write_summary_link(cmp_url)
    return cmp_url


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ci-path", default="tests/__snapshots__/ci.cd")
    p.add_argument("--base-path", default="tests/__snapshots__")
    p.add_argument("--branch", default=BRANCH_DEFAULT)
    p.add_argument("--base-branch", default=BASE_BRANCH_DEFAULT)
    return p.parse_args()


def main():
    args = parse_args()
    ci_path = Path(args.ci_path)
    base_path = Path(args.base_path)
    branch = args.branch
    base_branch = args.base_branch

    try:
        branch = checkout_branch(branch, base_path, ci_path)
    except Exception as e:
        print("Failed to checkout branch:", e)
        raise

    changes = collect_changes(ci_path, base_path)
    if not changes:
        print("No snapshot changes")
        return

    try:
        pushed = commit_push(branch, base_path, ci_path)
    except Exception as e:
        print("Failed to commit/push changes:", e)
        raise

    if pushed:
        create_pr_link(branch, changes, base_branch)


if __name__ == "__main__":
    main()
