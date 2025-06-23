import sys
import os
import logging
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from shared.utils import load_config
from core.exceptions import CollectionInitError


logger = logging.getLogger("init_collections")
logger.setLevel(logging.INFO)

CONFIG_JSON = load_config()
MILVUS_ENDPOINT = CONFIG_JSON["milvus_endpoint"]
COLLECTIONS_NAME = MILVUS_ENDPOINT["collections"]

if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def drop_milvus_collections():
    """
    Elimina las colecciones si existen.
    """    

    for collection in COLLECTIONS_NAME.values():
        try:
            if utility.has_collection(collection):                
                utility.drop_collection(collection)
                logger.info(f"🗑️  Colección eliminada: {collection}")
            else:
                logger.warning(f"⚠️  No existe la colección '{collection}' para eliminar.")
        except Exception as e:
            raise CollectionInitError(f"Error al eliminar la colección '{collection}': {str(e)}") from e


def init_milvus_collections(host, port, refresh=False):
    """
    Inicializa las colecciones necesarias para el agente SQL.
    Si refresh=True, elimina las existentes y las crea desde cero.
    """
    try: 
        connections.connect(alias="default", host=host, port=port) 
    except Exception as e:
        raise CollectionInitError(f"No se pudo conectar a Milvus en {host}:{port}") from e
    
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
        try:
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
        except Exception as e:
            raise CollectionInitError(f"Fallo al crear o indexar la colección '{name}': {str(e)}") from e
