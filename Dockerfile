# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies needed for building packages like dbus-python
# 'build-essential' provides compilers (like gcc) and other development tools
# 'pkg-config' is also often required for packages that use system libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libdbus-1-dev \
    # Clean up apt caches to keep the image size small
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire Python application code into the container
COPY . .

# Define the command to run your application when the container starts.
CMD ["python", "sec_form4_extractor.py"]
