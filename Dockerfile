# Build stage: fetch application code only (data comes from uploads)
FROM python:3.11-slim AS fetch

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG REPO=https://github.com/Saldenisov/radreactions.git
# You can override REF at build time to pin to a tag/commit: --build-arg REF=<sha-or-tag>
ARG REF=main

# Clone repo for application code and requirements
RUN git clone --depth=1 --branch "$REF" "$REPO" /src

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

# Copy the application code (data comes from uploads via admin interface)
COPY --from=fetch /src/app /app/app

# Create data directory for uploads (will be mounted as volume in production)
RUN mkdir -p /app/data

EXPOSE 8501
# Use sh for POSIX-compatible parameter expansion (no need for bash in slim)
CMD ["sh", "-lc", "streamlit run app/main_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
