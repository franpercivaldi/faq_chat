# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Sistema base (opcional pero útil para debug)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dependencias de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiamos el proyecto (en dev lo vas a montar como volumen igualmente)
COPY . /app

# Puerto de la API
EXPOSE 8080

# Comando por defecto (dev, con recarga)
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
