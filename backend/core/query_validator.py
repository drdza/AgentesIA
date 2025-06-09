# backend/core/query_validator.py

import sqlglot
from sqlglot.errors import ParseError

def validate_sql_query(sql: str) -> bool:
    """
    Valida la estructura del SQL generado usando sqlglot.
    Verifica sintaxis básica y posibles problemas estructurales.
    """
    msg = 'OK'
    try:
        # Intenta parsear el SQL
        expression = sqlglot.parse_one(sql)

        # Validaciones adicionales: aseguramos que al menos haya SELECT y FROM
        sql_lower = sql.lower()

        if "select" not in sql_lower or "from" not in sql_lower:
            print("❌ Error: La consulta no contiene SELECT o FROM.")
            return False

        # Validación básica anti-inyecciones (puedes ampliar este check)
        blacklist = [";--", "drop", "truncate", "delete from", "insert into"]
        if any(black in sql_lower for black in blacklist):
            print("🚨 Error: La consulta contiene palabras clave potencialmente peligrosas.")
            return False

        # (Opcional) Puedes imprimir el SQL formateado para tu log
        formatted_sql = expression.sql(pretty=True)
        # print("✅ SQL validado y formateado:\n", formatted_sql)

        return True, formatted_sql, msg

    except ParseError as e:
        return False, sql, e






