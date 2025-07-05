import re
import os
import sys
import unicodedata
from pathlib import Path


# Añade la carpeta raíz al sys.path para permitir imports absolutos
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
from shared.utils import clean_text

# ---------- sanitizador principal ----------
LIKE_PAT = re.compile(
    r"""(?P<op>       # grupo operador
           (?:NOT\s+)? # opcional NOT
           ILIKE|LIKE  # ILIKE o LIKE
         )\s*          # espacios
         '([^']+)'     # grupo literal (comillas simples)""",
    re.IGNORECASE | re.VERBOSE,
)

LITERAL_PAT = re.compile(r"'([^']+)'")        # para = 'texto', IN ('a','b'), etc.

# ---------- util: limpia y normaliza texto ----------
def _normalize(text: str) -> str:
    # quita acentos → ASCII, elimina símbolos raros, mayúsculas
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", text)  # deja alfanum + espacios
    return re.sub(r"\s+", " ", text).strip().upper()

def _fuzzy(text: str) -> str:
    tokens = _normalize(text).split()
    return f"%{'%'.join(tokens)}%"            # % al inicio, entre tokens y al final


def sanitize_query_literals(query: str) -> str:
    # 1️⃣ primero trata ILIKE / LIKE
    def repl_like(m):
        op, literal = m.group("op"), m.group(2)
        return f"{op} '{_fuzzy(literal)}'"
    query = LIKE_PAT.sub(repl_like, query)

    # 2️⃣ luego limpia otros literales (pero sin %)
    def repl_other(m):
        raw = m.group(1)
        return f"'{_normalize(raw)}'"
    query = LITERAL_PAT.sub(repl_other, query)

    return query



# SELECT * FROM "fa_tickets" WHERE departamento_colaborador ILIKE '%ADMINISTRACIÓN ALGO%' AND columna_b ILIKE 'TEXTO'
if __name__ == "__main__":
    query = input("Escribre tu query:\n\n")

    new_query = sanitize_query_literals(query=query)
    print(new_query)