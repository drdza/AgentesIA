import sys
import os
import json
import re
import logging
from datetime import datetime
from shared.utils import load_prompt_template
from core.llm import call_model
from core.query_validator import validate_sql, preprocess_sql, safe_extract_sql
from core.query_executor import execute_sql
from core.exceptions import ReformulationError, RagContextError, FlowGenerationError, PromptTemplateLoadError, InferenceServiceError
from agent.rag_agent import get_context_by_type


logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)

# Evita agregar múltiples handlers si se llama varias veces
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

KEYWORDS_DOMINIO = [
    "ranking", "top", "agrupación", "tickets", "atendidos", "abiertos", 
    "en proceso", "fuera de tiempo", "departamento", "área", "mes", "semana",
    "año", "sla", "colaborador", "servicio", "análisis", "tiempo atención",
    "fecha cierre"
]
    

def clean_enhanced_question(response: str, user_question: str) -> dict:
    user_question = user_question.lower()
    enhanced_dict = {}    
    try:     
        clean_response = re.sub(r"```(?:json)?\s*([\s\S]+?)\s*```", r"\1", response.strip())        
        enhanced_dict = json.loads(clean_response)

    except Exception:
        enhanced_dict['reformulacion'] = user_question
        enhanced_dict['tags'] = [palabra for palabra in KEYWORDS_DOMINIO if palabra in user_question]

    return enhanced_dict

def join_rag_context(rag_context: dict):

    if not rag_context:
        return rag_context
        
    rag_parts = []

    if rag_context["sql"]:
        rag_parts.append("### - Contexto - ✅ SQL previamente validado como referencia estructural (útil para formato, estilo y lógica similar):\n\n" + "\n".join(
            [f"• {item['question']} - ({item['score']:.2f})\n```sql\n{item['sql']}\n```" for item in rag_context["sql"]]
        ))

    if rag_context["docs"]:
        rag_parts.append("\n\n### - Contexto - 📚 Documentación relacionada (útil para interpretar conceptos o reglas de negocio):\n\n" + "\n".join(
            [f"{item['texto']} - ({item['score']:.2f})\n" for item in rag_context["docs"]]
        ))

    return "".join(rag_parts)


def handle_user_question(question: str, domain: str):
    """
    Agente SQL generalizado para múltiples dominios (ej. tickets, ventas, inventario).

    Returns:
        tuple: SQL generado, resultado de ejecución, flujo técnico, reformulación, tiempo total, tipo de respuesta, contexto RAG.
    """
    
    total_time = 0
    flow_text = ''
    result = {}    

    # Cargar prompt adecuado al dominio
    try:
        sql_prompt_template = load_prompt_template(domain, "system_context_rag.txt")

    except FileNotFoundError:
        logger.error(f"[Carga de Prompt]. No se encontró prompt para el dominio `{domain}`")
        raise PromptTemplateLoadError(f"[Carga de Prompt]. No se encontró prompt para el dominio `{domain}`")

    # Paso 1: Reformulación (opcionalmente usar otro modelo por dominio)    
    try:
        logger.info("💭 Generando reformulación...")
        enhancer_prompt = load_prompt_template(domain, "question_enhancer.txt")
        response, duration, _ = call_model("mistral", enhancer_prompt, question)
        
        enhanced_dict = clean_enhanced_question(response=response, user_question=question)
        enhanced_question = enhanced_dict['reformulacion'].strip()
        enhanced_question_tag = enhanced_dict['tags']
        
        total_time += duration
        logger.info(f"💭 Reformulación completa ( {duration:.2f} seg. )")

    except Exception as e:
        logger.error(f"[Reformulación]. {str(e)}")
        raise ReformulationError (f"[Reformulación]. {str(e)}")
    
    # Paso 2: Búsqueda de contexto relacionada a la pregunta reformulada del usuario
    try:
        logger.info("📚 Buscando contexto en Milvus...")
        rag_data = get_context_by_type(enhanced_question, top_k=3)

    except Exception as e:                
        logger.error(f"[Recuperación de contexto]. {str(e)}")
        raise RagContextError(f"[Recuperación de contexto]. {str(e)}")

    if not rag_data['sql'] and not rag_data['docs']:        
        logger.warning("⚠️  No se encontró contexto útil, se incluirá un flujo técnico.")    

        try:
            logger.info("🔀 Generando flujo técnico...")
            flow_prompt_template = load_prompt_template(domain, "flow_generator_rag.txt")            
            flow_text, duration, _ = call_model("mistral", flow_prompt_template, enhanced_question)

            flow_text = f"#### 🔀 Flujo Técnico a seguir para resolver la pregunta y generar el SQL válido para PostgreSQL:\n\n{flow_text}"
            total_time += duration

            logger.info(f"🔀 Flujo técnico completo ( {duration:.2f} seg. )")
        
        except FileNotFoundError as file_err:
            logger.warning(f"[Carga de Prompt]. {str(file_err)}")
            raise PromptTemplateLoadError(f"[Carga de Prompt]. {str(file_err)}")
        
        except Exception as e:
            logger.error(f"[Generación de Flujo Técnico]. {str(e)}")
            raise FlowGenerationError(f"[Generación de Flujo Técnico]. {str(e)}")
    
    logger.info("📝 Generando prompt para SQL...")
    rag_context = join_rag_context(rag_data)

    try:
        formatted_sql_prompt = sql_prompt_template.format(            
            flow=flow_text.strip(),
            context=rag_context.strip()        
        )

        logger.info("💡 Generando SQL con IA...")
        raw_sql, duration, _ = call_model("mistral", formatted_sql_prompt, enhanced_question)
        total_time += duration        
        logger.info(f"💡 SQL generado ( {duration:.2f} seg. )") 
    
    except Exception as e:
        raise InferenceServiceError(f"[Generación de SQL]. {str(e)}")

    try:
        logger.info("⚡ Validando SQL...")
        safe_sql = safe_extract_sql(raw_sql)

        formatted_sql = safe_sql  # fallback seguro por si el siguiente paso falla

        formatted_sql = preprocess_sql(formatted_sql)
        validate_sql(formatted_sql)

        logger.info("⚡ Ejecutando SQL...")
        result, duration = execute_sql(formatted_sql, domain=domain)

        total_time += duration
        logger.info(f"⚡ SQL ejecutado ( {duration:.2f} seg. )")

    except Exception as e:
        logger.error(f"🛑 {str(e)}")
        result['error'] = str(e)

    logger.info(f"🧠 Tiempo total IA: {total_time:.2f} seg.")    
    return formatted_sql, result, flow_text, enhanced_question, total_time, rag_context
