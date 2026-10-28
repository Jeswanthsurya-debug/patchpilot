import os, shutil, subprocess, sys, tempfile, difflib
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache"}

def load(repo):
    d = tempfile.mkdtemp(prefix="pp_")
    if repo.startswith("example:"):
        shutil.copytree(os.path.join(HERE, "examples", os.path.basename(repo[8:])), d, dirs_exist_ok=True)
    elif repo.startswith("https://"):
        subprocess.run(["git", "clone", "--depth", "1", repo, d], check=True, timeout=90, capture_output=True)
    else:
        raise ValueError("Use example:py_bug or an https git URL")
    return d

def snapshot(root, limit=30):
    tree, files = [], {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [x for x in dn if x not in SKIP]
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), root)
            tree.append(rel)
            try:
                if len(files) < limit and os.path.getsize(os.path.join(root, rel)) < 20000:
                    files[rel] = open(os.path.join(root, rel), encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                pass
    return sorted(tree), files

def apply(root, changes):
    for c in changes:
        p = os.path.realpath(os.path.join(root, c["path"]))
        if not p.startswith(os.path.realpath(root) + os.sep):
            raise ValueError("path escapes sandbox: " + c["path"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(c["content"])

def diff(before, after):
    out = []
    for p in sorted(set(before) | set(after)):
        out += difflib.unified_diff(before.get(p, "").splitlines(), after.get(p, "").splitlines(), f"a/{p}", f"b/{p}", lineterm="")
    return "\n".join(out)

def framework(root):
    return "jest" if os.path.exists(os.path.join(root, "package.json")) else "pytest"

def test(root):
    """Runs tests in a temp dir with a clean env and 60s timeout. USE_DOCKER=1 adds --network none isolation."""
    if framework(root) == "jest":
        cmd = ["npm", "test", "--silent"]
    elif os.getenv("USE_DOCKER") == "1" and shutil.which("docker"):
        cmd = ["docker", "run", "--rm", "--network", "none", "-v", f"{root}:/w", "-w", "/w", "python:3.11-slim",
               "sh", "-c", "pip install -q pytest 2>/dev/null; pytest -x -q"]
    else:
        cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"]
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60,
                           env={"PATH": os.environ.get("PATH", ""), "HOME": root})
        return p.returncode == 0, (p.stdout + p.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 60s"
