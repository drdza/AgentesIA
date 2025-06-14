# backend/core/query_executor.py

from core.config import DB_CONNECTIONS
from shared.utils import log_to_file, load_config
from core.exceptions import QueryExecutionError
import psycopg2
import time

CONFIG_JSON = load_config()
SQL_EXECUTION_MODE = CONFIG_JSON['execution_mode']
DOMAIN_TO_DB = CONFIG_JSON['domain_to_db']

def execute_sql(sql: str, domain: str):
    """
    Ejecuta una consulta SQL y devuelve los resultados como lista de registros.
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
            msg = f"[SQL EXECUTION ERROR] No hay configuración de base de datos para el dominio '{domain}'"
            log_to_file(msg)
            raise QueryExecutionError(msg)

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

        log_to_file(f"[SQL EXECUTION OK] Tiempo: {duration:.2f}s\nSQL:\n{sql}")
        return result, duration

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        log_to_file(f"[SQL EXECUTION ERROR] Tiempo: {duration:.2f}s\nSQL:\n{sql}\nError: {str(e)}")
        raise QueryExecutionError("Error al ejecutar la consulta SQL en la base de datos") from e
    finally:        
        if cursor:
            cursor.close()
