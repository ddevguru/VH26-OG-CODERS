FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements & install dependencies
COPY pyproject.toml README.md /app/
COPY core/ /app/core/
COPY interfaces/ /app/interfaces/
COPY presentation/ /app/presentation/
COPY services/ /app/services/

RUN pip install --no-cache-dir .

ENTRYPOINT ["leakguard"]
CMD ["scan", "."]
