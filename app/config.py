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
    candidates = [
        Path("/data"),  # Preferred Railway volume mount
        Path("/app/data"),  # Legacy path
        Path(r"E:\\ICP_notebooks\\Buxton\\data"),  # Local Windows development
        Path(__file__).parent.parent / "data",  # Relative fallback
    ]

    for candidate in candidates:
        if candidate.exists():
            BASE_DIR = candidate
            break
    else:
        # If none exist, choose based on platform/environment
        if Path("/data").exists() or Path("/").exists():  # Container environment
            BASE_DIR = Path("/data")
        elif Path(r"E:\\ICP_notebooks\\Buxton").exists():  # Local Windows
            BASE_DIR = Path(r"E:\\ICP_notebooks\\Buxton\\data")
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


def get_data_dir() -> Path:
    """Return the resolved data directory path used by the app."""
    return BASE_DIR
