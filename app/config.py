import os
from pathlib import Path

AVAILABLE_TABLES = ["table5", "table6", "table7", "table8", "table9"]

# Determine BASE_DIR robustly across environments (Railway Docker, local Windows)
# Priority:
# 1) DATA_DIR env var if provided
# 2) BASE_DIR env var if provided (back-compat)
# 3) Railway/Docker: /data (mounted volume)
# 4) Legacy Docker path: /app/data
# 5) Local Windows development: E:\ICP_notebooks\Buxton\data
# 6) Fallback: ./data relative to project
_env_data = os.getenv("DATA_DIR")
_env_base = os.getenv("BASE_DIR")

if _env_data:
    BASE_DIR = Path(_env_data)
elif _env_base:
    BASE_DIR = Path(_env_base)
else:
    # Check environment-specific paths in order of preference
    # For Railway/Docker, always prefer /data if it exists as a mount point
    if Path("/").exists():  # Container environment
        # In containers, prioritize /data volume mount over /app/data
        if Path("/data").exists():
            BASE_DIR = Path("/data")
        else:
            BASE_DIR = Path("/app/data")  # Legacy fallback
    elif Path(r"E:\\ICP_notebooks\\Buxton").exists():  # Local Windows
        BASE_DIR = Path(r"E:\\ICP_notebooks\\Buxton\\data")
    else:
        # Local development fallback
        BASE_DIR = Path(__file__).parent.parent / "data"

# Ensure BASE_DIR exists on import (for uploaded data)
BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_table_paths(table_choice):
    image_dir = BASE_DIR / table_choice / "sub_tables_images"
    pdf_dir = image_dir / "csv" / "latex"
    tsv_dir = image_dir / "csv"
    db_path = image_dir / "validation_db.json"
    return image_dir, pdf_dir, tsv_dir, db_path


def get_data_dir() -> Path:
    """Return the resolved data directory path used by the app."""
    return BASE_DIR
