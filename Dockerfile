FROM python:3.12-slim

WORKDIR /app

# Install Node.js for JS code execution support
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Default: launch Web UI
CMD ["python", "web_ui.py"]
