# Multi-stage build to ensure Git LFS assets are materialized even when .git is absent in the build context (e.g., on Railway)

# 1) Fetch stage: clone repo and checkout LFS files
FROM python:3.11-slim AS fetch

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    ca-certificates \
    file \
    && rm -rf /var/lib/apt/lists/*

RUN git lfs install

ARG REPO=https://github.com/Saldenisov/radreactions.git
# You can override REF at build time to pin to a tag/commit: --build-arg REF=<sha-or-tag>
ARG REF=main

RUN git clone --depth=1 --branch "$REF" "$REPO" /src && \
    cd /src && \
    git lfs fetch --all && \
    git lfs checkout && \
    # Optional verification (non-fatal): ensure some PNGs are real binaries, not LFS pointers
    (find data-full -name "*.png" -type f -exec file {} \; | head -5 || true)

# 2) Runtime stage: minimal runtime with app and resolved data copied in
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# System deps needed to run the app and build some wheels (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY --from=fetch /src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and data (with LFS files materialized)
COPY --from=fetch /src/app /app/app
COPY --from=fetch /src/data-full /app/data-full

EXPOSE 8501
# Use sh for POSIX-compatible parameter expansion (no need for bash in slim)
CMD ["sh", "-lc", "streamlit run app/main_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
