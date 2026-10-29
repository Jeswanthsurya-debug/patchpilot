import json, os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
import agents, config, runner

app = FastAPI(title="PatchPilot")

def ev(**k):
    return f"data: {json.dumps(k)}\n\n"

def _index_path():
    for d in ("public", "static"):
        p = os.path.join(runner.HERE, d, "index.html")
        if os.path.exists(p):
            return p

@app.get("/")
def index():
    p = _index_path()
    if p:
        return FileResponse(p)
    return HTMLResponse("<pre>index.html not found. Files here: " + ", ".join(sorted(os.listdir(runner.HERE))) + "</pre>", status_code=500)

@app.get("/api/health")
def health():
    return {"key_set": bool(config.API_KEY), "index": bool(_index_path()),
            "examples": os.path.isdir(os.path.join(runner.HERE, "examples")), "files": sorted(os.listdir(runner.HERE))}

@app.get("/api/models")
def models():
    return [m.id for m in agents.client.models.list().data]

@app.get("/api/run")
def run(repo: str = "example:py_bug", bug: str = ""):
    def gen():
        tokens = 0
        try:
            root = runner.load(repo)
            tree, files = runner.snapshot(root)
            yield ev(step="load", status="done", detail=f"Loaded {len(tree)} files")

            yield ev(step="planner", status="running", model=config.PLANNER_MODEL)
            plan, t = agents.plan(bug, tree, files); tokens += t
            yield ev(step="planner", status="done", model=config.PLANNER_MODEL, tokens=t, total=tokens,
                     detail=plan.get("root_cause", ""), steps=plan.get("steps", []))

            feedback, ok, summary, tested = "", False, "", False
            for i in range(1, config.MAX_ITERS + 1):
                yield ev(step="coder", status="running", model=config.CODER_MODEL, attempt=i)
                result, t = agents.patch(bug, plan, files, feedback); tokens += t
                before = {c["path"]: files.get(c["path"], "") for c in result["files"]}
                runner.apply(root, result["files"])
                after = {c["path"]: c["content"] for c in result["files"]}
                files.update(after)
                summary = result.get("summary", "")
                yield ev(step="coder", status="done", model=config.CODER_MODEL, tokens=t, total=tokens,
                         attempt=i, diff=runner.diff(before, after))

                yield ev(step="tester", status="running", model=config.TESTER_MODEL, attempt=i)
                if not tested:
                    try:
                        rt, t = agents.regression_test(bug, files, runner.framework(root)); tokens += t
                        runner.apply(root, [rt]); tested = True
                    except Exception:
                        pass
                ok, out = runner.test(root)
                yield ev(step="tester", status="done" if ok else "failed", model=config.TESTER_MODEL,
                         total=tokens, attempt=i, output=out)
                if ok:
                    break
                feedback = out
            yield ev(step="final", status="done" if ok else "failed", total=tokens, summary=summary)
        except Exception as e:
            yield ev(step="error", status="failed", detail=str(e))
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
