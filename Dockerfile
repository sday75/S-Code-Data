# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies needed for building packages like dbus-python
# 'build-essential' provides compilers (like gcc) and other development tools
# 'pkg-config' is also often required for packages that use system libraries
# 'libdbus-1-dev' is specific for dbus-python
# 'libglib2.0-dev' is required for the glib-2.0 dependency found in the logs
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libdbus-1-dev \
    libglib2.0-dev \
    # Clean up apt caches to keep the image size small
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file and install dependencies
# This step is done separately to leverage Docker's caching,
# so dependencies are not reinstalled on every code change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire Python application code into the container
# This copies everything from your project directory (where Dockerfile is)
# into /app inside the container
COPY . .

# Define the command to run your application when the container starts.
# This should point to your main Python script.
# Replace 'sec_form4_extractor.py' with the actual name of your main Python file
CMD ["python", "sec_form4_extractor.py"]
