
import os
import sys
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.rag_agent import generate_embedding
from shared.utils import load_config

CONFIG_JSON = load_config()
MILVUS_ENDPOINT = CONFIG_JSON["milvus_endpoint"]
MILVUS_HOST = MILVUS_ENDPOINT["host"]
MILVUS_PORT = MILVUS_ENDPOINT["port"]
COLLECTIONS_NAME = MILVUS_ENDPOINT["collections"]
collection_name = 'sql_agent_questions'
fields = ["question", "sql"]
distance = 0.75

def conectar_vectorstore(collection_name: str):
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

    collection = Collection(name=collection_name)
    collection.load()

    return collection

def eliminar():    
    id = input("ID a eliminar: ")
    resp = input(f"Eliminaremos el ID `{id}` de la colección `{collection_name}`.\n¿Es correcto? (y/n): ")
    if resp == 'y' or resp == 'yes':
        try:
            collection.delete(f"id in [{id}]")
            print(f"Se ha eliminado el registro con ID `{id}` de la colección `{collection_name}`.")
        except Exception as e:
            print(f"Error: {e}")

def buscar(distance: float, output_fields: list= fields):
    from rich import print
    text = f"""
    ¿Qué deseas buscar en ({collection_name})?: """
    question_text = input(text)
    embedding = generate_embedding(question_text)
    
    results = collection.search(
        data=[embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=10,
        output_fields=output_fields
    )
    
    #print(results)

    hit_data = [
        {**hit.to_dict()['entity'], "score": hit.distance, "id": hit.id} 
        for hit in results[0]
        if round(hit.distance,2) >= distance
        ]
        
    print(f"📌 Resultados ({len(hit_data)} registros)")
    for i, hit in enumerate(hit_data):        
        print(f"🔹 {i+1} - ID: {hit['id']}\nDistancia: {round(hit['score'], 2)}\nPregunta: {hit[fields[0]].strip()}\nContenido:\n{hit[fields[1]]}")


def consultar(output_fields: list= fields):
    from rich import print
    num_entities = collection.num_entities
    
    results = collection.query(
        expr="",  # Expresión vacía para obtener todo
        output_fields=output_fields,  # Todos los campos
        limit=num_entities  # Límite igual al número total
    )
    print(f"📌 Resultados ({len(results)} registros)")
    for doc in results:
        print(doc)  # Aquí tendrías el contenido de cada documento

is_live = True
while is_live:
    menu = f"""
    Opciones
    =============================        
    1   - Preguntar
    2   - Eliminar
    3   - Cambiar Colección
    4   - Consultar Todo
    0   - Salir
    Se está consultado la colección `{collection_name}` con un umbral de almenos {distance} unidades
    
    Selecciona una opción: """
    option = input(menu)
    match option:
        case "0":
            is_live = False
        case "1":
            collection = conectar_vectorstore(collection_name=collection_name)
            buscar(distance=distance, output_fields=fields)
        case "2":
            collection = conectar_vectorstore(collection_name=collection_name)
            eliminar()
        case "4":
            collection = conectar_vectorstore(collection_name=collection_name)
            consultar(output_fields=fields)
        case "3":
            info_collection = """
    ¿Qué colección desea consultar?
    ===============================
    1 - sql_agent_questions
    2 - sql_ddl
    3 - sql_docs

    Elija una opción: """
            option_collection = input(info_collection)
            match option_collection:
                case "1":
                    collection_name = 'sql_agent_questions'
                    distance = 0.75
                    fields = ["question", "sql"]
                case "2":
                    collection_name = 'sql_ddl'
                    distance = 0.1
                    fields = ["question", "ddl"]
                case "3":
                    collection_name = 'sql_docs'
                    distance = 0.65
                    fields = ["question", "texto"]

    
            





