import os
import sys
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.utils import  load_config

# Configuración
CONFIG_JSON = load_config()
EMBEDDING_ENDPOINT = CONFIG_JSON["embedding_endpoint"]
THRESHOLD = 0.85  # Umbral de similitud

def get_embedding(text: str) -> np.ndarray:
    """Llama al endpoint de embeddings y regresa el vector."""
    payload = {
        "input": [text],
        "model": "nvidia/nv-embedqa-e5-v5",
        "input_type": "query",
        "encoding_format": "float"
    }
    try:
        response = requests.post(EMBEDDING_ENDPOINT, json=payload)
        response.raise_for_status()
        embedding = response.json()["data"][0]["embedding"]
        return np.array(embedding)
    except Exception as e:
        print(f"❌ Error obteniendo embedding: {e}")
        return np.array([])

def compare_questions(q1: str, q2: str, threshold: float = THRESHOLD) -> None:
    """Compara dos preguntas y calcula su similitud semántica."""
    print(f"\n📌 Pregunta 1:\n{q1}")
    print(f"\n📌 Pregunta 2:\n{q2}")

    emb1 = get_embedding(q1)
    emb2 = get_embedding(q2)

    if emb1.size == 0 or emb2.size == 0:
        print("❌ No se pudieron obtener los embeddings.")
        return

    sim = cosine_similarity([emb1], [emb2])[0][0]
    print(f"\n🔍 Similitud coseno: {sim:.4f}")

    if sim >= threshold:
        print("✅ Se consideran semánticamente similares.")
    else:
        print("❌ No se consideran similares.")


if __name__ == "__main__":
    pregunta1 = input("📝 Ingresa la primera pregunta: ")
    pregunta2 = input("📝 Ingresa la segunda pregunta: ")
    compare_questions(pregunta1, pregunta2)
