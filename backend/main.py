# backend/main.py

from pymilvus import connections, Collection
import sys
import os
import requests
from fastapi import FastAPI,  HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import JSONResponse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.sql_agent import handle_user_question
from agent.rag_agent import generate_embedding, save_collection
from shared.utils import init_config, generate_request_id, log_to_file, log_event, load_config
from core.query_validator import validate_sql_query
from core.query_executor import execute_sql
from core.init_collections import init_milvus_collections
from core.exceptions import (
    InvalidCollectionTypeError,
    EmbeddingServiceError,
    SQLExecutionError,
    SQLValidationError
)

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

@app.post("/execute_sql")
async def try_execute_sql(payload: SQLExecute):
    try:
        is_valid, _, msg = validate_sql_query(payload.sql)
        if not is_valid:
            raise SQLValidationError(msg)
        
        result, duration = execute_sql(payload.sql, domain="tickets")
        
        if "error" in result:
            raise SQLExecutionError(result["error"])
                
        return {
            "success": True,
            "result": result,
            "duration": duration,
            "message": msg
        }

    except SQLValidationError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "message": "Error de validación en la consulta SQL"
            }
        )
    
    except SQLExecutionError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Fallo en la ejecución de la consulta SQL"
            }
    )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Ocurrió un error inesperado durante la ejecución"
            }
        )    
    


@app.post("/training")
async def training(payload: TrainingInput):
        try:
            embedding = generate_embedding(payload.question)
            collections = CONFIG_JSON["milvus_endpoint"]["collections"]

            match payload.type:
                case "sql":
                    collection_name = collections["questions"]
                case "ddl":
                    collection_name = collections["ddl"]
                case "docs":
                    collection_name = collections["docs"]
                case _:
                    raise HTTPException(status_code=400, detail="Tipo de colección no válido")
    
            fields = [[payload.question], [payload.content], [embedding]]
            result = save_collection(collection_name=collection_name, fields=fields)
            return result
        
        except EmbeddingServiceError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except InvalidCollectionTypeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")
