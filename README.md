# pytest-jsonschema-snapshot-bot

Single-file snapshot bot that:
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