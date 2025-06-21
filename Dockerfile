# Stage 1: Use an official Python 3.10 slim image as the base
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files and to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the dependency files first to leverage Docker's layer caching
COPY packages.txt .
COPY requirements.txt .

# Install the system-level dependencies listed in packages.txt
# The '--no-install-recommends' flag prevents installing optional packages.
# The 'rm -rf' command cleans up apt cache to keep the image size down.
RUN apt-get update && \
    apt-get install -y --no-install-recommends $(cat packages.txt) && \
    rm -rf /var/lib/apt/lists/*

# Install the Python packages from requirements.txt
# The '--no-cache-dir' flag reduces image size by not storing the download cache.
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's browsers and their required OS dependencies
# This is a special command provided by the Playwright library.
RUN playwright install --with-deps

# Copy the essential input CSV file that is required for the app to run
COPY EQUITY_L.csv .

# Copy the rest of your application's Python code into the container
# This respects the .dockerignore file.
COPY . .

# Expose the port that Streamlit will run on. This is for documentation and container linking.
EXPOSE 8501

# The command to execute when the container starts.
# We must use --server.address=0.0.0.0 to make the app accessible from outside the container.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]