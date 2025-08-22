# Python base
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies (keep minimal). Add LaTeX toolchain only if you need in-container compilation.
# Also install git and git-lfs to fetch LFS assets (PNGs) during build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ghostscript \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# For LaTeX compilation support (optional, heavy ~1GB+):
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
#     texlive-science \
#     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Fetch Git LFS content if repository metadata is present
RUN git lfs install && \
    if [ -d .git ]; then \
      echo "Fetching Git LFS objects..." && \
      git lfs fetch --all && \
      git lfs checkout; \
    else \
      echo "No .git directory; skipping git LFS"; \
    fi

# Streamlit settings
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
EXPOSE 8501

# Use dynamic PORT for Railway (fallback to 8501 locally)
CMD ["bash", "-lc", "streamlit run app/main_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
