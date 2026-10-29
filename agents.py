import json, re
from openai import OpenAI
import config

client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY or "missing")

def ask(model, system, user, retries=2):
    """Call a Nemotron model on Nebius Token Factory; validate JSON, retry on bad output."""
    last = None
    for _ in range(retries + 1):
        r = client.chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role": "system", "content": "detailed thinking off\n" + system + "\nReply with ONLY valid JSON, no markdown."},
                      {"role": "user", "content": user}])
        txt = re.sub(r"<think>.*?</think>", "", r.choices[0].message.content or "", flags=re.S)
        tokens = r.usage.total_tokens if r.usage else 0
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            return json.loads(m.group(0)), tokens
        except Exception as e:
            last = e
            user += "\n\nYour last reply was not valid JSON. Return only a JSON object."
    raise ValueError(f"model returned invalid JSON: {last}")

def fmt(files):
    return "\n\n".join(f"### {p}\n{c}" for p, c in files.items())

def plan(bug, tree, files):
    return ask(config.PLANNER_MODEL,
        'You are a senior debugger. Return {"root_cause": str, "steps": [str], "files_to_edit": [str]}.',
        f"Bug / failing test:\n{bug}\n\nFile tree:\n" + "\n".join(tree) + f"\n\nFiles:\n{fmt(files)}")

def patch(bug, plan_, files, feedback):
    return ask(config.CODER_MODEL,
        'You fix bugs. Return {"files": [{"path": str, "content": str}], "summary": str}. '
        'Give the COMPLETE new content of each changed file. "summary" is a short PR description in markdown.',
        f"Bug:\n{bug}\n\nPlan:\n{json.dumps(plan_)}\n\nCurrent files:\n{fmt(files)}"
        + (f"\n\nYour previous patch FAILED the tests:\n{feedback}\nFix it." if feedback else ""))

def regression_test(bug, files, framework):
    return ask(config.TESTER_MODEL,
        f'Write one small {framework} regression test for this bug. Return {{"path": str, "content": str}}. '
        'Use a new file name starting with test_patchpilot.',
        f"Bug:\n{bug}\n\nPatched code:\n{fmt(files)}")
