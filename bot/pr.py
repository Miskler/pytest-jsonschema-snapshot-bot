import os

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_REF = os.environ.get("GITHUB_REF", "refs/heads/main")

def pr_link(branch_name: str) -> str:
    """
    Формирует ссылку на создание PR с предзаполненными полями.
    """
    base_branch = GITHUB_REF.replace("refs/heads/", "")
    title = f"Update snapshots ({branch_name})"
    body = "Автоматическое обновление snapshot-файлов"
    url = f"https://github.com/{GITHUB_REPO}/compare/{base_branch}...{branch_name}?expand=1&title={title}&body={body}"
    return url