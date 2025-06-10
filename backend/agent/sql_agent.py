import sys
import os
import json
import logging
from datetime import datetime
from shared.utils import load_prompt_template, safe_extract_sql, log_event
from core.llm import call_model
from core.query_validator import validate_sql_query
from core.query_executor import execute_sql
from core.exceptions import ReformulationError, RagContextError, SQLAgentPipelineError, FlowGenerationError
from agent.rag_agent import get_context_by_type 


logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)

# Evita agregar múltiples handlers si se llama varias veces
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def handle_user_question(question: str, domain: str):
    """
    Agente SQL generalizado para múltiples dominios (ej. tickets, ventas, inventario).

    Args:
        question (str): Pregunta del usuario en lenguaje natural.
        domain (str): Dominio de datos. Define el contexto y prompt.

    Returns:
        tuple: SQL generado, modelo usado, resultado de ejecución
    """
    total_time = 0
    flow_text = ''
    # Cargar prompt adecuado al dominio
    try:
        sql_prompt_template = load_prompt_template(domain, "system_context_rag.txt")
    except FileNotFoundError:
        raise ValueError(f"❌ No se encontró prompt para el dominio: {domain}")

    # Paso 1: Reformulación (opcionalmente usar otro modelo por dominio)
    try:
        logger.info("💭 Generando reformulación")
        enhancer_prompt = load_prompt_template(domain, "question_enhancer.txt")
        formatted_enhancer_prompt = enhancer_prompt.format(question=question.strip())
        enhanced_question, duration, _ = call_model("gemma", formatted_enhancer_prompt)
        total_time += duration
        logger.info(f"💭 Reformulación completa ( {duration:.2f} seg. )")
    except Exception as e:
        logger.error(f"❌ Error al reformular la pregunta. Detalle: {str(e)}")
        raise ReformulationError (f"Error al reformular la pregunta: {str(e)}")
    
    # Paso 2: Búsqueda de contexto relacionada a la pregunta reformulada del usuario
    try:
        logger.info("📚 Buscando contexto en Milvus...")
        rag_data = get_context_by_type(enhanced_question, top_k=3)        
    except Exception as e:        
        rag_data = {"sql": [], "ddl": [], "docs": []}
        logger.error(f"⚠️ Fallo en búsqueda en Milvus: {str(e)}")
        raise RagContextError(f"Fallo al recuperar contexto: {str(e)}")

    if not rag_data['sql']:        
        logger.warning("⚠️ No se encontró contexto útil, se incluirá un flujo técnico.")          
        try:
            logger.info("🔀 Generando flujo técnico...")
            flow_prompt_template = load_prompt_template(domain, "flow_generator_rag.txt")
            formatted_flow_prompt = flow_prompt_template.format(question=enhanced_question.strip())
            flow_text, duration, _ = call_model("mistral", formatted_flow_prompt)
            total_time += duration
            logger.info(f"🔀 Flujo técnico completo ( {duration:.2f} seg. )")
        except FileNotFoundError:
            logger.warning("🔀 No se encontró prompt para flujo técnico.")
        except Exception as e:
            raise FlowGenerationError(f"Fallo al generar flujo técnico: {str(e)}")
    
    logger.info("📝 Generando prompt para SQL")
    rag_parts = []    
    if rag_data["sql"]:
        rag_parts.append("### ✅ SQL previamente validado como respuesta a preguntas similares:\n\n" + "\n".join(
            [f"• {item['question']}\n```sql\n{item['sql']}\n```" for item in rag_data["sql"]]
        ))

    if rag_data["docs"]:
        rag_parts.append("\n\n### 📚 Documentación útil o explicaciones relacionadas:\n\n" + "\n".join(
            [f"{item['texto']}\n" for item in rag_data["docs"]]
        ))
   
    rag_context = "".join(rag_parts)
    logger.info(f"RAG CONTEXT:\n{rag_context}")

    formatted_sql_prompt = sql_prompt_template.format(
        question=question.strip(),
        flow=flow_text.strip(),
        context=rag_context.strip(),
    )
    
    try:
        logger.info("💡 Generando SQL con IA...")
        raw_sql, duration, _ = call_model("mistral", formatted_sql_prompt)
        total_time += duration
        logger.info(f"💡 SQL generado ( {duration:.2f} seg. )")

        cleaned_sql = safe_extract_sql(raw_sql)    
        is_valid, sql, msg = validate_sql_query(cleaned_sql)
        if is_valid:        
            # Paso 4: Ejecutar
            logger.info("⚡ Ejecutando SQL...")
            result, duration = execute_sql(sql, domain=domain)     
            return_type = "success" if "error" not in result  else "fails"
            total_time += duration
            logger.info(f"⚡ SQL ejecutado ( {duration:.2f} seg. )")
        else:
            logger.error(f"⚡ SQL inválido: {msg}")
    except Exception as e:
        raise SQLAgentPipelineError(f"Fallo al generar SQL: {str(e)}")

    logger.info(f"🧠 Tiempo total IA: {total_time:.2f} seg.")    
    return sql, result, flow_text, enhanced_question, total_time, return_type, rag_context


# Nuevo: funciones separadas por etapa
def generate_reformulation(question: str, domain: str):
    enhancer_prompt = load_prompt_template(domain, "question_enhancer.txt")
    prompt = enhancer_prompt.format(question=question.strip())
    return call_model("gemma", prompt)

def generate_flow(enhanced_question: str, domain: str):
    try:
        flow_prompt = load_prompt_template(domain, "flow_generator_prompt.txt")
        prompt = flow_prompt.format(question=enhanced_question.strip())
        return call_model("mistral", prompt)
    except FileNotFoundError:
        return "", 0, {}

def generate_sql(question: str, flow: str, domain: str):
    sql_prompt = load_prompt_template(domain, "system_context.txt")
    prompt = sql_prompt.format(question=question.strip(), flujo=flow.strip())
    return call_model("mistral", prompt)

def run_sql_validation_and_execute(raw_sql: str, domain: str):
    cleaned_sql = safe_extract_sql(raw_sql)
    is_valid, final_sql = validate_sql_query(cleaned_sql)
    if not is_valid:
        raise ValueError("❌ El SQL generado no pasó la validación sintáctica.")
    result = execute_sql(final_sql, domain)
    return final_sql, result

def handle_user_question_stream(question: str, domain: str, request_id: str, client_ip: str):
    total_time = 0
    model_used = "gemma + mistral"

    # Acumuladores para logging
    enhanced, flow, sql_cleaned, result, error_msg = "", "", "", {}, ""
    start_time = datetime.now()

    try:
        yield json.dumps({"stage": "start", "message": "Reformulando pregunta..."})
        enhanced, duration, _ = generate_reformulation(question, domain)
        total_time += duration
        yield json.dumps({"stage": "reformulation", "content": enhanced})

        yield json.dumps({"stage": "message", "message": "Generando flujo técnico..."})
        flow, duration, _ = generate_flow(enhanced, domain)
        total_time += duration
        yield json.dumps({"stage": "flow", "content": flow})

        yield json.dumps({"stage": "message", "message": "Generando SQL..."})
        raw_sql, duration, _ = generate_sql(question, flow, domain)
        total_time += duration
        sql_cleaned = safe_extract_sql(raw_sql)
        yield json.dumps({"stage": "sql", "content": sql_cleaned})

        yield json.dumps({"stage": "message", "message": "Ejecutando consulta..."})
        final_sql, result = run_sql_validation_and_execute(raw_sql, domain)
        yield json.dumps({"stage": "result", "content": result})
        log_event(
            request_id=request_id,
            client_ip=client_ip,
            user_question=question,
            reformulation=enhanced,
            flow=flow,
            generated_sql=sql_cleaned,
            result=result,
            success=True,
            model=model_used,
            domain=domain,
            duration=total_time
        )
        yield json.dumps({"stage": "done", "total_time": total_time})

    except Exception as e:
        error_msg = str(e)
        log_event(
            request_id=request_id,
            client_ip=client_ip,
            user_question=question,
            reformulation=enhanced,
            flow=flow,
            generated_sql=sql_cleaned,
            result={"error": error_msg},
            success=False,
            model=model_used,
            domain=domain,
            duration=(datetime.now() - start_time).total_seconds()
        )

        yield json.dumps({"stage": "error", "message": error_msg})

