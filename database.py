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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            categoria    TEXT PRIMARY KEY,
            valor_limite REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ia_historico (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            data      TEXT    NOT NULL,
            role      TEXT    NOT NULL,
            conteudo  TEXT    NOT NULL,
            arquivado INTEGER NOT NULL DEFAULT 0
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


def get_metas() -> dict[str, float]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT categoria, valor_limite FROM metas ORDER BY categoria")
    metas = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return metas


def salvar_meta(categoria: str, valor_limite: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO metas (categoria, valor_limite) VALUES (?, ?)",
        (categoria, valor_limite),
    )
    conn.commit()
    conn.close()


def deletar_meta(categoria: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM metas WHERE categoria = ?", (categoria,))
    conn.commit()
    conn.close()


def get_config(chave: str, default: str | None = None) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def set_config(chave: str, valor: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
        (chave, valor),
    )
    conn.commit()
    conn.close()


def salvar_mensagem(role: str, conteudo: str):
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO ia_historico (data, role, conteudo) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, conteudo),
    )
    conn.commit()
    conn.close()


def get_historico(limite: int = 100, so_ativos: bool = True) -> list[dict]:
    """Retorna mensagens ordenadas do mais antigo ao mais recente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    filtro = "WHERE arquivado = 0" if so_ativos else ""
    cursor.execute(
        f"SELECT id, data, role, conteudo FROM ia_historico {filtro} "
        f"ORDER BY id DESC LIMIT ?",
        (limite,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "data": r[1], "role": r[2], "conteudo": r[3]}
        for r in reversed(rows)
    ]


def arquivar_historico():
    """Marca todas as mensagens ativas como arquivadas."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE ia_historico SET arquivado = 1 WHERE arquivado = 0")
    conn.commit()
    conn.close()


def get_stats_historico() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*), MIN(data), MAX(data) FROM ia_historico WHERE arquivado = 0"
    )
    total, primeira, ultima = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM ia_historico WHERE arquivado = 1")
    arquivadas = cursor.fetchone()[0]
    conn.close()
    return {"total": total or 0, "primeira": primeira, "ultima": ultima, "arquivadas": arquivadas}
