FROM python:3.12-slim

WORKDIR /app

# Install Java for Flyway
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Flyway CLI
ENV FLYWAY_VERSION=10.13.0
RUN wget -qO- https://repo1.maven.org/maven2/org/flywaydb/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}.tar.gz | tar xvz \
    && mv flyway-${FLYWAY_VERSION} /opt/flyway \
    && ln -s /opt/flyway/flyway /usr/local/bin/flyway \
    && chmod +x /usr/local/bin/flyway

# Prevents Python from writing .pyc bytecode files into __pycache__/ directories.
ENV PYTHONDONTWRITEBYTECODE=1

# Makes Python write logs/output immediately instead of buffering stdout/stderr.
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
