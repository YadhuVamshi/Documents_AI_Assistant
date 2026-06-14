# 1. Base Image
# Use a lightweight official Python 3.11 image.
FROM python:3.11-slim

# 2. Working Directory
# Define the directory inside the container where files will be copied.
WORKDIR /app

# 3. System Dependencies
# Install compiler tools (build-essential) required to compile libraries like ChromaDB and sqlite.
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy Dependency File
# Copy only the requirements first to take advantage of Docker's layer caching.
COPY requirements.txt .

# 5. Install Dependencies
# Install python packages without caching index packages to keep the image slim.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Source Code
# Copy backend files and configurations into the container.
COPY main.py db.py injest.py .env* ./

# 7. Expose Port
# Inform Docker that the container listens on port 8000 at runtime.
EXPOSE 8000

# 8. Start Command
# Run the FastAPI server bound to 0.0.0.0 (all network interfaces) so it can be reached from the host.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
