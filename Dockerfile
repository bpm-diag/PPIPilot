# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for pm4py and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/data /app/testfolder

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "interface_2.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
