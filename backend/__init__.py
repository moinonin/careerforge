import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

# Load .env if present (python-dotenv is a project dependency)
if os.environ.get("CAREERFORGE_SKIP_DOTENV") is None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE, override=False)
    except ImportError:  # pragma: no cover — only when run outside venv
        pass
