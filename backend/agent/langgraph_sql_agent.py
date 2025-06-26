from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional
import logging
import time

# Importar funciones necesarias desde tu backend
from shared.utils import load_prompt_template
from core.llm import call_model
from core.query_validator import validate_sql, preprocess_sql, safe_extract_sql
from core.query_executor import execute_sql
from core.exceptions import ReformulationError, RagContextError, FlowGenerationError, SQLAgentPipelineError, PromptTemplateLoadError, InferenceServiceError
from agent.rag_agent import get_context_by_type
from agent.sql_agent import clean_enhanced_question, join_rag_context


logger = logging.getLogger(__name__)

# --- 1. Definición del estado compartido en el grafo
class AgentState(TypedDict):
    question: str
    domain: str
    enhanced_question: Optional[str]
    enhanced_tags: Optional[list[str]]
    flow: Optional[str]
    rag_context: Optional[str]
    sql: Optional[str]
    result: Optional[dict]
    total_time: float


# --- 2. Nodos ---
def enhance_question_node(state: AgentState):
    try:
        enhancer_prompt = load_prompt_template(state['domain'], "question_enhancer.txt")
        response, duration, _ = call_model("mistral", enhancer_prompt, state['question'])

        enhanced_dict = clean_enhanced_question(response, state['question'])
        return {
            **state,
            "enhanced_question": enhanced_dict["reformulacion"].strip(),
            "enhanced_tags": enhanced_dict["tags"],
            "total_time": state["total_time"] + duration
        }
    except Exception as e:
        raise ReformulationError(str(e))

def get_context_node(state: AgentState):
    try:
        rag_data = get_context_by_type(state["enhanced_question"], top_k=3)
        rag_context = join_rag_context(rag_data)
        return {**state, "rag_context": rag_context, "rag_raw": rag_data}
    except Exception as e:
        raise RagContextError(str(e))

def generate_flow_or_context_node(state: AgentState):
    if state["rag_context"]:
        return state  # No requiere flujo técnico

    try:
        flow_prompt = load_prompt_template(state['domain'], "flow_generator_rag.txt")
        flow_text, duration, _ = call_model("mistral", flow_prompt, state['enhanced_question'])
        flow = f"#### 🔀 Flujo Técnico:\n\n{flow_text.strip()}"
        return {**state, "flow": flow, "total_time": state["total_time"] + duration}
    except Exception as e:
        raise FlowGenerationError(str(e))

def generate_sql_node(state: AgentState):
    try:
        sql_prompt_template = load_prompt_template(state['domain'], "system_context_rag.txt")
        prompt = sql_prompt_template.format(
            flow=state.get("flow", ""),
            context=state.get("rag_context", "")
        )
        raw_sql, duration, _ = call_model("mistral", prompt, state['enhanced_question'])
        return {**state, "sql": raw_sql, "total_time": state["total_time"] + duration}
    except Exception as e:
        raise InferenceServiceError(str(e))

def extract_sql_node(state: AgentState):
    try:
        start_time = time.time()            
        
        safe_sql = safe_extract_sql(state["sql"])        
        formatted_sql = preprocess_sql(safe_sql)        
        validate_sql(formatted_sql)

        duration = round(time.time() - start_time, 2)
        return {**state, "sql": formatted_sql, "total_time": state["total_time"] + duration}
    except Exception as e:
        logger.error(str(e))
        
def execute_sql_node(state: AgentState):
    try:
        formatted_sql = state['sql']
        print(f"{formatted_sql}")
        result, duration = execute_sql(formatted_sql, domain=state['domain'])
        return {**state, "sql": formatted_sql, "result": result, "total_time": state["total_time"] + duration}
    except Exception as e:
        logger.error(str(e))
        return {**state, "result": {"error": str(e)}}


# --- 3. Definición del grafo LangGraph ---
def build_sql_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("enhance", enhance_question_node)
    builder.add_node("rag", get_context_node)
    builder.add_node("generate_flow", generate_flow_or_context_node)
    builder.add_node("generate_sql", generate_sql_node)
    builder.add_node("extract_sql", extract_sql_node)
    builder.add_node("execute", execute_sql_node)

    builder.set_entry_point("enhance")
    builder.add_edge("enhance", "rag")
    builder.add_edge("rag", "generate_flow")
    builder.add_edge("generate_flow", "generate_sql")
    builder.add_edge("generate_sql", "extract_sql")
    builder.add_edge("extract_sql", "execute")
    builder.add_edge("execute", END)

    return builder.compile()


# --- 4. Wrapper para invocar el grafo ---
async def run_sql_graph(question: str, domain: str) -> AgentState:
    graph = build_sql_agent_graph()
    return await graph.ainvoke({"question": question, "domain": domain, "total_time": 0.0})
