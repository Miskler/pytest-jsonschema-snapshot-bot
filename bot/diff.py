import subprocess
import shutil
from pathlib import Path


def schema_changed(old, new):

    result = subprocess.run(
        ["jsonschema-diff", "--exit-code", old, new],
        capture_output=True,
        text=True,
    )

    return result.returncode != 0


def collect_changes(ci_dir: Path, base_dir: Path):

    changes = []

    if not ci_dir.exists():
        return changes

    for file in ci_dir.rglob("*"):

        if not file.is_file():
            continue

        rel = file.relative_to(ci_dir)
        target = base_dir / rel

        target.parent.mkdir(parents=True, exist_ok=True)

        if not target.exists():

            shutil.copy2(file, target)
            changes.append(("added", str(rel)))
            continue

        if schema_changed(str(target), str(file)):

            shutil.copy2(file, target)
            changes.append(("updated", str(rel)))

    return changes