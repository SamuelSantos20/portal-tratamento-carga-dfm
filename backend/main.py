"""
API Backend FastAPI — Sistema de Tratamento e Carga de Planilhas (Schema dfm)
Gerencia o fluxo em 3 etapas:
  1. Importação e Reconhecimento Automático (Arquivos 01 a 05)
  2. Tratamento Automático, Higienização de UGs e Conciliação Financeira
  3. Envio Transacional ao Banco de Dados (PostgreSQL schema dfm + SQLite Local)
"""

import csv
import io
import json
import os
import ipaddress
from contextlib import asynccontextmanager
from uuid import UUID
from typing import Any, Dict, Optional
from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile, Request
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend import ai_sessions
from backend.ai_model import model as ai_model
from backend.ai_service import answer as ai_answer
from backend import local_auth

from backend.database import (
    DEFAULT_CSVS,
    TREATED_EXPORT_DIR,
    cleanup_temp_tratados,
    get_conn,
    get_pg_config,
    init_db_schema,
    load_table_rows,
    save_pg_config,
    seed_initial_data_if_needed,
    test_pg_connection,
)
from backend.engine_secao10 import (
    TABLE_SCHEMAS,
    generate_synthetic_raw_sample,
    process_table_secao10,
)

@asynccontextmanager
async def lifespan(app):
    seed_initial_data_if_needed()
    yield
    ai_model.close()

app = FastAPI(
    title="Portal de Integração e Governança de Dados — Tratamento e Carga de Planilhas (Schema dfm)",
    version="3.0.0",
    lifespan=lifespan,
)

LOCAL_ORIGINS = [f'http://{host}:{port}' for host in ('localhost', '127.0.0.1', '[::1]') for port in (5173, 8000, 8082)]
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]'])

@app.middleware('http')
async def local_privacy_boundary(request: Request, call_next):
    try:
        local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    origin = request.headers.get('origin')
    if not local or (origin and origin not in LOCAL_ORIGINS) or request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'detail': 'Portal restrito ao uso local autorizado.'}, status_code=403)
    if request.url.path.startswith('/api/') and request.url.path != '/api/auth/session' and not local_auth.authorized(request):
        return JSONResponse({'detail': 'Abra o portal pelo inicializador local para autorizar esta sessão.'}, status_code=401, headers={'Cache-Control': 'no-store'})
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    return response

# Cache em memória do último lote tratado em prévia (Step 2 -> Step 3)
STAGED_BATCHES: Dict[str, Dict[str, Any]] = {}


@app.get('/health')
def health(request: Request, nonce: str = Query('', max_length=64)):
    return {'status': 'ok', 'prova': local_auth.health_proof(nonce, request.scope['server'][1])}

@app.post('/api/auth/session')
def open_local_session(payload: Dict[str, Any] = Body(...)):
    if not local_auth.same_secret(payload.get('chave')):
        raise HTTPException(status_code=401, detail='Acesso local não autorizado.')
    response = JSONResponse({'autorizado': True})
    response.set_cookie(local_auth.COOKIE, local_auth.make_cookie(), httponly=True, samesite='strict', max_age=local_auth.TTL, path='/')
    return response

class AssistantQuestion(BaseModel):
    pergunta: str = Field(min_length=1, max_length=2000)
    sessao_id: Optional[UUID] = None

@app.get('/api/ai/status')
def assistant_status():
    return {'execucao': 'local', 'classificador': ai_model.status(), 'modelo_experimental': True, 'envio_a_servicos_de_ia': False, 'conversa_persistida': False}

@app.get('/api/ai/session')
def assistant_session(sessao_id: Optional[UUID] = Query(None)):
    try:
        return ai_sessions.summary(str(sessao_id) if sessao_id else None)
    except LookupError:
        raise HTTPException(status_code=404, detail='Sessão não encontrada.') from None

@app.post('/api/ai/sessions')
def new_assistant_session():
    return ai_sessions.summary(ai_sessions.create_session()['id'])

@app.post('/api/ai/ask')
def ask_assistant(payload: AssistantQuestion):
    if not payload.pergunta.strip():
        raise HTTPException(status_code=422, detail='Digite uma pergunta.')
    try:
        ai_sessions.get_session(str(payload.sessao_id) if payload.sessao_id else None)
        return ai_answer(payload.pergunta.strip(), str(payload.sessao_id) if payload.sessao_id else None)
    except LookupError:
        raise HTTPException(status_code=404, detail='Sessão não encontrada.') from None


def get_cc_lookup(conn) -> dict:
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT centro_custos, atividade_geral FROM tb_custos_atividade")
        return {r[0]: r[1] for r in cur.fetchall() if r[0]}
    except Exception:
        return {}


@app.get("/api/status")
def get_system_status():
    conn = get_conn()
    init_db_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT * FROM controle_atualizacao ORDER BY nome_tabela")
    controle = [dict(r) for r in cur.fetchall()]

    table_counts = {}
    for tname in TABLE_SCHEMAS:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tname}")
            table_counts[tname] = int(cur.fetchone()[0] or 0)
        except Exception:
            table_counts[tname] = 0

    conn.close()
    pg_cfg = get_pg_config()
    return {
        "controle_atualizacao": controle,
        "table_counts": table_counts,
        "schemas": TABLE_SCHEMAS,
        "pg_config": {
            "enabled": pg_cfg.get("enabled", False),
            "host": pg_cfg.get("host", "localhost"),
            "port": pg_cfg.get("port", 5432),
            "database": pg_cfg.get("database", "DFM_70"),
            "user": pg_cfg.get("user", "postgres"),
            "schema": pg_cfg.get("schema", "dfm"),
        },
    }


@app.get("/api/db-config")
def read_db_config():
    cfg = get_pg_config()
    return {
        "enabled": cfg.get("enabled", False),
        "host": cfg.get("host", "localhost"),
        "port": cfg.get("port", 5432),
        "database": cfg.get("database", "DFM_70"),
        "user": cfg.get("user", "postgres"),
        "schema": cfg.get("schema", "dfm"),
        "has_password": bool(cfg.get("password")),
    }


@app.post("/api/db-config")
def update_db_config(payload: Dict[str, Any] = Body(...)):
    saved = save_pg_config(payload)
    test_res = test_pg_connection(saved) if saved.get("enabled") else {"connected": False, "message": "Modo SQLite local ativo."}
    return {
        "config": {
            "enabled": saved.get("enabled", False),
            "host": saved.get("host", "localhost"),
            "port": saved.get("port", 5432),
            "database": saved.get("database", "DFM_70"),
            "user": saved.get("user", "postgres"),
            "schema": saved.get("schema", "dfm"),
        },
        "connection_test": test_res,
    }


@app.post("/api/db-config/test")
def test_db_config(payload: Optional[Dict[str, Any]] = Body(None)):
    cfg = get_pg_config()
    if payload:
        cfg.update({k: v for k, v in payload.items() if v is not None and v != ""})
    return test_pg_connection(cfg)


@app.post("/api/secao10/process")
async def upload_and_process_secao10(
    file: UploadFile = File(...),
    target_table: Optional[str] = Form(None),
    default_ano_emissao: Optional[str] = Form("2026"),
    apply_to_db: bool = Form(False),
    session_id: Optional[UUID] = Form(None),
):
    """
    Etapa 1 -> Etapa 2: Recebe a planilha bruta (.csv, .xlsx), identifica automaticamente
    qual das 5 tabelas (01 a 05) corresponde ao arquivo, higieniza UGs, remove linhas de total
    e calcula a conciliação financeira.
    Se apply_to_db=True, já grava direto no banco; se False, prepara o lote para confirmação na Etapa 2.
    """
    try:
        current_session = ai_sessions.get_session(str(session_id) if session_id else None)
    except LookupError:
        raise HTTPException(status_code=404, detail='Sessão não encontrada.') from None
    file_bytes = await file.read()
    conn = get_conn()
    init_db_schema(conn)
    cc_lookup = get_cc_lookup(conn)

    try:
        t_arg = target_table if (target_table and target_table != "AUTO") else None
        result = process_table_secao10(
            file_bytes=file_bytes,
            filename=file.filename or "upload.csv",
            target_table=t_arg,
            default_ano_emissao=default_ano_emissao,
            cc_lookup=cc_lookup,
        )
    except Exception as exc:
        conn.close()
        ai_sessions.record_failure(file.filename or 'arquivo', target_table, current_session['id'])
        if target_table in TABLE_SCHEMAS:
            STAGED_BATCHES.pop(target_table, None)
        raise HTTPException(status_code=400, detail=str(exc))

    os.makedirs(TREATED_EXPORT_DIR, exist_ok=True)
    out_filename = f"{result['file_code']}_{result['table_name']}_TRATADO.csv"
    out_path = os.path.join(TREATED_EXPORT_DIR, out_filename)
    db_update_info = {
        "linhas_anteriores_removidas": 0,
        "linhas_inseridas": 0,
        "protocolo": None,
        "pg_synced": False,
        "pg_message": "",
    }
    applied = False

    analysis_session, analysis_id = ai_sessions.record_analysis(result, current_session['id'])
    # Armazena no cache de staging para permitir confirmação instantânea na Etapa 2
    STAGED_BATCHES[result["table_name"]] = {
        "result": result,
        "out_filename": out_filename,
        "session_id": analysis_session,
        "analysis_id": analysis_id,
    }

    try:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(result["csv_content"])

        if apply_to_db and result["status"] == "SUCESSO":
            soma_orig = sum(r["soma_original"] for r in result["reconciliation"])
            soma_trat = sum(r["soma_tratada"] for r in result["reconciliation"])
            db_update_info = load_table_rows(
                conn=conn,
                table_name=result["table_name"],
                rows=result["treated_rows"],
                filename=file.filename or out_filename,
                metrics=result["metrics"],
                soma_orig=soma_orig,
                soma_trat=soma_trat,
            )
            applied = True
            ai_sessions.mark_committed(analysis_id, db_update_info)
            cleanup_temp_tratados()
    finally:
        conn.close()

    return {
        "table_name": result["table_name"],
        "session_id": analysis_session,
        "analysis_id": analysis_id,
        "file_code": result["file_code"],
        "short_name": result["short_name"],
        "table_label": result["table_label"],
        "rule_title": result["rule_title"],
        "rule_summary": result["rule_summary"],
        "structural_analysis": result["structural_analysis"],
        "filename": result["filename"],
        "download_filename": out_filename,
        "applied_to_db": applied,
        "db_update": db_update_info,
        "status": result["status"],
        "timestamp": result["timestamp"],
        "metrics": result["metrics"],
        "reconciliation": result["reconciliation"],
        "sample_transformations": result["sample_transformations"],
        "validation_errors": result["validation_errors"],
        "preview_headers": result["preview_headers"],
        "preview_rows": result["preview_rows"],
    }


@app.post("/api/secao10/commit/{table_name}")
def commit_staged_batch(table_name: str, session_id: Optional[UUID] = Query(None)):
    """
    Etapa 2 -> Etapa 3: Confirma e envia os dados tratados em staging para o banco
    (SQLite local + PostgreSQL schema dfm se ativo) e gera o protocolo de carga.
    """
    if table_name not in TABLE_SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Tabela inválida: {table_name}")

    staged = STAGED_BATCHES.get(table_name)
    if not staged:
        raise HTTPException(status_code=404, detail="Nenhum lote em prévia encontrado para esta tabela. Importe a planilha primeiro.")

    result = staged["result"]
    try:
        current_session = ai_sessions.get_session(str(session_id) if session_id else None)
    except LookupError:
        raise HTTPException(status_code=404, detail='Sessão não encontrada.') from None
    if staged.get('session_id') != current_session['id']:
        raise HTTPException(status_code=409, detail='A prévia pertence a outra sessão. Importe novamente nesta sessão.')
    if result['status'] != 'SUCESSO':
        raise HTTPException(status_code=409, detail='Corrija as pendências de validação antes da carga.')
    out_filename = staged["out_filename"]
    soma_orig = sum(r["soma_original"] for r in result["reconciliation"])
    soma_trat = sum(r["soma_tratada"] for r in result["reconciliation"])

    conn = get_conn()
    try:
        db_update_info = load_table_rows(
            conn=conn,
            table_name=table_name,
            rows=result["treated_rows"],
            filename=result["filename"] or out_filename,
            metrics=result["metrics"],
            soma_orig=soma_orig,
            soma_trat=soma_trat,
        )
    finally:
        conn.close()
        cleanup_temp_tratados()

    ai_sessions.mark_committed(staged['analysis_id'], db_update_info)
    STAGED_BATCHES.pop(table_name, None)
    return {
        "table_name": table_name,
        "file_code": result["file_code"],
        "short_name": result["short_name"],
        "table_label": result["table_label"],
        "filename": result["filename"],
        "download_filename": out_filename,
        "applied_to_db": True,
        "db_update": db_update_info,
        "metrics": result["metrics"],
        "reconciliation": result["reconciliation"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if "datetime" in globals() else result["timestamp"],
    }


@app.post("/api/secao10/simulate/{table_name}")
def simulate_secao10_on_synthetic_raw(table_name: str, session_id: Optional[UUID] = Query(None)):
    """
    Gera uma planilha bruta de demonstração para qualquer uma das 5 tabelas (01 a 05)
    e executa o tratamento automático para pré-visualização na Etapa 2.
    """
    if table_name not in TABLE_SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Tabela inválida: {table_name}")
    try:
        current_session = ai_sessions.get_session(str(session_id) if session_id else None)
    except LookupError:
        raise HTTPException(status_code=404, detail='Sessão não encontrada.') from None

    raw_filename, raw_bytes = generate_synthetic_raw_sample(table_name)
    conn = get_conn()
    init_db_schema(conn)
    cc_lookup = get_cc_lookup(conn)
    conn.close()

    result = process_table_secao10(
        file_bytes=raw_bytes,
        filename=raw_filename,
        target_table=table_name,
        default_ano_emissao="2026",
        cc_lookup=cc_lookup,
    )
    out_filename = f"{result['file_code']}_{result['table_name']}_TRATADO.csv"
    analysis_session, analysis_id = ai_sessions.record_analysis(result, current_session['id'], demonstration=True)
    STAGED_BATCHES[result["table_name"]] = {
        "result": result,
        "out_filename": out_filename,
        "session_id": analysis_session,
        "analysis_id": analysis_id,
    }

    return {
        "table_name": result["table_name"],
        "file_code": result["file_code"],
        "short_name": result["short_name"],
        "table_label": result["table_label"],
        "rule_title": result["rule_title"],
        "rule_summary": result["rule_summary"],
        "structural_analysis": result["structural_analysis"],
        "filename": raw_filename,
        "session_id": analysis_session,
        "analysis_id": analysis_id,
        "download_filename": out_filename,
        "applied_to_db": False,
        "status": result["status"],
        "timestamp": result["timestamp"],
        "metrics": result["metrics"],
        "reconciliation": result["reconciliation"],
        "sample_transformations": result["sample_transformations"],
        "validation_errors": result["validation_errors"],
        "preview_headers": result["preview_headers"],
        "preview_rows": result["preview_rows"],
    }


@app.get("/api/secao10/download/{filename}")
def download_treated_file(filename: str):
    safe_name = os.path.basename(filename)
    fpath = os.path.join(TREATED_EXPORT_DIR, safe_name)
    if os.path.exists(fpath):
        return FileResponse(fpath, media_type="text/csv", filename=safe_name)

    matched_table = None
    for tname in TABLE_SCHEMAS:
        if tname in safe_name:
            matched_table = tname
            break

    if not matched_table:
        raise HTTPException(status_code=404, detail="Arquivo ou tabela correspondente não encontrada.")

    cols = TABLE_SCHEMAS[matched_table]["columns"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(cols)} FROM {matched_table}")
    db_rows = cur.fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(cols)
    for r in db_rows:
        writer.writerow(["" if val is None else val for val in r])

    return Response(
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.get("/api/explorer/{table_name}")
def explore_table(
    table_name: str,
    search: Optional[str] = Query(None),
    ano: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    if table_name not in TABLE_SCHEMAS:
        raise HTTPException(status_code=400, detail="Tabela inválida.")
    conn = get_conn()
    init_db_schema(conn)
    cur = conn.cursor()

    cols = TABLE_SCHEMAS[table_name]["columns"]
    where_clauses = ["1=1"]
    params = []

    if ano and ano != "TODOS":
        ano_col = "ano" if table_name == "tb_saldo_material_mb" else ("ano_emissao" if "ano_emissao" in cols else None)
        if ano_col:
            where_clauses.append(f"{ano_col} = ?")
            params.append(int(ano))

    if search and search.strip():
        q = f"%{search.strip()}%"
        text_cols = [c for c in cols if any(k in c for k in ("ug_", "acao", "macro", "atividade", "centro", "natureza", "pi", "ne"))]
        if text_cols:
            or_sql = " OR ".join(f"CAST({c} AS TEXT) LIKE ?" for c in text_cols)
            where_clauses.append(f"({or_sql})")
            params.extend([q] * len(text_cols))

    w_sql = " AND ".join(where_clauses)
    cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {w_sql}", params)
    total_count = cur.fetchone()[0]

    cur.execute(
        f"SELECT {', '.join(cols)} FROM {table_name} WHERE {w_sql} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "table_name": table_name,
        "columns": cols,
        "total": total_count,
        "rows": rows,
    }


@app.get("/api/schema-sql", response_class=PlainTextResponse)
def get_postgresql_ddl():
    ddl_path = os.path.join(os.path.dirname(__file__), "schema_dfm.sql")
    with open(ddl_path, "r", encoding="utf-8") as f:
        return f.read()


FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
