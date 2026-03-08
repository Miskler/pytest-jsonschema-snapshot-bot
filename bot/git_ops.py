# bot/git_ops.py
import os
import shutil
import subprocess
import time
import tempfile

BRANCH = "snapshot-bot/update-snapshots"


def run(cmd, **kwargs):
    subprocess.run(cmd, check=True, **kwargs)


def _save_paths(paths):
    """Переместить существующие пути в temp и вернуть список (orig, dest)."""
    saved = []
    tmpdir = None
    for p in paths:
        if os.path.exists(p):
            if tmpdir is None:
                tmpdir = tempfile.mkdtemp(prefix="snapshot-bot-")
            dest = os.path.join(tmpdir, os.path.basename(p))
            # если dest уже существует (маловероятно), добавляем суффикс
            if os.path.exists(dest):
                dest = dest + "-" + str(int(time.time()))
            shutil.move(p, dest)
            saved.append((p, dest))
    return tmpdir, saved


def _restore_paths(saved):
    """Восстановить ранее сохранённые пути (перемещая обратно)."""
    for orig, dest in saved:
        # если на месте orig что-то осталось — удалить (чтобы восстановить чисто)
        if os.path.exists(orig):
            if os.path.isdir(orig):
                shutil.rmtree(orig)
            else:
                os.remove(orig)
        shutil.move(dest, orig)


def checkout_branch():
    """
    Обеспечить переключение/создание BRANCH даже если рабочее дерево "грязное".
    Возвращает имя ветки.
    """
    # подготовка: сохранить потенциально конфликтные каталоги
    cwd = os.getcwd()
    paths_to_save = [
        os.path.join(cwd, "tests", "__snapshots__"),
        os.path.join(cwd, "tests", "__snapshots__", "ci.cd"),
    ]
    tmpdir, saved = _save_paths(paths_to_save)

    try:
        # настроить автора (чтобы git не жаловался позже)
        run(["git", "config", "user.name", "github-actions[bot]"])
        run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])

        # получить удалённые refs и переключиться либо создать ветку
        run(["git", "fetch", "origin", BRANCH])

        # если ветка существует на origin — проверить её
        r = subprocess.run(["git", "ls-remote", "--heads", "origin", BRANCH], capture_output=True, text=True)
        if r.stdout.strip():
            # получить последнюю версию и переключиться на неё
            run(["git", "checkout", BRANCH])
            run(["git", "reset", "--hard", f"origin/{BRANCH}"])
        else:
            # создать новую ветку от текущей HEAD
            run(["git", "checkout", "-b", BRANCH])

    except Exception:
        # если что-то пошло не так — восстановим сохранённые данные и пробросим ошибку
        if saved:
            _restore_paths(saved)
        raise

    # восстановить файлы, чтобы они стали частью рабочей копии ветки
    if saved:
        _restore_paths(saved)
        # убедиться, что файлы доступны для git (будут закоммичены далее)
    return BRANCH


def commit_push():
    """Добавить, закоммитить (если есть что) и принудительно запушить ветку BRANCH."""
    run(["git", "add", "tests/__snapshots__"])

    # проверить, есть ли staged изменения
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        print("No changes to commit")
        return False

    run(["git", "commit", "-m", "update jsonschema snapshots"])
    # force push — обновляем единую ветку
    run(["git", "push", "--force", "origin", BRANCH])
    return True
