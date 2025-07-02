FROM python:3.10-slim

WORKDIR /app

# Instalación de ibrerías necesarias. Se integra la librería ffmpeg para desarrollar una solución utilizando 'Voz'
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar código fuente
COPY backend /app/backend
COPY shared /app/shared
COPY prompts /app/prompts
COPY logs /app/logs
COPY outputs /app/outputs

# Establecer PYTHONPATH para que "agent" sea importable
ENV PYTHONPATH="/app/backend"

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]