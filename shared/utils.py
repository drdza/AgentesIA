# shared/utils.py

import sys
import os
import time
import uuid
import csv
import json
import re
from pathlib import Path
from datetime import datetime



# Archivo de configuración
CONFIG_FILE = "shared/config_dev.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    else:
        raise "No existe un archivo de configuración <<config.json>>"


def init_config():
    global LOG_FOLDER, OUTPUT_FOLDER, JSONL_OUTPUT, API_LOG_FILE, LOG_FILE

    CONFIG_JSON = load_config()
    LOG_FOLDER = CONFIG_JSON["log_folder"]
    OUTPUT_FOLDER = CONFIG_JSON["output_folder"]
    JSONL_OUTPUT = CONFIG_JSON["jsonl_output"]
    API_LOG_FILE = CONFIG_JSON["api_log_file"]
    LOG_FILE = CONFIG_JSON["log_file"]

    os.makedirs(LOG_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Utilidad para generar un ID único por consulta
def generate_request_id():
    return str(uuid.uuid4())

# Utilidad para medir tiempos de ejecución
class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.interval = self.end - self.start

# Logging general
def log_to_file(message: str, api: bool = False):
    log_file = API_LOG_FILE if api else LOG_FILE
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

# Exportación JSONL
def export_jsonl(entry: dict):
    with open(JSONL_OUTPUT, "a", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)
        f.write("\n")

# Formatear respuesta para logs o terminal
def format_log_entry(entry: dict) -> str:
    return (
        f"ID: {entry.get('request_id')} | "
        f"Pregunta: {entry.get('original_question')} | "
        f"Modelo: {entry.get('selected_model')} | "
        f"Estado: {entry.get('status')} | "
        f"Tiempo: {entry.get('response_time', 0):.2f}s"
    )

def load_prompt_template( domain: str, template_name: str) -> str:
    """
    Carga una plantilla de prompt desde el directorio /prompts.

    Args:
        domian (str): Path del dominio a utilizar.
        template_name (str): Nombre del archivo de la plantilla.

    Returns:
        str: Contenido de la plantilla.
    """    
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
    template_path = os.path.join(base_path, domain, template_name)


    try:
        with open(template_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"⚠️ No se encontró la plantilla de prompt: {template_path}")
    

def log_event(
    request_id: str,
    client_ip: str,
    user_question: str,
    reformulation: str,
    flow: str,
    generated_sql: str,
    result: dict,
    type_result: str,
    model: str = "",
    domain: str = "",
    duration: float = 0.0,
    tags: list = None
):
    message = "OK"
    log_day = datetime.now().strftime("%Y%m%d")
    # tipo = success
    
    # Ruta absoluta a la carpeta de logs
    root_path = Path(__file__).resolve().parent.parent

    # Validar y normalizar type_result
    type_result = str(type_result).strip().lower()
    if type_result not in {"success", "fails"}:
        type_result = "fails"

    log_dir = root_path / "outputs" / type_result
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"ptuning_{type_result}_cases_{log_day}.jsonl"

    event = {
        "request_id": request_id,
        "client_ip": client_ip,
        "timestamp": datetime.now().isoformat(),
        "status": type_result,
        "original_question": user_question,
        "enhanced_question": reformulation,
        "flow": flow,
        "generated_sql": generated_sql,
        "result": result,
        "model": model,
        "domain": domain,
        "duration": round(duration, 2),
        "tags": tags or []
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            json.dump(event, f, ensure_ascii=False, default=str)
            f.write("\n")
    except Exception as e:
        message = f"{e}"

    return event, message

        
