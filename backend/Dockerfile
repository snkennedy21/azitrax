FROM python:3.12-slim

WORKDIR /app

# Prevents Python from writing .pyc bytecode files into __pycache__/ directories.
ENV PYTHONDONTWRITEBYTECODE=1 

# Makes Python write logs/output immediately instead of buffering stdout/stderr.
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
