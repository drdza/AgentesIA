import sys
import os
import json
import logging
from datetime import datetime
from shared.utils import load_prompt_template, log_event
from core.llm import call_model
from core.query_validator import validate_sql, preprocess_sql, safe_extract_sql
from core.query_executor import execute_sql
from core.exceptions import ReformulationError, RagContextError, FlowGenerationError, SQLAgentPipelineError
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

    Returns:
        tuple: SQL generado, resultado de ejecución, flujo técnico, reformulación, tiempo total, tipo de respuesta, contexto RAG.
    """
    
    total_time = 0
    flow_text = ''
    resutl = {}
    return_type = "fail"

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
    try:
        formatted_sql_prompt = sql_prompt_template.format(
            question=question.strip(),
            flow=flow_text.strip(),
            context=rag_context.strip(),
        )
        
        logger.info("💡 Generando SQL con IA...")
        raw_sql, duration, _ = call_model("mistral", formatted_sql_prompt)
        total_time += duration
        logger.info(f"💡 SQL generado ( {duration:.2f} seg. )")

        safe_sql = safe_extract_sql(raw_sql)
        formatted_sql = preprocess_sql(safe_sql) 
        validate_sql(formatted_sql)
        
        logger.info("⚡ Ejecutando SQL...")
        result, duration = execute_sql(formatted_sql, domain=domain)     
        total_time += duration
        return_type = "success" if "error" not in result  else "fail"        
        logger.info(f"⚡ SQL ejecutado ( {duration:.2f} seg. )")

    except Exception as e:
        raise SQLAgentPipelineError(f"Fallo al generar SQL: {str(e)}")

    logger.info(f"🧠 Tiempo total IA: {total_time:.2f} seg.")    
    return formatted_sql, result, flow_text, enhanced_question, total_time, return_type, rag_context
