# Use the official Playwright Python Docker image as base (pre-includes browsers and deps)
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# Install Xvfb and x11vnc for virtual display and VNC access
RUN apt-get update && apt-get install -y xvfb x11vnc && rm -rf /var/lib/apt/lists/*

# Define the application directory
ARG APP_HOME=/app
WORKDIR ${APP_HOME}

# Define a build argument to determine which environment to use
ARG BUILD_ENV=production

# Install uv using pip (since the base has pip)
RUN pip install uv

# Copy pyproject.toml first for dependency resolution
COPY pyproject.toml ./

RUN uv pip install --system .

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy necessary startup scripts
COPY ./scripts/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copy the entire application code to the app directory
COPY . ${APP_HOME}

# Set the working directory
WORKDIR ${APP_HOME}

