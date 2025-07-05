import sys
import os
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEndpoint

from shared.utils import load_prompt_template

ENDPOINT_LLM = "http://altheia:8000"
PROMPT_TEMPLATE = load_prompt_template("tickets", "verificator_context.txt")


def response_without_stream():
    question = input("¿Cúal es tu pregunta?\n")
    prompt = PromptTemplate.from_template("""
Eres un clasificador experto en filtrar preguntas que pueden ser respondidas con una consulta estructurada en un Data Warehouse.

Tu tarea es analizar la pregunta a continuación y devolver una respuesta **en formato JSON** con estas claves:

{{
  "dominio_valido": true|false,
  "explicacion": "Motivo claro. Explica si es una consulta analítica o no."
}}

Pregunta: {pregunta}
""")

    llm = HuggingFaceEndpoint(
        endpoint_url=ENDPOINT_LLM,
        max_new_tokens=100,
        top_k=10,
        top_p=0.95,
        typical_p=0.95,
        temperature=0.01,
        repetition_penalty=1.03,
        do_sample=False
    )

    llm_chain = prompt | llm

    response = llm_chain.invoke({"pregunta":question})
    print(response)


def response_with_stream():      
    from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    
    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
    question = input("¿Cúal es tu pregunta?\n") 

    llm = HuggingFaceEndpoint(
            endpoint_url=ENDPOINT_LLM,
            max_new_tokens=512,
            top_k=10,
            top_p=0.95,
            typical_p=0.95,
            temperature=0.01,
            repetition_penalty=1.03,
            callbacks=[StreamingStdOutCallbackHandler()]                
        )
    
    llm_chain = prompt | llm

    for token in llm_chain.stream(question):        
        pass


if __name__ == "__main__":
    print("""
1 - Respuest Directa
2 - Respuesta Streaming
""")
    
    option = int(input('Opción: '))

    match option:
        case 1 :
            response_without_stream()
        case 2:
            response_with_stream()
    
    