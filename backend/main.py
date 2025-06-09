# backend/agent/main.py

from pymilvus import connections, Collection
import sys
import os
import requests
from fastapi import FastAPI,  HTTPException, Request, UploadFile, File
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.sql_agent import handle_user_question
from agent.rag_agent import generate_embedding
from shared.utils import init_config, generate_request_id, log_to_file, log_event, load_config
from core.query_validator import validate_sql_query
from core.query_executor import execute_sql
from core.init_collections import init_milvus_collections

init_config()

CONFIG_JSON = load_config()
MILVUS_ENDPOINT = CONFIG_JSON["milvus_endpoint"]
MILVUS_HOST = MILVUS_ENDPOINT["host"]
MILVUS_PORT = MILVUS_ENDPOINT["port"]
EMBEDDING_ENDPOINT = CONFIG_JSON["embedding_endpoint"]
COLLECTIONS_NAME = MILVUS_ENDPOINT["collections"]

init_milvus_collections(MILVUS_HOST, MILVUS_PORT, False)

app = FastAPI(
    title="SQL AI Agent Multi-Model",
    description="Agente que genera consultas SQL a partir de preguntas en lenguaje natural usando modelos multi-inferencia.",
    version="1.0.0"
)

class SQLRequest(BaseModel):
    question: str
    domain: str

class TrainingInput(BaseModel):
    question: str
    type: str 
    content: str

class SQLExecute(BaseModel):
    sql: str

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Agente SQL IA funcionando correctamente"}

@app.post("/generate_sql")
async def generate_sql(request: SQLRequest, http_request: Request):

    client_ip = http_request.client.host
    request_id = generate_request_id()

    try:
        log_to_file(f"API Request {request_id} desde {client_ip} | Pregunta: {request.question} | Dominio: {request.domain}", api=True)

        sql, result_exec, flow, reformulation, total_time_ia, return_type, rag_context = handle_user_question(
            request.question, 
            domain=request.domain
            )
                
        log_event(
            request_id=request_id,
            client_ip=client_ip,
            user_question=request.question,
            reformulation=reformulation,
            flow=flow,
            generated_sql=sql,
            result=result_exec,
            type_result=return_type,
            model="mistral & gemma",
            domain=request.domain,
            duration=total_time_ia
        )

        return {
            "sql": sql,
            "flow": flow,
            "reformulation": reformulation,
            "client_ip": client_ip,
            "domain": request.domain,
            "request_id": request_id,
            "duration_agent": total_time_ia,
            "result": result_exec,
            "rag_context": rag_context
        }
  
    except Exception as e:
        log_event(
            request_id=request_id,
            client_ip=client_ip,
            user_question=request.question,
            reformulation="",
            flow="",
            generated_sql="",
            result={"error": str(e)},
            type_result="fails",
            model="mistral & gemma",
            domain=request.domain,
            duration=0
        )        
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import JSONResponse

@app.post("/execute_sql")
async def try_execute_sql(payload: SQLExecute):
    try:
        is_valid, _, msg = validate_sql_query(payload.sql)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": "SQL inválido", "details": msg}
            )
        
        result, duration = execute_sql(payload.sql, domain="tickets")
        if "error" in result:
            return {
                "success": False,
                "result": result,
                "duration": duration,
                "message": msg
            }
                
        return {
            "success": True,
            "result": result,
            "duration": duration,
            "message": msg
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Ocurrió un error durante la ejecución"
            }
        )


@app.post("/train")
async def train(payload: TrainingInput):
    try:

        # Generador de embeddings
        embedding = generate_embedding(payload.question)        
        print(f"🔎 Embedding Training (primeras 5 dimensiones): {embedding[:5]}")

        # Conectar a Milvus
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
        collections = CONFIG_JSON["milvus_endpoint"]["collections"]

        if payload.type == "sql":
            collection = Collection(collections["questions"])
            fields = [[payload.question], [payload.content], [embedding]]
        elif payload.type == "ddl":
            collection = Collection(collections["ddl"])
            fields = [[payload.question], [payload.content], [embedding]]
        elif payload.type == "docs":
            collection = Collection(collections["docs"])
            fields = [[payload.question], [payload.content], [embedding]]
        else:
            raise HTTPException(status_code=400, detail="Tipo inválido. Usa 'sql', 'ddl' o 'docs'.")

        collection.load()
        collection.insert(fields)
        collection.flush()

        return {"status": "ok", "message": "Ejemplo entrenado correctamente."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
