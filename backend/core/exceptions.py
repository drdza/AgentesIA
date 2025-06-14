# backend/core/exceptions.py

class AgentException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class InferenceServiceError(AgentException):
    def __init__(self, message="Error en el servicio de inferencia"):
        super().__init__(message, status_code=502)

class EmbeddingGenerationError(AgentException):
    def __init__(self, message="Fallo al generar embeddings"):
        super().__init__(message, status_code=500)

class SQLGenerationError(AgentException):
    def __init__(self, message="Error al generar la consulta SQL"):
        super().__init__(message, status_code=422)

class QueryValidationError(AgentException):
    def __init__(self, message="Error de validación en la consulta SQL"):
        super().__init__(message, status_code=400)

class QueryExecutionError(AgentException):
    def __init__(self, message="Error al ejecutar la consulta SQL en la base de datos"):
        super().__init__(message, status_code=500)

class CollectionNotFoundError(AgentException):
    def __init__(self, message="Colección no encontrada en la base vectorial"):
        super().__init__(message, status_code=404)

class InvalidCollectionNameError(AgentException):
    def __init__(self, message="Nombre de colección inválido"):
        super().__init__(message, status_code=400)

class CollectionInitError(AgentException):
    def __init__(self, message="Error al inicializar las colecciones de Milvus"):
        super().__init__(message, status_code=500)

class InvalidAgentTypeError(AgentException):
    def __init__(self, message="Tipo de agente inválido"):
        super().__init__(message, status_code=400)

class AgentProcessingError(AgentException):
    def __init__(self, message="Error general al procesar el agente"):
        super().__init__(message, status_code=500)

class ReformulationError(AgentException):
    def __init__(self, message="Error al reformular la pregunta del usuario"):
        super().__init__(message, status_code=500)

class RagContextError(AgentException):
    def __init__(self, message="Error al recuperar contexto desde Milvus"):
        super().__init__(message, status_code=500)

class FlowGenerationError(AgentException):
    def __init__(self, message="Error al generar el flujo técnico con IA"):
        super().__init__(message, status_code=500)

class SQLAgentPipelineError(AgentException):
    def __init__(self, message="Fallo general en el pipeline del agente SQL"):
        super().__init__(message, status_code=500)

class MilvusConnectionError(AgentException):
    def __init__(self, message="Error al conectar o consultar Milvus"):
        super().__init__(message, status_code=500)
