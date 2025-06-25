# backend/core/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta ABSOLUTA al .env (sube 1 nivel desde core/)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)  # Carga el .env desde la ruta correcta

# Rutas de salida
LOG_FOLDER = os.getenv('LOG_FOLDER', './logs')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', './outputs')

# Archivos de log
LOG_FILE = os.path.join(LOG_FOLDER, 'execution_log.txt')
API_LOG_FILE = os.path.join(LOG_FOLDER, 'api_log.txt')
JSONL_OUTPUT = os.path.join(OUTPUT_FOLDER, 'log_respuestas.jsonl')
CSV_OUTPUT = os.path.join(OUTPUT_FOLDER, 'log_respuestas.csv')

# Configuración base de datos (real)
DB_CONNECTIONS = {
"DWHReymaOP":
    {
        "host": os.getenv('DB_HOST'),
        "port": os.getenv('DB_PORT'),
        "dbname": os.getenv('DB_NAME_INN_TICKETS'),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD')
    },
"DWHReyma":
    {
        "host": os.getenv('DB_HOST'),
        "port": os.getenv('DB_PORT'),
        "dbname": os.getenv('DB_NAME_RY_VENTAS'),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD') 
    }
}


def model_mapper(model: str):
    mapping = {
        "gemma": "google/gemma-2-9b-it",
        "llama": "meta/llama-3.1-8b-instruct",
        "mistral": "mistral/mistral-7b-instruct-v0.3",        
        "hermes": "teknium/openhermes-2.5-mistral-7b",
        "deepseek": "deepseek-ai/deepseek-coder-6.7b-instruct",
        "mixtral": "mistralai/mixtral-8x7b-instruct-v0.1",
        "starcoder": "bigcode/starcoder2-15b",
        "codellama": "codellama/codellama-13b-instruct-hf",
    }
    return mapping.get(model.lower(), model)