import os
from pathlib import Path

AVAILABLE_TABLES = ["table5", "table6", "table7", "table8", "table9"]

# Determine BASE_DIR robustly across environments (Railway Docker, local Windows)
# Priority:
# 1) Explicit BASE_DIR env var if provided
# 2) Docker/Railway: /app/data
# 3) Local Windows development: E:\ICP_notebooks\Buxton\data
# 4) Fallback: ./data relative to config file
_env_base = os.getenv("BASE_DIR")
if _env_base:
    BASE_DIR: Path = Path(_env_base)
else:
    # Check environment-specific paths
    candidates = [
        Path("/app/data"),  # Docker/Railway
        Path(r"E:\ICP_notebooks\Buxton\data"),  # Local Windows development
        Path(__file__).parent.parent / "data",  # Relative fallback
    ]

    for candidate in candidates:
        if candidate.exists():
            BASE_DIR = candidate
            break
    else:
        # If none exist, choose based on platform/environment
        if Path("/app").exists():  # We're in Docker/Railway
            BASE_DIR = Path("/app/data")
        elif Path(r"E:\ICP_notebooks\Buxton").exists():  # Local Windows
            BASE_DIR = Path(r"E:\ICP_notebooks\Buxton\data")
        else:
            # Fallback to relative path
            BASE_DIR = Path(__file__).parent.parent / "data"

# Ensure BASE_DIR exists on import (for uploaded data)
BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_table_paths(table_choice):
    image_dir = BASE_DIR / table_choice / "sub_tables_images"
    pdf_dir = image_dir / "csv" / "latex"
    tsv_dir = image_dir / "csv"
    db_path = image_dir / "validation_db.json"
    return image_dir, pdf_dir, tsv_dir, db_path
