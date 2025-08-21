import math
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.config import AVAILABLE_TABLES, get_table_paths
from app.db_utils import load_db
from app.import_reactions import import_single_csv_idempotent
from app.reactions_db import ensure_db, set_validated_by_source
from fast_populate_db import bulk_import_validated_sources as _fast_build

CHUNK_SIZE = 50
DB_FILE = Path("reactions.db")


def _safe_remove_db_files(db_path: Path, retries: int = 10, backoff_s: float = 0.2) -> None:
    """Remove SQLite DB and sidecars with retries (Windows-friendly)."""
    targets = [db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")]
    def try_unlink(p: Path) -> None:
        if not p.exists():
            return
        last_err: Exception | None = None
        for i in range(retries):
            try:
                p.unlink()
                return
            except PermissionError as e:
                last_err = e
                time.sleep(backoff_s * (i + 1))
            except Exception:
                raise
        raise PermissionError(
            f"Could not remove '{p}'. Close any process using the database and retry."
        ) from last_err
    for t in targets:
        try_unlink(t)


def collect_sources(tables: list[str]) -> list[tuple[int, Path, dict[str, Any]]]:
    sources: list[tuple[int, Path, dict[str, Any]]] = []
    for t in tables:
        try:
            tno = int(t.replace("table", ""))
        except Exception:
            continue
        IMAGE_DIR, PDF_DIR, TSV_DIR, DB_JSON_PATH = get_table_paths(t)
        if not DB_JSON_PATH.exists():
            print(f"[SKIP] {t} has no validation_db.json at {DB_JSON_PATH}")
            continue
        try:
            db = load_db(DB_JSON_PATH, IMAGE_DIR)
        except Exception as e:
            print(f"[WARN] Failed to load {DB_JSON_PATH}: {e}")
            continue
        for img, meta in db.items():
            # normalize meta
            if isinstance(meta, bool):
                meta = {"validated": bool(meta), "by": None, "at": None}
            stem = Path(img).stem
            csv_path = TSV_DIR / f"{stem}.csv"
            tsv_path = TSV_DIR / f"{stem}.tsv"
            source = csv_path if csv_path.exists() else (tsv_path if tsv_path.exists() else None)
            if source is None:
                print(f"[MISS] {t} image {img}: no TSV/CSV at {csv_path} or {tsv_path}")
                continue
            sources.append((tno, source, meta))
    return sources


def rebuild_db_from_validations(chunk_size: int = CHUNK_SIZE):
    # Try normal open and clean; if DB is corrupted, nuke file and recreate
    try:
        con = ensure_db()
        # Wait for locks
        try:
            con.execute("PRAGMA busy_timeout = 5000")
        except Exception:
            pass
        cur = con.cursor()
        tables = ["measurements", "reactions_fts", "reactions", "references_map"]
        for tbl in tables:
            retries = 5
            for i in range(retries):
                try:
                    cur.execute(f"DELETE FROM {tbl}")
                    break
                except sqlite3.OperationalError as oe:
                    if "locked" in str(oe).lower() and i < retries - 1:
                        time.sleep(0.3 * (i + 1))
                        continue
                    raise
        con.commit()
    except sqlite3.DatabaseError as e:
        msg = str(e).lower()
        if "malformed" in msg or "disk image" in msg:
            print("[WARN] DB appears corrupted. Recreating reactions.db ...")
            try:
                _safe_remove_db_files(DB_FILE)
            except Exception as del_err:
                raise RuntimeError(f"Failed to remove corrupted DB: {del_err}")
            con = ensure_db()
            # DB is fresh; nothing to delete
        else:
            raise

    tasks = collect_sources(AVAILABLE_TABLES)
    total = len(tasks)
    if total == 0:
        print("[INFO] No sources discovered from validation_db.json. Nothing to import.")
        return

    chunks = math.ceil(total / chunk_size)
    processed = 0
    print(f"[START] Importing {total} sources in {chunks} chunks (chunk_size={chunk_size})")

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, total)
        batch = tasks[start:end]
        batch_imported = 0
        batch_validated_updates = 0
        for tno, source, meta in batch:
            try:
                rcount, _ = import_single_csv_idempotent(source, tno)
                batch_imported += rcount or 0
            except Exception as e:
                print(f"[ERR][IMPORT] table={tno} source={source}: {e}")
                continue
            try:
                updated = set_validated_by_source(
                    con,
                    str(source),
                    bool(meta.get("validated", False)),
                    by=meta.get("by"),
                    at_iso=meta.get("at"),
                )
                batch_validated_updates += updated
            except Exception as e:
                print(f"[ERR][VALIDATE] table={tno} source={source}: {e}")
        processed = end
        pct = processed * 100.0 / total
        print(
            f"[PROGRESS] {processed}/{total} ({pct:.1f}%) | batch_imported={batch_imported} batch_validated_updates={batch_validated_updates}"
        )

    # Reindex FTS5
    try:
        con.execute("INSERT INTO reactions_fts(reactions_fts) VALUES('rebuild')")
        con.commit()
        print("[FTS] Rebuilt reactions_fts index")
    except Exception as e:
        print(f"[FTS][WARN] Failed to rebuild FTS: {e}")

    # Summary
    rcount = con.execute("SELECT COUNT(*) FROM reactions").fetchone()[0]
    mcount = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    print(f"[DONE] Recreated DB. reactions={rcount}, measurements={mcount}")


def build_db_offline_fast(build_path: Path = Path("reactions_build.db")) -> None:
    """Build a fresh DB offline using the fast importer into build_path.

    This does not touch the live DB file. It removes any existing build_path first.
    """
    if build_path.exists():
        _safe_remove_db_files(build_path)
    # Reuse fast bulk builder pointed at the build file
    _fast_build(build_path)

def swap_live_db(build_path: Path, live_path: Path = DB_FILE, backup: bool = True, retries: int = 15, backoff_s: float = 0.25) -> None:
    """Atomically replace live DB with build DB with Windows-friendly retries.

    Caller MUST ensure no open connections hold the live DB before calling.
    """
    # Best-effort: checkpoint WAL to reduce locks
    try:
        con = sqlite3.connect(str(live_path))
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            con.close()
    except Exception:
        pass

    # Remove live sidecars to avoid conflicts
    for p in [Path(str(live_path) + "-wal"), Path(str(live_path) + "-shm")]:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

    # Backup current live DB if requested, with retries for Windows locks
    bak = live_path.with_suffix(".bak")
    if backup and live_path.exists():
        # Ensure previous backup doesn't block
        try:
            if bak.exists():
                bak.unlink()
        except Exception:
            pass
        last_err: Exception | None = None
        for i in range(retries):
            try:
                live_path.replace(bak)
                last_err = None
                break
            except PermissionError as e:
                last_err = e
                time.sleep(backoff_s * (i + 1))
            except Exception:
                raise
        if last_err is not None:
            raise PermissionError(
                f"Failed to move '{live_path}' to backup '{bak}'. It appears to be in use by another process."
            ) from last_err

    # Move build to live with retries
    last_err2: Exception | None = None
    for i in range(retries):
        try:
            build_path.replace(live_path)
            last_err2 = None
            break
        except PermissionError as e:
            last_err2 = e
            time.sleep(backoff_s * (i + 1))
        except Exception:
            raise
    if last_err2 is not None:
        raise PermissionError(
            f"Failed to activate new DB '{build_path}' -> '{live_path}'. File may be locked."
        ) from last_err2


if __name__ == "__main__":
    rebuild_db_from_validations()
