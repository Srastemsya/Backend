FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runtime/ .
CMD ["uvicorn", "runtime:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--log-level", "warning"]
