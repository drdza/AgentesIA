import re
import sqlglot
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Evita agregar múltiples handlers si se llama varias veces
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s]: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


# ---------- 1. Embellecer (opcional) ----------
def _prettify(sql: str) -> str:
    return sqlglot.transpile(
        sql,
        read="postgres",
        write="postgres",
        pretty=True,
        identify=True
    )[0]

# ---------- 2. Parchear ILIKE -----------------
ILIKE_REGEX = re.compile(
    r'("?[A-Za-z0-9_]+"?)\s+ILIKE\s+\'([^\']+)\'',
    flags=re.IGNORECASE
)

def _insert_wildcards(pattern: str) -> str:
    """
    - Si el literal contiene varias palabras y NO tiene comodines intermedios,
      inserta % entre cada token.
    - Asegura % al inicio y al final.
    """
    tokens = pattern.strip('%').split()
    if len(tokens) > 1:
        pattern = "%" + "%".join(tokens) + "%"
    else:                                # una sola palabra
        if not pattern.startswith("%"):
            pattern = "%" + pattern
        if not pattern.endswith("%"):
            pattern = pattern + "%"
    return pattern


def _patch_ilike(sql: str) -> str:
    def _repl(match: re.Match) -> str:
        field, pattern = match.groups()
        pattern = _insert_wildcards(pattern)

        return (
            f'unaccent(lower({field.strip()})) '
            f'ILIKE unaccent(lower(\'{pattern}\'))'
        )

    return ILIKE_REGEX.sub(_repl, sql)

# ---------- 3. Validación básica ---------------
PROHIBITED = {"DROP", "ALTER", "TRUNCATE", "DELETE", "INSERT", "UPDATE"}

def _safety_checks(sql: str) -> None:
    up = sql.upper()
    if not (up.lstrip().startswith("SELECT") or up.lstrip().startswith("WITH")):
        raise ValueError("Solo se permiten SELECT / WITH.")
    for kw in PROHIBITED:
        if kw in up:
            raise ValueError(f"Palabra prohibida detectada: {kw}")

# ---------- 4. Orquestador ---------------------
def beautify_and_patch(raw_sql: str) -> str:
    try:
        #logger.info(f"Raw SQL:\n{raw_sql}")

        pretty = _prettify(raw_sql)
        #logger.info(f"Pretty:\n{pretty}")
        
        patched = _patch_ilike(pretty)
        #logger.info(f"Patched:\n{patched}")

        _safety_checks(patched)
        return patched
    except Exception as e:
        logger.error(e)
        return raw_sql

