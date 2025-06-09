# 🤖 Agentes IA

Este repositorio contiene una arquitectura modular de agentes inteligentes basada en LangChain, FastAPI, Streamlit y Milvus, con soporte para despliegue vía Docker.

## Estructura del proyecto

- `backend/`: Contiene el agente SQL, validaciones, ejecución y lógica de control.
- `frontend/`: Aplicación Streamlit para pruebas y visualización.
- `shared/`: Configuraciones compartidas y archivos JSON de entrenamiento.

## Requisitos

- Docker y Docker Compose
- Python 3.10+
- Acceso a modelo NIM o servidor con GPU

## Despliegue

```bash
docker-compose up --build
