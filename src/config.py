"""Configuration for the HF Referral Assistant."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REFERRALS_DIR = DATA_DIR / "referrals"
GUIDELINES_DIR = DATA_DIR / "guidelines"

# Database
DB_PATH = DATA_DIR / "referrals.db"
INDEX_PATH = DATA_DIR / "guidelines_index"

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality
EMBEDDING_DIMENSION = 384

# Retrieval settings
TOP_K_SIMILAR_CASES = 5
TOP_K_GUIDELINE_CHUNKS = 3
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50
