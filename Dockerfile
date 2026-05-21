FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first for layer caching.
COPY bot/requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r /app/bot/requirements.txt

# Copy code and data.
COPY bot /app/bot
COPY questions.json /app/questions.json
RUN mkdir -p /app/data
COPY data/distractors.json /app/data/distractors.json

# DB lives on a Fly volume mounted at /data; ensure dir exists locally too.
RUN mkdir -p /data

CMD ["python", "-m", "bot.bot"]
