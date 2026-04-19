# pytest-jsonschema-snapshot-bot

Snapshot bot that:
- switches to a persistent branch (creates if missing) while preserving working snapshot files,
- checks out the persistent snapshot branch from the latest base branch in a dedicated step before snapshot updates run,
- collects changes from CI snapshots (default: tests/__snapshots__/ci.cd) comparing with tests/__snapshots__
  using jsonschema-diff (falls back to bytewise compare),
- copies new/updated files into base snapshots folder,
- commits and force-pushes a single persistent branch,
- does NOT call GitHub REST API to create PRs; instead writes a prefilled PR "compare" URL to GITHUB_STEP_SUMMARY
  (and stdout) so a human can open the PR with title+body prefilled.

Usage:
  python bot/main.py \
    --branch snapshot-bot/update-snapshots \
    --ci-path tests/__snapshots__/ci.cd \
    --base-path tests/__snapshots__

Environment:
  GITHUB_REPOSITORY should be set (owner/repo) for PR link generation (set automatically in GitHub Actions).
  If push requires authentication and you want to push via token, set GITHUB_TOKEN in env. If not present,
  bot will attempt to push to 'origin' (requires actions/checkout with credentials).
