"""
Camada de Banco de Dados Híbrida (PostgreSQL schema dfm + Espelho Analítico Local SQLite)
Suporta as 5 tabelas oficiais (Arquivos 01 a 05):
  01 -> dfm.tb_provisoes
  02 -> dfm.tb_saldo_material_mb
  03 -> dfm.tb_custos_atividade
  04 -> dfm.tb_custos_ugr_na_liq
  05 -> dfm.tb_custos_atividade_mes
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

from backend.engine_secao10 import TABLE_SCHEMAS, process_table_secao10
from backend.private_paths import private_path, ensure_private_directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(private_path('portal'))
TREATED_EXPORT_DIR = os.path.join(DATA_DIR, "tratados")
DB_PATH = os.path.join(DATA_DIR, "dfm_scm.db")
PG_CONFIG_PATH = os.path.join(DATA_DIR, "pg_config.json")
DDL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_dfm.sql")

DEFAULT_CSVS = {
    "tb_provisoes": r"c:\Users\samue\Downloads\01_Provisoes_MB_2025_2026_PI_TRATADO_20_COLUNAS.csv",
    "tb_saldo_material_mb": r"c:\Users\samue\Downloads\02_Saldo_Material_MB_2025_2026_TRATADO.csv",
    "tb_custos_atividade": r"c:\Users\samue\Downloads\03_Custos_Atividade_2025_2026_TRATADO.csv",
    "tb_custos_ugr_na_liq": r"c:\Users\samue\Downloads\04_Custos_UGR_na_LIQ_2025_2026_TRATADO_EMITENTE.csv",
    "tb_custos_atividade_mes": r"c:\Users\samue\Downloads\05_Custos_Atividade_Mensal_2026_TRATADO_CORRIGIDO.csv",
}


def get_conn() -> sqlite3.Connection:
    legacy = os.path.join(BASE_DIR, 'data', 'dfm_scm.db')
    if os.path.isfile(legacy) and not os.path.exists(DB_PATH):
        raise RuntimeError('Banco legado detectado. Execute scripts/migrar_armazenamento.py antes de iniciar o portal.')
    ensure_private_directory(DATA_DIR)
    ensure_private_directory(TREATED_EXPORT_DIR)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_config() -> Dict[str, Any]:
    cfg = {
        "enabled": os.environ.get("PG_ENABLED", "false").lower() == "true",
        "host": os.environ.get("PG_HOST", "localhost"),
        "port": int(os.environ.get("PG_PORT", "5432")),
        "database": os.environ.get("PG_DATABASE", "DFM_70"),
        "user": os.environ.get("PG_USER", "postgres"),
        "password": os.environ.get("PG_PASSWORD", ""),
        "schema": "dfm",
    }
    if os.path.exists(PG_CONFIG_PATH):
        try:
            with open(PG_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    return cfg


def save_pg_config(new_cfg: Dict[str, Any]) -> Dict[str, Any]:
    ensure_private_directory(DATA_DIR)
    cfg = get_pg_config()
    for k in ("enabled", "host", "port", "database", "user", "password", "schema"):
        if k in new_cfg and new_cfg[k] is not None:
            cfg[k] = new_cfg[k]
    with open(PG_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def test_pg_connection(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if psycopg2 is None:
        return {"connected": False, "message": "Driver psycopg2 não instalado."}
    c = cfg or get_pg_config()
    try:
        conn = psycopg2.connect(
            host=c.get("host", "localhost"),
            port=int(c.get("port", 5432)),
            dbname=c.get("database", "DFM_70"),
            user=c.get("user", "postgres"),
            password=c.get("password", ""),
            connect_timeout=4,
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        conn.close()
        return {"connected": True, "message": f"Conectado ao PostgreSQL ({c.get('database')})", "version": ver}
    except Exception as exc:
        return {"connected": False, "message": f"Falha na conexão PostgreSQL: {exc}"}


def to_float_or_none(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s == '""':
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def to_float_zero(val: Any) -> float:
    res = to_float_or_none(val)
    return res if res is not None else 0.0


def init_db_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # Verifica se alguma tabela existente precisa ser recriada para alinhar com as novas colunas DDL
    for tname, schema_info in TABLE_SCHEMAS.items():
        cur.execute(f"PRAGMA table_info({tname})")
        existing_cols = {r[1] for r in cur.fetchall()}
        required_cols = set(schema_info["columns"])
        if existing_cols and not required_cols.issubset(existing_cols):
            cur.execute(f"DROP TABLE IF EXISTS {tname}")
            cur.execute("DELETE FROM controle_atualizacao WHERE nome_tabela = ?", (f"dfm.{tname}",))

    cur.execute("PRAGMA table_info(controle_atualizacao)")
    ctrl_cols = {r[1] for r in cur.fetchall()}
    if ctrl_cols and "protocolo_carga" not in ctrl_cols:
        cur.execute("ALTER TABLE controle_atualizacao ADD COLUMN protocolo_carga TEXT")

    cur.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        -- 01: dfm.tb_provisoes
        CREATE TABLE IF NOT EXISTS tb_provisoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_emissao INTEGER NOT NULL,
            ug_beneficiada_acc TEXT NOT NULL,
            ug_beneficiada_nome TEXT,
            ug_emitente TEXT,
            ug_emitente_nome TEXT,
            ug_executora TEXT,
            ug_executora_nome TEXT,
            ug_responsavel TEXT,
            ug_responsavel_nome TEXT,
            acao_governo TEXT,
            acao_governo_nome TEXT,
            provisao_rcb REAL DEFAULT 0,
            destaque_rcb REAL DEFAULT 0,
            rpnp_insc REAL DEFAULT 0,
            provisao_liquidada REAL DEFAULT 0,
            destaque_liquidado REAL DEFAULT 0,
            rpnp_liq REAL DEFAULT 0,
            provisao_a_liquidar REAL DEFAULT 0,
            destaque_a_liquidar REAL DEFAULT 0,
            rpnp_a_liq REAL DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            pi TEXT,
            pi_nome TEXT
        );

        CREATE INDEX IF NOT EXISTS tb_provisoes_filtros_idx
            ON tb_provisoes(ano_emissao, ug_beneficiada_acc, acao_governo);
        CREATE INDEX IF NOT EXISTS tb_provisoes_ug_responsavel_idx
            ON tb_provisoes(ano_emissao, ug_responsavel);

        -- 02: dfm.tb_saldo_material_mb
        CREATE TABLE IF NOT EXISTS tb_saldo_material_mb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano INTEGER NOT NULL,
            ug_executora TEXT,
            ug_executora_nome TEXT,
            ug_beneficiada_acc TEXT NOT NULL,
            ug_beneficiada_nome TEXT,
            saldo_material_estoque REAL DEFAULT 0,
            saldo_material_permanente REAL DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS tb_saldo_material_mb_filtros_idx
            ON tb_saldo_material_mb(ano, ug_beneficiada_acc);

        -- 03: dfm.tb_custos_atividade
        CREATE TABLE IF NOT EXISTS tb_custos_atividade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_emissao INTEGER NOT NULL,
            ug_emitente TEXT,
            ug_emitente_nome TEXT,
            ug_responsavel TEXT,
            ug_responsavel_nome TEXT,
            macroatividade TEXT,
            macroatividades_mb TEXT,
            centro_custos TEXT,
            atividade_geral TEXT,
            valor_dh REAL NOT NULL DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            ug_beneficiada_acc TEXT,
            ug_beneficiada_nome TEXT,
            acao_governo TEXT,
            acao_governo_nome TEXT,
            natureza_despesa_detalhada TEXT,
            natureza_despesa_detalhada_nome TEXT,
            atividades_geral TEXT GENERATED ALWAYS AS (atividade_geral) STORED,
            detacusto_dh_rs REAL GENERATED ALWAYS AS (valor_dh) STORED
        );

        CREATE INDEX IF NOT EXISTS tb_custos_atividade_acao_natureza_idx
            ON tb_custos_atividade(acao_governo, natureza_despesa_detalhada);
        CREATE INDEX IF NOT EXISTS tb_custos_atividade_filtros_idx
            ON tb_custos_atividade(ano_emissao, ug_responsavel, macroatividade, centro_custos);

        -- 04: dfm.tb_custos_ugr_na_liq
        CREATE TABLE IF NOT EXISTS tb_custos_ugr_na_liq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_emissao INTEGER NOT NULL,
            ug_emitente TEXT,
            ug_emitente_nome TEXT,
            ug_responsavel TEXT,
            ug_responsavel_nome TEXT,
            detacusto_dh_rs REAL NOT NULL DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            ug_beneficiada_acc TEXT,
            ug_beneficiada_nome TEXT,
            ne TEXT
        );

        CREATE INDEX IF NOT EXISTS tb_custos_ugr_na_liq_beneficiada_ne_idx
            ON tb_custos_ugr_na_liq(ano_emissao, ug_beneficiada_acc, ne);
        CREATE INDEX IF NOT EXISTS tb_custos_ugr_na_liq_filtros_idx
            ON tb_custos_ugr_na_liq(ano_emissao, ug_responsavel);

        -- 05: dfm.tb_custos_atividade_mes
        CREATE TABLE IF NOT EXISTS tb_custos_atividade_mes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_emissao INTEGER NOT NULL,
            ano_referencia_acc INTEGER,
            mes_referencia_acc TEXT,
            mes_referencia_numero INTEGER,
            mes_referencia_ordem INTEGER,
            mes_referencia_data TEXT,
            ug_responsavel TEXT,
            ug_responsavel_nome TEXT,
            ug_beneficiada_acc TEXT,
            ug_beneficiada_nome TEXT,
            ug_emitente TEXT,
            ug_emitente_nome TEXT,
            acao_governo TEXT,
            acao_governo_nome TEXT,
            macroatividades_mb TEXT,
            atividades_geral TEXT,
            centro_custos TEXT,
            natureza_despesa_detalhada TEXT,
            natureza_despesa_detalhada_nome TEXT,
            detacusto_dh_rs REAL
        );

        CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_ano
            ON tb_custos_atividade_mes(ano_emissao);
        CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_beneficiada
            ON tb_custos_atividade_mes(ug_beneficiada_acc);
        CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_emitente
            ON tb_custos_atividade_mes(ug_emitente);
        CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_mes
            ON tb_custos_atividade_mes(mes_referencia_ordem);
        CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_responsavel
            ON tb_custos_atividade_mes(ug_responsavel);

        CREATE TABLE IF NOT EXISTS controle_atualizacao (
            nome_tabela TEXT PRIMARY KEY,
            arquivo_origem TEXT,
            data_hora_inicio TEXT,
            data_hora_fim TEXT,
            status TEXT,
            total_linhas_brutas INTEGER,
            linhas_totalizacao_removidas INTEGER,
            total_linhas_carregadas INTEGER,
            sentinelas_substituidas INTEGER,
            sentinelas_restantes INTEGER,
            soma_financeira_original REAL,
            soma_financeira_carregada REAL,
            protocolo_carga TEXT,
            mensagem_detalhe TEXT
        );
        """
    )
    conn.commit()


def cleanup_temp_tratados() -> int:
    if not os.path.isdir(TREATED_EXPORT_DIR):
        return 0
    removed = 0
    for fname in os.listdir(TREATED_EXPORT_DIR):
        if fname.lower().endswith((".csv", ".xlsx", ".xls", ".tmp")):
            fpath = os.path.join(TREATED_EXPORT_DIR, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    removed += 1
            except OSError:
                pass
    return removed


def _build_typed_tuples(table_name: str, rows: List[List[str]]) -> List[tuple]:
    parsed: List[tuple] = []

    if table_name == "tb_provisoes":
        for r in rows:
            if len(r) < 22:
                continue
            parsed.append((
                int(r[0]) if str(r[0]).isdigit() else 2026,
                r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10],
                to_float_zero(r[11]), to_float_zero(r[12]), to_float_zero(r[13]),
                to_float_zero(r[14]), to_float_zero(r[15]), to_float_zero(r[16]),
                to_float_zero(r[17]), to_float_zero(r[18]), to_float_zero(r[19]),
                r[20], r[21],
            ))

    elif table_name == "tb_saldo_material_mb":
        for r in rows:
            if len(r) < 7:
                continue
            parsed.append((
                int(r[0]) if str(r[0]).isdigit() else 2026,
                r[1], r[2], r[3], r[4],
                to_float_or_none(r[5]),
                to_float_or_none(r[6]),
            ))

    elif table_name == "tb_custos_atividade":
        for r in rows:
            if len(r) < 16:
                continue
            parsed.append((
                int(r[0]) if str(r[0]).isdigit() else 2026,
                r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
                to_float_zero(r[9]),
                r[10], r[11], r[12], r[13], r[14], r[15],
            ))

    elif table_name == "tb_custos_ugr_na_liq":
        for r in rows:
            if len(r) < 9:
                continue
            parsed.append((
                int(r[0]) if str(r[0]).isdigit() else 2026,
                r[1], r[2], r[3], r[4],
                to_float_zero(r[5]),
                r[6], r[7], r[8],
            ))

    elif table_name == "tb_custos_atividade_mes":
        for r in rows:
            if len(r) < 20:
                continue
            parsed.append((
                int(r[0]) if str(r[0]).isdigit() else 2026,
                int(r[1]) if str(r[1]).isdigit() else 2026,
                r[2],
                int(r[3]) if str(r[3]).isdigit() else 1,
                int(r[4]) if str(r[4]).isdigit() else 202601,
                r[5] if r[5] else "2026-01-01",
                r[6], r[7], r[8], r[9], r[10], r[11],
                r[12], r[13], r[14], r[15], r[16], r[17], r[18],
                to_float_zero(r[19]),
            ))

    return parsed


def _sync_to_postgresql_if_enabled(
    table_name: str,
    cols: List[str],
    parsed_tuples: List[tuple],
    protocolo: str,
) -> Dict[str, Any]:
    pg_cfg = get_pg_config()
    if not pg_cfg.get("enabled"):
        return {"pg_synced": False, "pg_message": "Sincronização PostgreSQL desativada (modo SQLite local ativo)."}
    if psycopg2 is None:
        return {"pg_synced": False, "pg_message": "psycopg2 não disponível."}

    try:
        pg_conn = psycopg2.connect(
            host=pg_cfg.get("host", "localhost"),
            port=int(pg_cfg.get("port", 5432)),
            dbname=pg_cfg.get("database", "DFM_70"),
            user=pg_cfg.get("user", "postgres"),
            password=pg_cfg.get("password", ""),
            connect_timeout=8,
        )
        pg_cur = pg_conn.cursor()
        schema = pg_cfg.get("schema", "dfm")
        pg_cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")

        if os.path.exists(DDL_PATH):
            with open(DDL_PATH, "r", encoding="utf-8") as f:
                ddl_sql = f.read()
            pg_cur.execute(ddl_sql)

        pg_cur.execute(f"DELETE FROM {schema}.{table_name};")
        cols_sql = ", ".join(cols)
        insert_sql = f"INSERT INTO {schema}.{table_name} ({cols_sql}) VALUES %s"
        psycopg2.extras.execute_values(pg_cur, insert_sql, parsed_tuples, page_size=2000)
        pg_conn.commit()
        pg_conn.close()
        return {
            "pg_synced": True,
            "pg_message": f"Sincronizado com PostgreSQL ({schema}.{table_name} • {len(parsed_tuples)} registros • Protocolo {protocolo})."
        }
    except Exception as exc:
        return {
            "pg_synced": False,
            "pg_message": f"Aviso PostgreSQL: {exc} (dados salvos no banco local SQLite)."
        }


def load_table_rows(
    conn: sqlite3.Connection,
    table_name: str,
    rows: List[List[str]],
    filename: str,
    metrics: Optional[Dict[str, Any]] = None,
    soma_orig: float = 0.0,
    soma_trat: float = 0.0,
) -> Dict[str, Any]:
    init_db_schema(conn)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    prev_count = int(cur.fetchone()[0] or 0)

    now_dt = datetime.now()
    now_start = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    protocolo = f"{now_dt.year}NL{now_dt.strftime('%H%M%S')}"

    cur.execute(
        """
        INSERT OR REPLACE INTO controle_atualizacao
        (nome_tabela, arquivo_origem, data_hora_inicio, status, total_linhas_brutas, linhas_totalizacao_removidas,
         total_linhas_carregadas, sentinelas_substituidas, sentinelas_restantes, soma_financeira_original,
         soma_financeira_carregada, protocolo_carga, mensagem_detalhe)
        VALUES (?, ?, ?, 'EM_ANDAMENTO', ?, ?, 0, ?, ?, ?, ?, ?, 'Substituindo dados anteriores no banco...')
        """,
        (
            f"dfm.{table_name}",
            filename,
            now_start,
            metrics.get("total_linhas_lidas", len(rows)) if metrics else len(rows),
            metrics.get("linhas_totalizacao_removidas", 0) if metrics else 0,
            metrics.get("sentinelas_substituidas", 0) if metrics else 0,
            metrics.get("sentinelas_restantes_ug", 0) if metrics else 0,
            soma_orig,
            soma_trat,
            protocolo,
        ),
    )
    conn.commit()

    try:
        cols = TABLE_SCHEMAS[table_name]["columns"]
        parsed = _build_typed_tuples(table_name, rows)

        cur.execute(f"DELETE FROM {table_name}")
        placeholders = ",".join(["?"] * len(cols))
        cols_sql = ", ".join(cols)
        cur.executemany(
            f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})",
            parsed,
        )

        if soma_trat == 0.0 and parsed:
            if table_name == "tb_provisoes":
                soma_trat = sum(p[11] + p[12] + p[13] for p in parsed)
            elif table_name == "tb_saldo_material_mb":
                soma_trat = sum((p[5] or 0.0) + (p[6] or 0.0) for p in parsed)
            elif table_name == "tb_custos_atividade":
                soma_trat = sum(p[9] for p in parsed)
            elif table_name == "tb_custos_ugr_na_liq":
                soma_trat = sum(p[5] for p in parsed)
            elif table_name == "tb_custos_atividade_mes":
                soma_trat = sum(p[19] for p in parsed)
            soma_orig = soma_trat

        pg_info = _sync_to_postgresql_if_enabled(table_name, cols, parsed, protocolo)

        inserted_count = len(parsed)
        now_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detalhe_msg = (
            f"Dados anteriores apagados ({prev_count:,} reg.) e substituídos por "
            f"{inserted_count:,} novos registros tratados. {pg_info['pg_message']}"
        ).replace(",", ".")

        cur.execute(
            """
            UPDATE controle_atualizacao
               SET data_hora_fim = ?,
                   status = 'SUCESSO',
                   total_linhas_carregadas = ?,
                   soma_financeira_original = ?,
                   soma_financeira_carregada = ?,
                   protocolo_carga = ?,
                   mensagem_detalhe = ?
             WHERE nome_tabela = ?
            """,
            (
                now_end,
                inserted_count,
                round(soma_orig, 2),
                round(soma_trat, 2),
                protocolo,
                detalhe_msg,
                f"dfm.{table_name}",
            ),
        )
        conn.commit()
        return {
            "linhas_anteriores_removidas": prev_count,
            "linhas_inseridas": inserted_count,
            "protocolo": protocolo,
            "pg_synced": pg_info["pg_synced"],
            "pg_message": pg_info["pg_message"],
        }
    except Exception as exc:
        conn.rollback()
        now_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            UPDATE controle_atualizacao
               SET data_hora_fim = ?,
                   status = 'ERRO',
                   mensagem_detalhe = ?
             WHERE nome_tabela = ?
            """,
            (now_end, str(exc), f"dfm.{table_name}"),
        )
        conn.commit()
        raise


def seed_initial_data_if_needed() -> None:
    conn = get_conn()
    init_db_schema(conn)
    if os.environ.get('SCM_SEED_LEGACY', '').lower() != 'true':
        conn.close()
        return
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM controle_atualizacao WHERE status = 'SUCESSO'")
    done_count = cur.fetchone()[0]
    if done_count >= 5:
        conn.close()
        return

    for tname, fpath in DEFAULT_CSVS.items():
        cur.execute(
            "SELECT 1 FROM controle_atualizacao WHERE nome_tabela = ? AND status = 'SUCESSO'",
            (f"dfm.{tname}",),
        )
        if cur.fetchone():
            continue
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "rb") as f:
                raw_bytes = f.read()
            res = process_table_secao10(
                file_bytes=raw_bytes,
                filename=os.path.basename(fpath),
                target_table=tname,
            )
            soma_orig = sum(r["soma_original"] for r in res["reconciliation"])
            soma_trat = sum(r["soma_tratada"] for r in res["reconciliation"])
            load_table_rows(
                conn=conn,
                table_name=tname,
                rows=res["treated_rows"],
                filename=os.path.basename(fpath),
                metrics=res["metrics"],
                soma_orig=soma_orig,
                soma_trat=soma_trat,
            )
        except Exception as exc:
            print(f"Aviso ao inicializar {tname}: {exc}")

    conn.close()
