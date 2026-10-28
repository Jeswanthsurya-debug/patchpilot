# patchpilot
## Live demo
https://YOUR-APP.vercel.app (click **Play demo**, or run **Fix it** with `example:py_bug`)

## Try it on a real repo
Repo: https://github.com/Jeswanthsurya-debug/patchpilot-demo-bug
Bug: `test_discount fails: apply_discount(200, 10) returns -1800 instead of 180. Fix the bug without changing the tests.`

## Deploy on Vercel
1. Import this repo at vercel.com
2. Add env vars: NEBIUS_API_KEY, PLANNER_MODEL, CODER_MODEL, TESTER_MODEL
3. Deploy

## Built during the submission period
PatchPilot was created for this hackathon. Everything in this repo is new.

## Feedback on Nebius Token Factory and NVIDIA
- Token Factory: the OpenAI-compatible API made integration quick, and Nano was fast for small calls.
- The model IDs I expected did not match the live model list, so I added a /api/models endpoint to check them.
- The API key is shown only once, and billing needed a card before I could start.
- Nemotron Ultra gave solid root-cause plans, and the three-size routing (Ultra/Super/Nano) kept token use low.
