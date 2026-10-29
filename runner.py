import io, os, re, shutil, subprocess, sys, tempfile, difflib, urllib.request, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache"}

def _github_zip(url, dest):
    """Download a public GitHub repo as a zip (no git binary needed, works on Vercel)."""
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$", url.strip())
    if not m:
        return False
    req = urllib.request.Request(f"https://codeload.github.com/{m[1]}/{m[2]}/zip/HEAD", headers={"User-Agent": "patchpilot"})
    data = urllib.request.urlopen(req, timeout=60).read()
    if len(data) > 30_000_000:
        raise ValueError("repo is too large (30 MB max)")
    root = os.path.realpath(dest)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        top = z.namelist()[0].split("/")[0] + "/"
        for n in z.namelist():
            rel = n[len(top):]
            if not rel or n.endswith("/"):
                continue
            p = os.path.realpath(os.path.join(dest, rel))
            if p.startswith(root + os.sep):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(z.read(n))
    return True

def load(repo):
    d = tempfile.mkdtemp(prefix="pp_")
    if repo.startswith("example:"):
        shutil.copytree(os.path.join(HERE, "examples", os.path.basename(repo[8:])), d, dirs_exist_ok=True)
    elif repo.startswith("https://"):
        if not _github_zip(repo, d):
            if not shutil.which("git"):
                raise ValueError("Only public github.com repos are supported on this server")
            subprocess.run(["git", "clone", "--depth", "1", repo, d], check=True, timeout=90, capture_output=True,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
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

def _env(root):
    """Child env: keeps Python packages visible, strips API keys and secrets."""
    e = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I)}
    e["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e["HOME"] = os.environ.get("HOME", root)
    return e

def test(root):
    """Runs tests in a temp dir, 60s timeout, no secrets in env. USE_DOCKER=1 adds --network none."""
    if framework(root) == "jest":
        cmd = ["npm", "test", "--silent"]
    elif os.getenv("USE_DOCKER") == "1" and shutil.which("docker"):
        cmd = ["docker", "run", "--rm", "--network", "none", "-v", f"{root}:/w", "-w", "/w", "python:3.11-slim",
               "sh", "-c", "pip install -q pytest 2>/dev/null; pytest -x -q"]
    else:
        cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"]
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60, env=_env(root))
        return p.returncode == 0, (p.stdout + p.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 60s"
