
import sqlglot
import re



sql = """

SELECT
  date_trunc('week', fecha_registro)::date AS semana,
  count(*) FILTER (WHERE estatus_ticket = 'EN PROCESO') AS en_proceso
FROM ft_tickets_ia
WHERE fecha_registro >= current_date - interval '2 weeks'
GROUP BY 1;


"""


def preprocess_sql(sql: str) -> str:
    """
    Formatea el SQL usando sqlglot para normalizarlo.
    """
    try:
        parsed = sqlglot.transpile(sql, write='postgres', pretty=True, identify=True)[0]
        transpiled = parsed#.sql(pretty=True)
        return transpiled
        #return _fix_postgres_interval(transpiled)
    except Exception as e:
        print(f"El SQL no pudo ser procesado correctamente.\n{e}")



result = preprocess_sql(sql)
print(result)