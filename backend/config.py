"""
HSN Classifier — Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHAPTERS_DIR = DATA_DIR / "chapters"
INDEX_CACHE = PROJECT_ROOT / "backend" / ".index_cache.json"

# ─── Agent Provider ───────────────────────────────────────────────────────────
AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "openrouter")

# ─── OpenRouter API ───────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it:free")

# ─── Custom API ───────────────────────────────────────────────────────────────
CUSTOM_AGENT_API_URL = os.getenv("CUSTOM_AGENT_API_URL", "")
CUSTOM_AGENT_API_KEY = os.getenv("CUSTOM_AGENT_API_KEY", "")

# ─── Local Agent ──────────────────────────────────────────────────────────────
LOCAL_AGENT_PATH = os.getenv("LOCAL_AGENT_PATH", "")

# ─── Model Limits ─────────────────────────────────────────────────────────────
MAX_CONTEXT_TOKENS = 262_144
MAX_OUTPUT_TOKENS = 32_768
# Reserve tokens for system prompt + user query + safety margin
CONTEXT_BUDGET_FOR_RAG = 200_000  # ~200K tokens for RAG context
TOKENS_PER_CHAR_ESTIMATE = 0.3   # rough estimate for English text

# ─── Retrieval Config ─────────────────────────────────────────────────────────
BM25_TOP_K = 40           # candidates from BM25
RERANK_TOP_K = 10         # candidates after reranking
FINAL_CONTEXT_CHUNKS = 6  # chunks sent to classifier
CHAPTER_BOOST_FACTOR = 1.5  # boost for routing-matched chapters

# ─── Server ───────────────────────────────────────────────────────────────────
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8899"))
