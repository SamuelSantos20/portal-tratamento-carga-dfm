import csv
import io
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pytest

def session(client):
    result = client.post('/api/ai/sessions')
    assert result.status_code == 200
    return result.json()['id']

def upload(client, table='tb_custos_atividade', session_id=None, values=('0.1', '0.2')):
    from backend.engine_secao10 import TABLE_SCHEMAS
    schema = TABLE_SCHEMAS[table]
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(schema['columns'])
    for value in values:
        row = []
        for col in schema['columns']:
            if col in schema['numeric_cols']: cell = value
            elif col in ('ano', 'ano_emissao', 'ano_referencia_acc'): cell = '2026'
            elif col == 'mes_referencia_acc': cell = 'JAN'
            elif col == 'mes_referencia_numero': cell = '1'
            elif col == 'mes_referencia_ordem': cell = '202601'
            elif col == 'mes_referencia_data': cell = '2026-01-01'
            elif col == 'ne': cell = '2026NE000001'
            elif col.endswith('_nome'): cell = 'UNIDADE FICTICIA'
            elif col.startswith('ug_'): cell = '111111'
            else: cell = 'FICTICIO'
            row.append(cell)
        writer.writerow(row)
    return client.post('/api/secao10/process', files={'file': ('synthetic.csv', output.getvalue().encode(), 'text/csv')}, data={'target_table': table, 'session_id': session_id or session(client)})

def ask(client, question, session_id=None):
    payload = {'pergunta': question}
    if session_id: payload['sessao_id'] = session_id
    return client.post('/api/ai/ask', json=payload)

def test_three_real_question_forms_without_model(client, monkeypatch):
    from backend.ai_model import model
    monkeypatch.setattr(model, 'classify', lambda _: pytest.fail('Consulta de sessao nao deve depender do modelo'))
    sid = session(client)
    assert upload(client, session_id=sid).status_code == 200
    report = ask(client, 'Quais arquivos foram analisados e tratados na ultima sessão?', sid).json()
    assert len(report['arquivos']) == 1
    assert report['arquivos'][0]['nome'] == 'synthetic.csv'
    assert not report['arquivos'][0]['carregado_no_banco']
    totals = ask(client, 'Quais os valores totais de cada tabela na ultima analise?', sid).json()
    assert Decimal(totals['totais'][0]['por_ano'][0]['valores']['valor_dh']) == Decimal('0.3')
    complete = ask(client, 'Todas planilhas já foram tratadas?', sid).json()
    assert not complete['sessao']['todas_tratadas']
    assert '03' not in complete['sessao']['arquivos_pendentes']

def test_last_analysis_replaces_not_adds_and_survives_restart(client):
    from backend import ai_sessions
    sid = session(client)
    upload(client, session_id=sid, values=('10',))
    upload(client, session_id=sid, values=('3',))
    result = ai_sessions.summary(sid)
    assert len(result['arquivos']) == 1
    assert Decimal(result['arquivos'][0]['totais_por_ano'][0]['valores']['valor_dh']) == 3
    other = session(client)
    assert ai_sessions.summary(other)['arquivos'] == []
    assert len(ai_sessions.summary(sid)['arquivos']) == 1

def test_simulation_is_not_real_analysis(client):
    sid = session(client)
    response = client.post('/api/secao10/simulate/tb_custos_atividade', params={'session_id': sid})
    assert response.status_code == 200
    result = client.get('/api/ai/session', params={'sessao_id': sid}).json()
    assert result['simulacoes'] == 1
    assert result['arquivos'] == []
    assert not result['todas_tratadas']

def test_all_five_tables_complete(client):
    from backend.engine_secao10 import TABLE_SCHEMAS
    sid = session(client)
    for table in TABLE_SCHEMAS:
        response = upload(client, table=table, session_id=sid, values=('12.34',))
        assert response.status_code == 200
        assert response.json()['status'] == 'SUCESSO'
    assert ask(client, 'Todas planilhas já foram tratadas?', sid).json()['sessao']['todas_tratadas']

def test_unknown_session_and_invalid_question(client):
    assert ask(client, 'Todas planilhas já foram tratadas?', str(uuid4())).status_code == 404
    assert ask(client, ' ').status_code == 422
    assert ask(client, 'x' * 2001).status_code == 422
    assert ask(client, 'Total de cada tabela', "' OR 1=1 --").status_code == 422

def test_unsupported_filters_not_ignored(client):
    sid = session(client)
    upload(client, session_id=sid)
    for question in ('Total do arquivo 03 por UG 111111 em 2026', 'Total do arquivo 03 por ação de governo', 'Total do arquivo 05 por competência JAN/2026'):
        assert ask(client, question, sid).json()['status'] == 'esclarecimento'
    assert ask(client, 'Qual total do arquivo 06?', sid).json()['status'] == 'fora_escopo'
    assert ask(client, 'DELETE FROM tb_provisoes', sid).json()['status'] == 'fora_escopo'

def test_commits_are_distinct_and_session_bound(client):
    sid = session(client)
    upload(client, session_id=sid, values=('1',))
    other = session(client)
    assert client.post('/api/secao10/commit/tb_custos_atividade', params={'session_id': other}).status_code == 409
    response = client.post('/api/secao10/commit/tb_custos_atividade', params={'session_id': sid})
    assert response.status_code == 200
    assert ask(client, 'Todas planilhas já foram tratadas?', sid).json()['arquivos'][0]['carregado_no_banco']
    assert client.post('/api/secao10/commit/tb_custos_atividade', params={'session_id': sid}).status_code == 404

def test_queries_do_not_log_conversation(client):
    from backend.private_paths import private_path
    sid = session(client)
    marker = 'Todas planilhas já foram tratadas? MARCADOR_PRIVADO_FICTICIO'
    ask(client, marker, sid)
    with sqlite3.connect(private_path('portal', 'ai_sessions.sqlite')) as db:
        dump = '\n'.join(db.iterdump())
    assert 'MARCADOR_PRIVADO_FICTICIO' not in dump

def test_model_unavailable_and_abstention(client, monkeypatch):
    from backend.ai_model import model
    monkeypatch.setattr(model, 'classify', lambda _: {'aceita': False})
    assert ask(client, 'Qual regra corrige a unidade negativa?').json()['status'] == 'abstencao'
    def unavailable(_): raise RuntimeError('unavailable')
    monkeypatch.setattr(model, 'classify', unavailable)
    assert ask(client, 'Qual regra corrige a unidade negativa?').json()['status'] == 'modelo_indisponivel'

def test_decimal_null_and_large_values(client):
    from backend.ai_sessions import row_totals
    from backend.engine_secao10 import TABLE_SCHEMAS
    schema = TABLE_SCHEMAS['tb_saldo_material_mb']
    row = ['2026', '111111', 'FICTICIO', '111111', 'FICTICIO', '', '99999999999999.9999']
    result = row_totals({'table_name': 'tb_saldo_material_mb', 'treated_rows': [row, row]})[0]
    assert result['valores']['saldo_material_estoque'] is None
    assert result['ausentes']['saldo_material_estoque'] == 2
    assert result['valores']['saldo_material_permanente'] == '199999999999999.9998'

def test_failed_import_invalidates_previous_success(client):
    sid = session(client)
    upload(client, session_id=sid)
    response = client.post('/api/secao10/process', files={'file': ('invalid.csv', b'')}, data={'target_table': 'tb_custos_atividade', 'session_id': sid})
    assert response.status_code == 400
    report = ask(client, 'Todas planilhas já foram tratadas?', sid).json()
    assert report['arquivos'][0]['status'] == 'ERRO'
    assert '03' in report['sessao']['arquivos_pendentes']
    assert client.post('/api/secao10/commit/tb_custos_atividade', params={'session_id': sid}).status_code == 404

def test_unrecognized_import_recorded(client):
    sid = session(client)
    response = client.post('/api/secao10/process', files={'file': ('invalid.csv', b'')}, data={'session_id': sid})
    assert response.status_code == 400
    result = client.get('/api/ai/session', params={'sessao_id': sid}).json()
    assert result['falhas_nao_identificadas'][0]['nome'] == 'invalid.csv'
