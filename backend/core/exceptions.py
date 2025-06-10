# backend/core/exceptions.py

# backend/core/exceptions.py

class EmbeddingServiceError(Exception):
    """Error al obtener embeddings desde el microservicio."""
    pass

class MilvusConnectionError(Exception):
    """Error al conectar o consultar en Milvus."""
    pass

class InvalidCollectionTypeError(Exception):
    """El tipo de colección recibido no está soportado."""
    pass

class SQLValidationError(Exception):
    """Error de validación en la consulta SQL."""
    pass

class SQLExecutionError(Exception):
    """Fallo durante la ejecución de SQL."""
    pass

class SQLAgentPipelineError(Exception):
    """Fallo en alguna etapa del flujo del agente SQL."""
    pass

class ReformulationError(Exception):
    """Fallo al reformular la pregunta del usuario."""
    pass

class RagContextError(Exception):
    """Fallo al recuperar el contexto con RAG."""
    pass

class FlowGenerationError(Exception):
    """Fallo al generar flujo técnico"""
    pass