# backend/core/llm.py

import sys
import os
import requests
import time
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.utils import load_config


CONFIG_JSON = load_config()
MODEL_ENDPOINTS = CONFIG_JSON["model_endpoints"]

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

def call_model(model: str, prompt: str):    
    start_time = time.time()
    model_id = model.lower()
    model_use = model_mapper(model_id)
    model_endpoint = MODEL_ENDPOINTS.get(model_id)

    if not model_endpoint:
        raise ValueError(f"Modelo '{model_use}' no está configurado en MODEL_ENDPOINTS.")
    
    chat_models = {"gemma", "llama", "mixtral", "deepseek", "starcoder", "codellama"}

    if model_id in chat_models:
        # Usar formato de mensajes estilo OpenAI
        payload = {
            "model": model_use,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    else:
        # Usar formato clásico con prompt directo
        payload = {
            "prompt": prompt,
            "model": model_use
        }

    try:
        response = requests.post(
            url=model_endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=180
        )

        response.raise_for_status()
        data = response.json()

        # Decodificación dinámica del resultado según el tipo de modelo
        if model_id in chat_models:
            generated_text = data["choices"][0]["message"]["content"]
        else:
            generated_text = data["sql"]

        duration = round(time.time() - start_time, 2)
        return generated_text, duration, data

    except requests.RequestException as e:
        print(f"🚨 Error al invocar el modelo {model}: {e}")
        raise e


def call_model_streaming(model: str, prompt: str):
    """
    Ejecuta una inferencia en modo streaming si el modelo lo soporta.
    Compatible con modelos tipo chat que usan el formato 'messages' y retorno de fragmentos.
    """
    model_id = model.lower()
    model_use = model_mapper(model_id)
    model_endpoint = MODEL_ENDPOINTS.get(model_id)

    if not model_endpoint:
        raise ValueError(f"Modelo '{model_use}' no está configurado en MODEL_ENDPOINTS.")

    # Modelos que soportan chat streaming con 'messages' y 'delta'
    chat_models = {"gemma", "llama", "mixtral", "deepseek", "starcoder", "codellama"}

    if model_id in chat_models:
        payload = {
            "model": model_use,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }
    else:
        raise NotImplementedError(f"El modelo '{model_id}' no soporta streaming en este flujo.")
    try:
        response = requests.post(
            url=model_endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=120
        ) 
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
                    continue

    except requests.RequestException as e:
        print(f"🚨 Error al invocar modelo en streaming ({model_id}): {e}")
        raise e
