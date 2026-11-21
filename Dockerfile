
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install FFmpeg and Supervisor
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create application and Supervisor directories
RUN mkdir -p /tmp/vice0x-data \
    /etc/supervisor/conf.d

# Configure web server and background worker
RUN printf '%s\n' \
    '[supervisord]' \
    'nodaemon=true' \
    'logfile=/dev/null' \
    'pidfile=/tmp/supervisord.pid' \
    '' \
    '[program:web]' \
    'command=python -m app.main' \
    'directory=/app' \
    'autostart=true' \
    'autorestart=true' \
    'startsecs=5' \
    'stdout_logfile=/dev/fd/1' \
    'stdout_logfile_maxbytes=0' \
    'stderr_logfile=/dev/fd/2' \
    'stderr_logfile_maxbytes=0' \
    '' \
    '[program:worker]' \
    'command=python -m app.worker' \
    'directory=/app' \
    'autostart=true' \
    'autorestart=true' \
    'startsecs=5' \
    'stdout_logfile=/dev/fd/1' \
    'stdout_logfile_maxbytes=0' \
    'stderr_logfile=/dev/fd/2' \
    'stderr_logfile_maxbytes=0' \
    > /etc/supervisor/conf.d/vice0x.conf

EXPOSE 7860

CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/vice0x.conf"]
