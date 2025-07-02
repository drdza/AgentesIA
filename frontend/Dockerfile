FROM python:3.10

WORKDIR /app

COPY frontend /app/frontend
COPY shared /app/shared
COPY prompts /app/prompts
COPY logs /app/logs
COPY outputs /app/outputs

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "frontend/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
