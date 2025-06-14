# backend/core/llm.py

import sys
import os
import requests
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.utils import load_config, log_to_file
from core.config import model_mapper
from core.exceptions import InferenceServiceError

CONFIG_JSON = load_config()
MODEL_ENDPOINTS = CONFIG_JSON["model_endpoints"]["api_endpoints"]

def call_model(model: str, prompt: str):
    """
    Llama al endpoint del modelo correspondiente según el tipo solicitado.
    Retorna el contenido generado como string.
    """
    start_time = time.time()
    model_id = model.lower()
    model_type = model_mapper(model_id)    
    server_type = CONFIG_JSON["model_endpoints"]["server_type"].get(model_id)

    try:
        endpoint = MODEL_ENDPOINTS.get(model_id)
        if not endpoint:
            raise InferenceServiceError(f"Modelo '{model_id}' no soportado o no mapeado.")

        match server_type:
            case "TGI":
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "temperature": 0.1,              # Control de aleatoriedad — bajo para respuestas estables
                        "top_p": 1.0,                    # No limitar vocabulario — importante si hay palabras técnicas
                        "top_k": 50,                     # Recorta un poco las opciones menos probables
                        "repetition_penalty": 1.2,       # Penaliza repeticiones (importante en SQL malformado)
                        "frequency_penalty": 0.0,        # No penalices palabras frecuentes (necesarias en SQL)
                        "max_new_tokens": 512,           # Tamaño razonable para SQL de varias líneas
                        "return_full_text": False,       # Solo quieres la respuesta, no el prompt embebido
                        "do_sample": False,              # Desactiva sampling = más determinismo
                        "details": False                 # No necesitas logits ni estructura extendida
                        }
                }
            case "TRANSFORMERS":           # Usar formato de mensajes estilo OpenAI
                payload = {
                    "model": model_type,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False
                }
            case "NIMs":                
                payload = {
                    "prompt": prompt,
                    "model": model_type
                }
    
        response = requests.post(url=endpoint, json=payload, timeout=180)

        if response.status_code != 200:
            raise InferenceServiceError(f"Error del modelo '{model_type}' – HTTP {response.status_code}: {response.text}")
                
        data = response.json()

        # Decodificación dinámica del resultado según el tipo de modelo
        if model_id in CHAT_MODELS:
            content = data["choices"][0]["message"]["content"].strip()
        else:
            content = data["sql"].strip()

        if not content:
            raise InferenceServiceError("La respuesta del modelo no contiene contenido válido.")
        
        duration = round(time.time() - start_time, 2)
        return content, duration, data

    except (requests.RequestException, ValueError, KeyError) as e:        
        raise InferenceServiceError("Fallo al conectarse o procesar la respuesta del modelo") from e


def call_model_streaming(model: str, prompt: str):
    """
    Ejecuta una inferencia en modo streaming si el modelo lo soporta.
    Compatible con modelos tipo chat que usan el formato 'messages' y retorno de fragmentos.
    """
    model_id = model.lower()
    model_use = model_mapper(model_id)
    try:
        endpoint = MODEL_ENDPOINTS.get(model_id)

        if not endpoint:
            raise InferenceServiceError(f"Modelo '{model_id}' no tiene endpoint registrado.")
        if model_id not in CHAT_MODELS:
            raise InferenceServiceError(f"Modelo '{model_id}' no soporta streaming.")

        # Modelos que soportan chat streaming con 'messages' y 'delta'
        if model_id in CHAT_MODELS:
            payload = {
                "model": model_use,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
    
        response = requests.post(
            url=endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=120
        )
        if response.status_code != 200:
            raise InferenceServiceError(f"Error HTTP del modelo '{model_id}' – código {response.status_code}: {response.text}")
        
        buffer = ""

        for line in response.iter_lines():
            if line and line.decode().startswith("data:"):
                payload = line.decode().replace("data: ", "")
                
                if payload.strip() == "[DONE]":
                    break
                
                try:
                    data = json.loads(payload)                    
                    delta = data["choices"][0]["delta"]

                    if "content" in delta:
                        chunk = delta["content"]
                        buffer += chunk
                        yield chunk
                except json.JSONDecodeError:
                    log_to_file(f"[CALL MODEL STREAMING ERROR] Fragmento malformado: {payload}")
                    continue

    except (requests.RequestException, ValueError) as e:
        raise InferenceServiceError(f"Error en la conexión o formato de respuesta del modelo '{model_id}'") from e
