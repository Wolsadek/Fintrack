import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "data" / "financas.db"


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            data          TEXT    NOT NULL,
            valor         REAL    NOT NULL,
            identificador TEXT    UNIQUE,
            descricao     TEXT    NOT NULL,
            categoria     TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regras_categorias (
            padrao    TEXT PRIMARY KEY,
            categoria TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def salvar_transacoes(df: pd.DataFrame) -> tuple[int, int]:
    """Insere transações ignorando duplicatas. Retorna (inseridos, duplicatas)."""
    conn = sqlite3.connect(DB_PATH)
    inseridos = 0
    duplicatas = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                "INSERT INTO transacoes (data, valor, identificador, descricao, categoria) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    row["data"].strftime("%Y-%m-%d"),
                    row["valor"],
                    row["identificador"],
                    row["descricao"],
                    row["categoria"],
                ),
            )
            inseridos += 1
        except sqlite3.IntegrityError:
            duplicatas += 1
    conn.commit()
    conn.close()
    return inseridos, duplicatas


def get_transacoes(mes_ano: str | None = None) -> pd.DataFrame:
    """Retorna transações. mes_ano no formato 'YYYY-MM'."""
    conn = sqlite3.connect(DB_PATH)
    if mes_ano:
        df = pd.read_sql(
            "SELECT * FROM transacoes WHERE strftime('%Y-%m', data) = ? ORDER BY data, id",
            conn,
            params=(mes_ano,),
        )
    else:
        df = pd.read_sql(
            "SELECT * FROM transacoes ORDER BY data, id", conn
        )
    conn.close()
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df


def get_meses_disponiveis() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT strftime('%Y-%m', data) FROM transacoes ORDER BY 1 DESC"
    )
    meses = [row[0] for row in cursor.fetchall()]
    conn.close()
    return meses


def update_categoria(id_: int, categoria: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE transacoes SET categoria = ? WHERE id = ?", (categoria, id_)
    )
    conn.commit()
    conn.close()


def get_regras() -> dict[str, str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT padrao, categoria FROM regras_categorias ORDER BY padrao"
    )
    regras = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return regras


def salvar_regra(padrao: str, categoria: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO regras_categorias (padrao, categoria) VALUES (?, ?)",
        (padrao.lower().strip(), categoria),
    )
    conn.commit()
    conn.close()


def deletar_regra(padrao: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM regras_categorias WHERE padrao = ?", (padrao,))
    conn.commit()
    conn.close()
