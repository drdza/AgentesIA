# backend/core/llm.py

import sys
import os
import requests
import time
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.utils import load_config, log_to_file
from core.config import model_mapper
from core.exceptions import InferenceServiceError

logger = logging.getLogger("llm")
logger.setLevel(logging.INFO)

CONFIG_JSON = load_config()
MODEL_ENDPOINTS = CONFIG_JSON["model_endpoints"]["api_endpoints"]

if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def call_model(model: str, system_prompt: str, user_prompt: str = ""):
    """
    Llama al endpoint del modelo correspondiente según el tipo solicitado.
    Retorna el contenido generado como string.
    """
    start_time = time.time()
    model_id = model.lower()
    model_type = model_mapper(model_id)    
    server_type = CONFIG_JSON["model_endpoints"]["server_type"].get(model_id)
    # logger.info(f"Server Type: {server_type}")

    try:
        endpoint = MODEL_ENDPOINTS.get(model_id)

        if not endpoint:
            raise InferenceServiceError(f"Modelo '{model_id}' no soportado o no mapeado.")

        match server_type:

            case "NIMs":
                prompt_text = system_prompt.format(question = user_prompt)                
                messages = [
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ]

                payload = {
                    "model": model_type,
                    "messages": messages,
                    "stream": False,
                    "temperature": 1
                }

            case "TRANSFORMERS":
                payload = {
                    "prompt": system_prompt                
                }

            case "TGI":                     
                payload = {
                    "inputs": system_prompt,
                    "parameters": {
                        "temperature": 0.00001,
                        "num_beams": 3,
                        "top_p": 0.99,
                        "top_k": 50,
                        "repetition_penalty": 1.2,
                        "frequency_penalty": 0.0,
                        "max_new_tokens": 2048,
                        "return_full_text": False,
                        "do_sample": False,
                        "details": False
                        }
                }

            case "CHAT":
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                #logger.info(messages)
                payload = {
                    "messages": messages,
                    "temperature": 0.01,
                    "stream":False,
                    "num_beams": 3,
                    "top_p": 0.99,
                    "top_k": 50,
                    "repetition_penalty": 1.2,
                    "frequency_penalty": 0.0,
                    "max_new_tokens": 2048,
                    "return_full_text": False,
                    "do_sample": False,
                    "details": False                    
                }
                #logger.info(payload)


        response = requests.post(url=endpoint, json=payload, timeout=180)        
        if response.status_code != 200:
            raise InferenceServiceError(f"Error del modelo '{model_type}' – HTTP {response.status_code}: {response.text}")

        data = response.json()        

        if server_type == 'NIMs' or server_type == 'CHAT':
            content = data["choices"][0]["message"]["content"].strip()
        elif server_type == 'TGI':
            content = data["generated_text"].strip()
        else:
            content = data["sql"]

        if not content:
            raise InferenceServiceError("La respuesta del modelo no contiene contenido válido.")

        duration = round(time.time() - start_time, 2)
        return content, duration, data

    except (requests.RequestException, ValueError, KeyError) as e:
        raise InferenceServiceError("Fallo al conectarse o procesar la respuesta del modelo") from e

