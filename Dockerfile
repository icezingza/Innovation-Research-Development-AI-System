FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# สร้าง non-root user
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
