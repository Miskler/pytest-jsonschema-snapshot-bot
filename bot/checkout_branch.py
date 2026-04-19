#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from main import BRANCH_DEFAULT, checkout_branch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Checkout the snapshot bot branch before updating snapshots."
    )
    parser.add_argument("--ci-path", default="tests/__snapshots__/ci.cd")
    parser.add_argument("--base-path", default="tests/__snapshots__")
    parser.add_argument("--branch", default=BRANCH_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkout_branch(args.branch, Path(args.base_path), Path(args.ci_path))


if __name__ == "__main__":
    main()
