from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional
import asyncio
import logging
import json
import time

from shared.utils import load_prompt_template
from core.llm import call_model
from core.query_validator import validate_sql, preprocess_sql, safe_extract_sql
from core.query_executor import execute_sql
from agent.rag_agent import get_context_by_type
from agent.sql_agent import clean_enhanced_question, join_rag_context, clean_text
from core.exceptions import ReformulationError, RagContextError, FlowGenerationError, InferenceServiceError, ContextVerificationError

logger = logging.getLogger("llm")
logger.setLevel(logging.INFO)

# --- 1. Definición del estado compartido en el grafo
class AgentState(TypedDict):
    question: str
    domain: str
    previous_question: Optional[str]
    enhanced_question: Optional[str]
    enhanced_question_llm: Optional[str]
    enhanced_tags: Optional[list[str]]
    flow: Optional[str]
    rag_context: Optional[str]
    sql: Optional[str]
    result: Optional[dict]
    total_time: float
    dominio_valido: Optional[bool]
    contexto_dominio: Optional[str]
    execution_ok: Optional[bool]
    execution_error: Optional[str]
    repair_attempted: Optional[bool]




# --- 2. Nodos ---
async def fallback_node(state: AgentState):
    rejection = {
        "mensaje": "¡Ups! Parece que tu pregunta está fuera de mi alcance. ¿Podrías darme más detalles o reformularla?.",    
        "motivo": state.get('contexto_dominio', 'Fuera de dominio')
        }
    logger.warning(f"Pregunta rechazada: {state['question']}  Motivo: {rejection}")
    return {**state, "result": {"out_domain": rejection}}


def route_after_verificator(state: AgentState) -> str:    
    return "enhance" if state.get("dominio_valido") else "fallback"



async def verify_context_node(state: AgentState):
    try:
        prompt = await asyncio.to_thread(load_prompt_template, state["domain"], "verificator_context.txt")
        resp_json, duration, _ = await asyncio.to_thread(call_model, "llama3", prompt, state["question"])        

        data = json.loads(resp_json)
        return {
            **state,
            "dominio_valido": bool(data.get("dominio_valido", False)),
            "contexto_dominio": data.get("explicacion", ""),
            "total_time": state["total_time"] + duration,
        }

    except Exception as e:
        # ← NUNCA levantes aquí. Marca como fuera de dominio y registra el motivo
        return {
            **state,
            "dominio_valido": False,
            "contexto_dominio": f"Error verificador: {e}",
            "total_time": state["total_time"],
        }


async def enhance_question_node(state: AgentState):
    try:
        enhancer_prompt = await asyncio.to_thread(load_prompt_template, state['domain'], "question_enhancer.txt")
        user_prompt = state['question']
        enhancer_question, duration, _ = await asyncio.to_thread(call_model, "llama3", enhancer_prompt, user_prompt)
        enhanced_dict = clean_enhanced_question(enhancer_question, state['question'])
        
        # logger.info(f"User Prompt: {user_prompt}")
        # logger.info(f"Enhanced question: {enhanced_dict}")
        
        return {
            **state,
            "enhanced_question_llm": enhanced_dict["reformulacion"].strip(),
            "enhanced_question": clean_text(enhanced_dict["reformulacion"].strip()),
            "enhanced_tags": enhanced_dict["tags"],
            "total_time": state["total_time"] + duration
        }
    except Exception as e:
        raise ReformulationError(str(e))

async def get_context_node(state: AgentState):    
    try:
        rag_data = await asyncio.to_thread(get_context_by_type, state["enhanced_question"], top_k=3)
        rag_context = join_rag_context(rag_data)          
        return {**state, "rag_context": rag_context, "rag_raw": rag_data}
    except Exception as e:
        raise RagContextError(str(e))

async def generate_flow_or_context_node(state: AgentState):
    # if state["rag_context"]:
    #     return state  # No requiere flujo técnico

    try:
        flow_prompt = await asyncio.to_thread(load_prompt_template, state['domain'], "flow_generator.txt")
        flow_text, duration, _ = await asyncio.to_thread(call_model, "llama3", flow_prompt, state['enhanced_question'])
        flow = f"### 🔀 Flujo Técnico:\n\n{flow_text.strip()}"
        return {**state, "flow": flow, "total_time": state["total_time"] + duration}
    except Exception as e:
        raise FlowGenerationError(str(e))

async def generate_sql_node(state: AgentState):
    try:
        sql_prompt_template = await asyncio.to_thread(load_prompt_template,state['domain'], "system_context.txt")
        prompt = sql_prompt_template.format(
            flow=state.get("flow", ""),
            context=state.get("rag_context", "")
        )
        raw_sql, duration, _ = await asyncio.to_thread(call_model, "llama3", prompt, state['enhanced_question'])
        return {**state, 
                "sql": raw_sql, 
                "total_time": state["total_time"] + duration
                }
    except Exception as e:
        raise InferenceServiceError(str(e))

def extract_sql_node(state: AgentState):
    try:
        start_time = time.time()            
        
        safe_sql = safe_extract_sql(state["sql"])        
        formatted_sql = preprocess_sql(safe_sql)        
        validate_sql(formatted_sql)

        duration = round(time.time() - start_time, 2)
        return {**state, 
                "sql": formatted_sql, 
                "total_time": state["total_time"] + duration
            }
    except Exception as e:
        logger.error(f"Falló la extracción del SQL: {str(e)}")
        
def execute_sql_node(state: AgentState):
    try:
        formatted_sql = state['sql']        
        result, duration = execute_sql(formatted_sql, domain=state['domain'])
        return {**state,            
            "result": result,
            "execution_ok": True,
            "total_time": state["total_time"] + duration
        }
    
    except Exception as e:
        logger.error(str(e))
        return {**state,
            "result": {"error": str(e)},
            "execution_ok": False,
            "execution_error": str(e),
            "total_time": state["total_time"]
        }

def route_after_execute(state: AgentState) -> str:    
    if state.get("execution_ok"):
        return END

    if not state.get("repair_attempted"):
        return "repair_sql"

    return END


async def repair_sql_node(state: AgentState):
    """
    Intenta corregir la consulta fallida usando el error devuelto por Postgres.
    Solo se ejecuta si execute_sql_node dejó un error en state['execution_error'].
    """
    try:
        # ── Carga el prompt template (.txt) ───────────────────
        prompt_template = await asyncio.to_thread(load_prompt_template, state["domain"], "repair_sql.txt")

        formatted_prompt = prompt_template.format(
            sql=state.get("sql", ""),
            execution_error=state.get("execution_error", ""),
            question=state.get("enhanced_question_llm", "")            
        )
                
        fixed_sql, duration, _ = await asyncio.to_thread(call_model, "llama3", formatted_prompt, "Corrige la siguiente consulta fallida, por favor.")        

        return {
            **state,
            "sql": fixed_sql.strip(),
            "repair_attempted": True,
            "total_time": state["total_time"] + duration
        }

    except Exception as e:
        # Falla la reparación → dejar constancia y saltar a fallback_sql
        return {
            **state,
            "repair_attempted": True            
        }


# --- 3. Definición del grafo LangGraph ---
def build_sql_agent_graph():
    
    builder = StateGraph(AgentState)  
    builder.add_node("verificator", verify_context_node)  
    builder.add_node("enhance", enhance_question_node)
    builder.add_node("rag", get_context_node)
    builder.add_node("generate_flow", generate_flow_or_context_node)
    builder.add_node("generate_sql", generate_sql_node)
    builder.add_node("extract_sql", extract_sql_node)
    builder.add_node("execute", execute_sql_node)
    builder.add_node("fallback", fallback_node)
    builder.add_node("repair_sql", repair_sql_node)

    builder.set_entry_point("verificator")

    # ***Bifurcación condicional ***
    builder.add_conditional_edges( 
        "verificator",
        route_after_verificator,
        {
            "enhance": "enhance",
            "fallback": "fallback",
        },
    )

    # resto del flujo “válido”
    builder.add_edge("enhance", "rag")
    builder.add_edge("rag", "generate_flow")
    builder.add_edge("generate_flow", "generate_sql")
    builder.add_edge("generate_sql", "extract_sql")
    builder.add_edge("extract_sql", "execute")
    
    builder.add_conditional_edges(
        "execute", 
        route_after_execute,
        {
            "repair_sql": "repair_sql",            
            END: END
        },
    )

    builder.add_edge("repair_sql", "extract_sql")    
    builder.add_edge("fallback", END)

    return builder.compile()

# --- 4. Wrapper para invocar el grafo ---
async def run_sql_graph(question: str, domain: str, previous_question: str = None) -> AgentState:    
    return await graph.ainvoke({"question": question, "domain": domain, "total_time": 0.0, "previous_question": previous_question})

# --- 5. Ejecución del agente en LangGraph
graph = build_sql_agent_graph()