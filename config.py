import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load .env file if exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass

# Gemini API configuration
# Never hardcode the key; always read from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AI_MODEL = "gemini-3.5-flash"

# Scope and limits
REQUIRE_POWERPOINT = False  # Set to False per user instruction: accept any PDF
MAX_UPLOAD_MB = 10
MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
MAX_PAGES = 30
MAX_FIGURES = 60
MIN_FIGURE_SIZE_PT = 15
MIN_DRAWING_ITEMS = 5
CLUSTER_GAP_PT = 10
RENDER_DPI = 150
CONTEXT_MAX_CHARS = 1000
REQUEST_TIMEOUT_S = 60
FILE_TTL_SECONDS = 3600

# Directory paths
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / "cache"

# Server configuration
HOST = "127.0.0.1"
PORT = 5000
