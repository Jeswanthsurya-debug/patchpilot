import os
from dotenv import load_dotenv
load_dotenv()
# Verify these in the Token Factory model list (GET /api/models lists what your key can use).
BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
API_KEY = os.getenv("NEBIUS_API_KEY", "")
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1")   # deep reasoning
CODER_MODEL = os.getenv("CODER_MODEL", "nvidia/Llama-3_3-Nemotron-Super-49B-v1")        # patch writing
TESTER_MODEL = os.getenv("TESTER_MODEL", "nvidia/NVIDIA-Nemotron-Nano-9B-v2")           # fast, cheap calls
MAX_ITERS = int(os.getenv("MAX_ITERS", "3"))
