# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including LaTeX and Git LFS
RUN apt-get update && apt-get install -y \
    texlive-xetex \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    cm-super \
    curl \
    git \
    git-lfs \
    file \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY ops/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project including .git for LFS
COPY . /app/

# Configure Git and fetch Git LFS content to get actual image files
RUN git config --global --add safe.directory /app && \
    git lfs install && \
    if [ -d .git ]; then \
      echo "Git directory found. Fetching LFS objects..." && \
      git lfs fetch --all && \
      echo "Checking out LFS files..." && \
      git lfs checkout && \
      echo "Verifying PNG files are binary (not pointers):" && \
      find data* -name "*.png" -type f -exec file {} \; | head -3; \
    else \
      echo "No .git directory found; LFS files may remain as pointers"; \
    fi && \
    # Move data-full to expected location
    if [ -d "data-full" ]; then \
      echo "Moving data-full to /app/data" && \
      cp -r data-full/* /app/data/ 2>/dev/null || true && \
      echo "Data moved. Sample files:" && \
      find /app/data -name "*.png" -type f | head -3; \
    fi && \
    # Ensure data directory exists
    mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Set environment variables
ENV BASE_DIR=/app/data
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# The startup script is already copied with the project, just fix permissions
RUN if [ -f "ops/start.sh" ]; then \
      cp ops/start.sh /start.sh && \
      sed -i 's/\r$//' /start.sh && \
      chmod +x /start.sh; \
    else \
      echo "Warning: ops/start.sh not found"; \
    fi

# Run the application via startup script (ensures $PORT is honored)
CMD ["/start.sh"]
