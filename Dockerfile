# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the working directory
# This step is done separately to leverage Docker's caching,
# so dependencies are not reinstalled on every code change.
COPY requirements.txt ./

# Install any needed Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code to the working directory
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variables (optional, good practice for common ones)
ENV NAME YourPythonApp

# Run the application when the container launches
# Replace 'app.py' with the actual name of your application's main entry file
CMD ["python", "app.py"]
