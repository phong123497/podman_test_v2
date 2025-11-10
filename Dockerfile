# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System deps for FAISS wheels and MySQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py ./

ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app:create_app \
    MYSQL_HOST=mysql \
    MYSQL_USER=appuser \
    MYSQL_PASSWORD=apppassword \
    MYSQL_DATABASE=appdb \
    MYSQL_PORT=3306

EXPOSE 5000

CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:5000", "-w", "2", "--timeout", "120"]


