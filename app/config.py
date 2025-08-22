import os
from pathlib import Path

AVAILABLE_TABLES = ["table5", "table6", "table7", "table8", "table9"]

# Determine BASE_DIR robustly across environments (Railway Docker, local Windows)
# Priority:
# 1) Explicit BASE_DIR env var if provided
# 2) Local repo data folder (data next to this file)
# 3) Common container paths (/app/data preferred, then /data)
# 4) Local Windows development path
_env_base = os.getenv("BASE_DIR")
if _env_base:
    _env_path = Path(_env_base)
    if _env_path.exists():
        BASE_DIR = _env_path
    else:
        BASE_DIR = Path(__file__).parent / "data"
else:
    # After repo restructuring, data lives at the project root, one level above this file
    local_data = Path(__file__).parent.parent / "data"
    if local_data.exists():
        BASE_DIR = local_data
    else:
        candidates = [
            Path("/app/data"),
            Path("/data"),
            Path(r"E:\\ICP_notebooks\\Buxton"),
        ]
        for _p in candidates:
            if _p.exists():
                BASE_DIR = _p
                break
        else:
            # Default to local data (created later) to keep paths consistent
            BASE_DIR = local_data

# Ensure BASE_DIR exists on import (for uploaded data)
BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_table_paths(table_choice):
    image_dir = BASE_DIR / table_choice / "sub_tables_images"
    pdf_dir = image_dir / "csv" / "latex"
    tsv_dir = image_dir / "csv"
    db_path = image_dir / "validation_db.json"
    return image_dir, pdf_dir, tsv_dir, db_path
