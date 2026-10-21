"""Import a script from a skill folder by path (the folder names have hyphens), plus shared test helpers."""

import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")


def script(folder, name):
    return os.path.join(SKILLS_DIR, folder, "scripts", name + ".py")


def load(folder, name):
    spec = importlib.util.spec_from_file_location("oldhand_test_" + name, script(folder, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def skill_file(folder, name):
    return os.path.join(SKILLS_DIR, folder, name)


def cli(folder, name, *args, **kw):
    """Run a script as a command. Returns (exit code, stdout, stderr)."""
    p = subprocess.run([sys.executable, script(folder, name)] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, **kw)
    return p.returncode, p.stdout, p.stderr


# Git in the tests must not read the user's global or system config (signing, hooks, excludes).
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(cwd, *args):
    env = dict(os.environ, **GIT_ENV)
    subprocess.run(["git"] + list(args), cwd=cwd, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def git_repo(path):
    """A fresh repo with one committed file, a.txt."""
    git(path, "init", "-q")
    git(path, "config", "user.name", "Oldhand Test")
    git(path, "config", "user.email", "test@example.test")
    git(path, "config", "commit.gpgsign", "false")
    with open(os.path.join(path, "a.txt"), "w") as fh:
        fh.write("one\n")
    git(path, "add", "a.txt")
    git(path, "commit", "-q", "-m", "init")
