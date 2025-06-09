import sys
import os
import logging
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

logger = logging.getLogger("init_collections")
logger.setLevel(logging.INFO)

# Evita agregar múltiples handlers si se llama varias veces
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def drop_milvus_collections():    
    utility.drop_collection("sql_agent_questions")
    utility.drop_collection("sql_ddl")
    utility.drop_collection("sql_docs")


def init_milvus_collections(host, port, refresh=False):
    connections.connect(alias="default", host=host, port=port) 

    if refresh:
        drop_milvus_collections()        

    collections = {
        "sql_agent_questions": [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="sql", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024)            
        ],
        "sql_ddl": [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="ddl", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),        
        ],
        "sql_docs": [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="texto", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),        
        ]
    }

    for name, fields in collections.items():
        if utility.has_collection(name):
            logger.warning(f"⚠️  La colección '{name}' ya existe.")
            continue

        schema = CollectionSchema(fields=fields, description=f"Colección: {name}")
        collection = Collection(name=name, schema=schema)
        collection.create_index("embedding", {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        })
        logger.info(f"✅ Colección creada: {name}")