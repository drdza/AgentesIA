from pymilvus import connections, Collection
import requests
import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.utils import  load_config


logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)

# Evita agregar múltiples handlers si se llama varias veces
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

CONFIG_JSON = load_config()

MILVUS_ENDPOINT = CONFIG_JSON["milvus_endpoint"]
MILVUS_HOST = MILVUS_ENDPOINT["host"]
MILVUS_PORT = MILVUS_ENDPOINT["port"]
EMBEDDING_ENDPOINT = CONFIG_JSON["embedding_endpoint"]
COLLECTIONS_NAME = MILVUS_ENDPOINT["collections"]
SIMILARITY_THRESHOLD = MILVUS_ENDPOINT["similarity_thresholds"]

def generate_embedding(text: str) -> list:
    
    payload = {
        "input": [text],
        "model": "nvidia/nv-embedqa-e5-v5",
        "input_type": "query",
        "encoding_format": "float"
    }

    response = requests.post(EMBEDDING_ENDPOINT, json=payload)
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]

def search_similar_questions(question: str, top_k: int = 3) -> list:
    # Obtener embedding de la pregunta
    embedding = generate_embedding(question)

    # Conectarse a Milvus
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    collection = Collection(COLLECTIONS_NAME["questions"])
    collection.load()

    # Buscar en Milvus
    results = collection.search(
        data=[embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["question"]
    )

    # Formatear resultados
    matches = []
    for hit in results[0]:
        matches.append({
            "score": round(hit.score, 4),
            "question": hit.entity.get("question", "")
        })

    return matches

def search_collection(collection_name: str, query_embedding: list, fields: list, top_k: int, full_search: bool=False):
    from rich import print 

    collection = Collection(collection_name)
    collection.load()
    
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=fields
    )

    if not results or not results[0]:
        return []

    hit_data = [
        {**hit.to_dict()['entity'], "score": hit.distance, "id": hit.id} 
        for hit in results[0]
        if hit.distance >= SIMILARITY_THRESHOLD[collection_name]
        ]

    if hit_data:
        logger.info(f"🕵🏻 Resultados de la búsqueda en la colección: '{collection_name}'")
        for i, hit in enumerate(hit_data):        
            print(f"\t🔹 {i+1} - Distancia: {float(hit['score']):.2f} | Pregunta: {hit['question'][:80]}")
    else:
        return []
    
    return hit_data


def get_context_by_type(question: str, top_k: int = 3) -> dict:    
    embedding = generate_embedding(question)

    context = {"sql": [], "ddl": [], "docs": []}    
    context["sql"] = search_collection(COLLECTIONS_NAME["questions"], embedding, ["question", "sql"], top_k)    
    context["docs"] = search_collection(COLLECTIONS_NAME["docs"], embedding, ["question", "texto"], top_k)
    
    return context
