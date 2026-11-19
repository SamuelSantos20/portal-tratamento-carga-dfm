"""Historico local de analises. Nao armazena perguntas ou conversas."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from backend.engine_secao10 import TABLE_SCHEMAS
from backend.private_paths import private_path, ensure_private_directory

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connection():
    path = private_path('portal', 'ai_sessions.sqlite')
    ensure_private_directory(path.parent)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS ai_sessions (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES ai_sessions(id),
                table_name TEXT NOT NULL, filename TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL,
                demonstration INTEGER NOT NULL, rows_count INTEGER NOT NULL,
                totals_json TEXT NOT NULL, metrics_json TEXT NOT NULL,
                errors_json TEXT NOT NULL, commit_json TEXT
            );
            CREATE INDEX IF NOT EXISTS ai_analyses_session ON ai_analyses(session_id, id);
        ''')
        yield db
        db.commit()
    finally:
        db.close()

def valid_id(session_id):
    return str(UUID(str(session_id)))

def create_session():
    session = {'id': str(uuid4()), 'created_at': now()}
    with connection() as db:
        db.execute('INSERT INTO ai_sessions VALUES (?, ?)', (session['id'], session['created_at']))
    return session

def get_session(session_id=None):
    with connection() as db:
        if session_id:
            row = db.execute('SELECT * FROM ai_sessions WHERE id=?', (valid_id(session_id),)).fetchone()
            if row is None:
                raise LookupError('Sessao nao encontrada.')
        else:
            row = db.execute('SELECT * FROM ai_sessions ORDER BY created_at DESC, rowid DESC LIMIT 1').fetchone()
    return dict(row) if row else create_session()

def row_totals(result):
    schema = TABLE_SCHEMAS[result['table_name']]
    columns = schema['columns']
    year_index = columns.index('ano' if 'ano' in columns else 'ano_emissao')
    groups = {}
    for row in result['treated_rows']:
        year = str(row[year_index])
        group = groups.setdefault(year, {'ano': year, 'registros': 0, 'valores': {c: Decimal(0) for c in schema['numeric_cols']}, 'ausentes': {c: 0 for c in schema['numeric_cols']}})
        group['registros'] += 1
        for col in schema['numeric_cols']:
            value = row[columns.index(col)]
            if value is None or str(value).strip() == '':
                group['ausentes'][col] += 1
            else:
                amount = Decimal(str(value))
                if not amount.is_finite():
                    raise ValueError('Valor monetario nao finito.')
                group['valores'][col] += amount
    for group in groups.values():
        group['valores'] = {c: None if group['ausentes'][c] == group['registros'] else format(v, 'f') for c, v in group['valores'].items()}
    return [groups[y] for y in sorted(groups)]

def record_analysis(result, session_id=None, demonstration=False):
    session = get_session(session_id)
    totals = row_totals(result)
    filename = str(result.get('filename', '')).replace('\\', '/').rsplit('/', 1)[-1]
    with connection() as db:
        cur = db.execute('''INSERT INTO ai_analyses
            (session_id, table_name, filename, created_at, status, demonstration,
             rows_count, totals_json, metrics_json, errors_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['id'], result['table_name'], filename, now(), result['status'], int(demonstration), len(result['treated_rows']), json.dumps(totals), json.dumps(result['metrics']), json.dumps(result['validation_errors'])))
        analysis_id = cur.lastrowid
    return session['id'], analysis_id

def mark_committed(analysis_id, commit_info):
    with connection() as db:
        db.execute('UPDATE ai_analyses SET commit_json=? WHERE id=?', (json.dumps(commit_info), analysis_id))

def record_failure(filename, table_name=None, session_id=None):
    session = get_session(session_id)
    table_name = table_name if table_name in TABLE_SCHEMAS else ''
    filename = str(filename).replace('\\', '/').rsplit('/', 1)[-1]
    with connection() as db:
        db.execute('''INSERT INTO ai_analyses
            (session_id, table_name, filename, created_at, status, demonstration,
             rows_count, totals_json, metrics_json, errors_json)
            VALUES (?, ?, ?, ?, 'ERRO', 0, 0, '[]', '{}', ?)''',
            (session['id'], table_name, filename, now(), json.dumps(['Falha ao reconhecer ou tratar o arquivo. Revise a importação.'])))

def summary(session_id=None):
    session = get_session(session_id)
    with connection() as db:
        rows = db.execute('SELECT * FROM ai_analyses WHERE session_id=? ORDER BY id', (session['id'],)).fetchall()
    latest = {}
    demos = 0
    unknown_failures = []
    for row in rows:
        if row['demonstration']:
            demos += 1
            continue
        if row['table_name'] not in TABLE_SCHEMAS:
            unknown_failures.append({'nome': row['filename'], 'analisado_em': row['created_at']})
            continue
        latest[row['table_name']] = row
    files = []
    for name, schema in TABLE_SCHEMAS.items():
        row = latest.get(name)
        if row is not None:
            files.append({'arquivo': schema['file_code'], 'tabela': 'dfm.' + name, 'nome': row['filename'], 'status': row['status'], 'registros': row['rows_count'], 'analisado_em': row['created_at'], 'carregado_no_banco': row['commit_json'] is not None, 'metricas': json.loads(row['metrics_json']), 'pendencias': json.loads(row['errors_json']), 'totais_por_ano': json.loads(row['totals_json'])})
    pending = [s['file_code'] for name, s in TABLE_SCHEMAS.items() if name not in latest or latest[name]['status'] != 'SUCESSO']
    return {'id': session['id'], 'criada_em': session['created_at'], 'arquivos': files, 'arquivos_pendentes': pending, 'falhas_nao_identificadas': unknown_failures, 'todas_tratadas': not pending and not unknown_failures, 'simulacoes': demos, 'escopo': ['01', '02', '03', '04', '05']}
