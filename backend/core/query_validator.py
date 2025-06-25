# backend/core/query_validator.py

import sqlglot
import re
from core.exceptions import QueryValidationError

PROHIBITED_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]

def _extract_last_sql_block(text: str) -> str:
    """
    Intenta extraer un bloque SQ a través de los delimitadores Markdown.
    """
    matches = re.findall(r"```sql\s+(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return matches[-1].strip() if matches else None


def _fallback_extract_sql(text: str) -> str:
    """
    Intenta extraer un bloque SQL sin depender de delimitadores Markdown.
    """
    pattern = re.compile(r"(WITH\s+.*?SELECT|SELECT\s+.*?);", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else None

def preprocess_sql(sql: str) -> str:
    """
    Formatea el SQL usando sqlglot para normalizarlo.
    """
    try:
        return sqlglot.transpile(sql, write='postgres', pretty=True, identify=True)[0]    
    except Exception as e:
        raise QueryValidationError("El SQL no pudo ser procesado correctamente.") from e

def validate_sql(sql: str) -> None:
    """
    Valida que el SQL sea seguro y comience con SELECT o WITH.
    """
    if not sql or not sql.strip():
        raise QueryValidationError("La consulta SQL está vacía o es inválida.")

    sql_upper = sql.upper().lstrip()

    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise QueryValidationError("La consulta debe iniciar con SELECT o WITH (CTE).")

    for keyword in PROHIBITED_KEYWORDS:
        if keyword in sql_upper:
            raise QueryValidationError(f"La consulta contiene una palabra prohibida: {keyword}")


def safe_extract_sql(text: str) -> str:
    """
    Orquesta la extracción robusta de SQL.
    Prioriza bloques Markdown y usa heurística como fallback.
    """
    extracted = _extract_last_sql_block(text)
    if extracted:
        return extracted

    fallback = _fallback_extract_sql(text)
    if fallback:
        return fallback

    return text.strip()






