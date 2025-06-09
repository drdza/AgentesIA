# backend/core/query_executor.py

from core.config import DB_CONNECTIONS
from shared.utils import log_to_file, load_config
import psycopg2
import time

CONFIG_JSON = load_config()
SQL_EXECUTION_MODE = CONFIG_JSON['execution_mode']
DOMAIN_TO_DB = CONFIG_JSON['domain_to_db']

def execute_sql(sql: str, domain: str):
    """
    Ejecuta una consulta SQL dependiendo del dominio de datos.

    Args:
        sql (str): Consulta SQL a ejecutar.
        domain (str): Dominio de datos (ej. tickets, ventas, etc.)

    Returns:
        dict: Resultado de la consulta o error.
    """
    start_time = time.time()    
    if SQL_EXECUTION_MODE == "dummy":
        log_to_file("Modo DUMMY: Simulando ejecución SQL.")
        return {"mensaje": "Ejecución simulada. SQL no ejecutado."}

    try:
        # Obtener configuración específica del dominio
        db_domain = DOMAIN_TO_DB.get(domain)
        db_conf = DB_CONNECTIONS.get(db_domain)
        if not db_conf:
            msg = f"No hay configuración de base de datos para el dominio '{domain}'"
            log_to_file(msg)
            raise ValueError(msg)

        connection = psycopg2.connect(**db_conf)
        cursor = connection.cursor()
        cursor.execute(sql)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result = {"columns": columns, "rows": rows}

        connection.commit()

        cursor.close()
        connection.close()
        duration = round(time.time() - start_time, 2)
        
        return result, duration

    except Exception as e:
        log_to_file(f"Error al ejecutar SQL para el dominio '{domain}': {str(e)}")
        duration = round(time.time() - start_time, 2)
        return {"error": str(e)}, duration
