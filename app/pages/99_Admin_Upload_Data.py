"""Admin page for uploading data ZIP files.

This page allows authenticated admin users to upload ZIP files containing
table data that will be extracted to the data directory.
"""

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

# Import your existing auth functions
try:
    from app.auth import check_authentication
except ImportError:
    # Fallback for development
    def check_authentication() -> str | None:
        return "admin"


try:
    from app.config import BASE_DIR
except ImportError:
    # Fallback - use environment variable or detect based on platform
    _base_dir_str = os.environ.get("BASE_DIR")
    if _base_dir_str:
        BASE_DIR = Path(_base_dir_str)
    elif Path("/app").exists():  # Docker/Railway environment
        BASE_DIR = Path("/app/data")
    elif Path(r"E:\ICP_notebooks\Buxton").exists():  # Local Windows
        BASE_DIR = Path(r"E:\ICP_notebooks\Buxton\data")
    else:
        BASE_DIR = Path("./data")  # Relative fallback


def is_within_base(base: str, target: str) -> bool:
    """Check if target path is within base directory to prevent zip slip attacks."""
    base = os.path.abspath(base)
    target = os.path.abspath(target)
    return os.path.commonpath([base]) == os.path.commonpath([base, target])


def extract_zip_safely(zip_bytes: bytes, dest_dir: str) -> None:
    """Extract ZIP file safely to destination directory, preventing zip slip attacks."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Validate no paths escape dest_dir
        for name in zf.namelist():
            # Skip directories and hidden files starting with .
            if name.endswith("/") or os.path.basename(name).startswith("."):
                continue

            dest_path = os.path.join(dest_dir, name)
            if not is_within_base(dest_dir, dest_path):
                raise ValueError(f"Illegal path in zip: {name}")

        # Extract all files
        zf.extractall(dest_dir)


def get_directory_size(path: Path | str) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except OSError:
        pass
    return total_size


def format_size(bytes_size: int) -> str:
    """Format size in bytes to human readable format."""
    size_float = float(bytes_size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} TB"


def get_table_title(table_path: Path | str) -> str:
    """Get table title from info.txt file, or return empty string if not found.

    Args:
        table_path: Path to the table directory

    Returns:
        Table title from info.txt if found and has format 'TITLE: Name of Table',
        otherwise returns empty string.
    """
    info_file = Path(table_path) / "info.txt"
    if not info_file.exists():
        return ""

    try:
        content = info_file.read_text(encoding="utf-8").strip()
        # Look for line starting with "TITLE: "
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("TITLE: "):
                return line[7:].strip()  # Remove "TITLE: " prefix
        return ""
    except Exception:
        return ""


def main():
    st.title("🔧 Admin: Upload Data")

    # Check authentication - only allow logged in users (basic admin check)
    try:
        current_user = check_authentication()
        if not current_user:
            st.error("❌ You must be logged in to access this page.")
            st.info("Please log in to continue.")
            return
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        st.info("Please ensure the authentication system is properly configured.")
        return

    st.success(f"✅ Authenticated as: {current_user}")

    # Ensure BASE_DIR exists
    os.makedirs(BASE_DIR, exist_ok=True)

    # Show current data directory status
    st.subheader("📁 Current Data Directory Status")

    col1, col2 = st.columns(2)
    with col1:
        st.code(f"Target directory: {BASE_DIR}")

    with col2:
        if os.path.exists(BASE_DIR):
            current_size = get_directory_size(BASE_DIR)
            st.metric("Current Size", format_size(current_size))

            # Show subdirectories
            subdirs = [
                d
                for d in os.listdir(BASE_DIR)
                if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".")
            ]
            if subdirs:
                st.write("📊 **Tables found:**")
                for subdir in sorted(subdirs):
                    subdir_path = os.path.join(BASE_DIR, subdir)
                    subdir_size = get_directory_size(subdir_path)
                    table_title = get_table_title(subdir_path)
                    if table_title:
                        st.write(f"  • `{subdir}` - **{table_title}** ({format_size(subdir_size)})")
                    else:
                        st.write(f"  • `{subdir}` ({format_size(subdir_size)})")
        else:
            st.warning("Directory does not exist yet")

    st.divider()

    # Upload section
    st.subheader("📤 Upload Data ZIP File")

    st.info("""
    **Upload Instructions:**
    - Upload a ZIP file containing your table data directories
    - The ZIP should contain folders like `Table5/`, `Table6/`, etc.
    - Each table folder can optionally contain an `info.txt` file with format: `TITLE: Name of Table`
    - If no `info.txt` file exists, the table name will be displayed without a title
    - Maximum file size: 500 MB
    - ⚠️ **Warning**: This will replace existing data in the target directory
    """)

    uploaded_file = st.file_uploader(
        "Choose a ZIP file containing table data",
        type=["zip"],
        help="Select a ZIP file with your data contents",
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📦 **Uploaded file**: `{uploaded_file.name}` ({file_size_mb:.1f} MB)")

        # Show contents of ZIP file
        try:
            with zipfile.ZipFile(uploaded_file) as zf:
                file_list = [f for f in zf.namelist() if not f.endswith("/")]
                st.write(f"📋 **ZIP contains {len(file_list)} files**")

                # Show first few files as preview
                if file_list:
                    st.write("**Preview (first 10 files):**")
                    for filename in file_list[:10]:
                        st.write(f"  • `{filename}`")
                    if len(file_list) > 10:
                        st.write(f"  ... and {len(file_list) - 10} more files")

        except zipfile.BadZipFile:
            st.error("❌ Invalid ZIP file. Please upload a valid ZIP archive.")
            return
        except Exception as e:
            st.error(f"❌ Error reading ZIP file: {str(e)}")
            return

        # Confirmation and extraction
        st.divider()

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🗑️ Clear Existing Data First", type="secondary"):
                try:
                    if os.path.exists(BASE_DIR):
                        # Remove all contents but keep the directory
                        for item in os.listdir(BASE_DIR):
                            item_path = os.path.join(BASE_DIR, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        st.success("✅ Existing data cleared successfully!")
                        st.rerun()
                    else:
                        st.info("ℹ️ Directory was already empty")
                except Exception as e:
                    st.error(f"❌ Error clearing data: {str(e)}")

        with col2:
            if st.button("🚀 Extract ZIP to Data Directory", type="primary"):
                try:
                    with st.spinner("Extracting ZIP file..."):
                        # Extract to temporary directory first, then move
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            extract_zip_safely(uploaded_file.getvalue(), tmp_dir)

                            # Move extracted contents to BASE_DIR
                            for item in os.listdir(tmp_dir):
                                src_path = os.path.join(tmp_dir, item)
                                dst_path = os.path.join(BASE_DIR, item)

                                if os.path.exists(dst_path):
                                    if os.path.isdir(dst_path):
                                        shutil.rmtree(dst_path)
                                    else:
                                        os.remove(dst_path)

                                if os.path.isdir(src_path):
                                    shutil.copytree(src_path, dst_path)
                                else:
                                    shutil.copy2(src_path, dst_path)

                    st.success("✅ **Data uploaded and extracted successfully!**")
                    st.balloons()

                    # Show updated directory status
                    new_size = get_directory_size(BASE_DIR)
                    st.metric("New Directory Size", format_size(new_size))

                    # Suggest next steps
                    st.info(
                        "💡 **Next steps:** Navigate to other pages to verify your data is accessible."
                    )

                    # Auto-refresh the page to show new status
                    st.rerun()

                except ValueError as e:
                    st.error(f"❌ Security error: {str(e)}")
                except zipfile.BadZipFile:
                    st.error("❌ Invalid ZIP file format")
                except Exception as e:
                    st.error(f"❌ Error extracting ZIP file: {str(e)}")

    # Footer with additional info
    st.divider()
    st.caption("""
    🔒 **Security Note**: This upload feature is restricted to administrators only.
    All uploaded files are validated to prevent directory traversal attacks.
    """)


if __name__ == "__main__":
    main()
