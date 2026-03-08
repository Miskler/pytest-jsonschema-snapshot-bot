import jsonschema_diff
from pathlib import Path

def find_changes(ci_path: str, base_path: str):
    """
    Возвращает True, если есть изменения или новые файлы.
    """
    ci_path = Path(ci_path)
    base_path = Path(base_path)

    changes_found = False

    for ci_file in ci_path.rglob("*.json"):
        base_file = base_path / ci_file.relative_to(ci_path)
        if not base_file.exists():
            changes_found = True
            break
        else:
            diff = jsonschema_diff.diff(str(base_file), str(ci_file))
            if diff:
                changes_found = True
                break

    return changes_found
