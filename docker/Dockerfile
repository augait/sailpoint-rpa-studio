FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && playwright install --with-deps chromium firefox
COPY . .
RUN pip install --no-deps . && useradd --create-home --uid 10001 studio && mkdir -p /data/artifacts && chown -R studio:studio /data /opt/playwright
USER studio
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
