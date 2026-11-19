import hashlib
from pathlib import Path
import pytest

def test_access_requires_secret_and_cookie_is_httponly(client):
    from backend.local_auth import local_secret
    del client.headers['authorization']
    assert client.get('/api/status').status_code == 401
    assert client.post('/api/auth/session', json={'chave': 'wrong'}).status_code == 401
    response = client.post('/api/auth/session', json={'chave': local_secret()})
    assert response.status_code == 200
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie
    assert client.get('/api/ai/session').status_code == 200

def test_external_origin_and_host_rejected(client):
    assert client.get('/api/status', headers={'origin': 'https://example.invalid'}).status_code == 403
    assert client.get('/api/status', headers={'host': 'example.invalid'}).status_code == 400
    assert client.get('/api/status', headers={'sec-fetch-site': 'cross-site'}).status_code == 403

def test_remote_clients_rejected(client):
    from backend.main import app
    from fastapi.testclient import TestClient
    with TestClient(app, base_url='http://localhost', client=('192.0.2.1', 1234)) as remote:
        assert remote.get('/api/status').status_code == 403

def test_no_store_and_no_external_resources(client):
    assert client.get('/api/ai/session').headers['cache-control'] == 'no-store'
    index = (Path(__file__).resolve().parents[1] / 'frontend/index.html').read_text(encoding='utf-8')
    assert 'fonts.googleapis.com' not in index and 'fonts.gstatic.com' not in index

def test_cookie_tampering_expiration_and_health_proof(client, monkeypatch):
    from backend import local_auth
    cookie = local_auth.make_cookie()
    assert local_auth.valid_cookie(cookie)
    assert not local_auth.valid_cookie(cookie + 'changed')
    original_time = local_auth.time.time()
    monkeypatch.setattr(local_auth.time, 'time', lambda: original_time + local_auth.TTL + 1)
    assert not local_auth.valid_cookie(cookie)
    proof = client.get('/health', params={'nonce': 'synthetic'}).json()['prova']
    assert proof == local_auth.health_proof('synthetic', 80)
    assert proof != local_auth.local_secret()

def test_invalid_responsible_copies_executor_and_retains_executor():
    from backend.engine_secao10 import process_table_secao10
    raw = b'ano_emissao;ug_executora;ug_executora_nome;ug_beneficiada_acc;ug_beneficiada_nome;ug_responsavel;ug_responsavel_nome;provisao_rcb\n2026;111111;EXEC FICTICIA;222222;BEN FICTICIA;-8;INVALIDO;1.25\n'
    result = process_table_secao10(raw, 'synthetic.csv', 'tb_provisoes')
    row = dict(zip(result['preview_headers'], result['treated_rows'][0]))
    assert (row['ug_responsavel'], row['ug_responsavel_nome']) == ('111111', 'EXEC FICTICIA')
    assert (row['ug_beneficiada_acc'], row['ug_beneficiada_nome']) == ('111111', 'EXEC FICTICIA')
    assert (row['ug_executora'], row['ug_executora_nome']) == ('111111', 'EXEC FICTICIA')

def test_incomplete_executor_blocks_commit(client):
    sid = client.post('/api/ai/sessions').json()['id']
    raw = b'ano_emissao;ug_executora;ug_responsavel;provisao_rcb\n2026;111111;-8;1.25\n'
    result = client.post('/api/secao10/process', files={'file': ('synthetic.csv', raw)}, data={'target_table': 'tb_provisoes', 'session_id': sid})
    assert result.status_code == 200
    assert result.json()['status'] == 'ERRO'
    assert client.post('/api/secao10/commit/tb_provisoes', params={'session_id': sid}).status_code == 409

def test_material_null_preserved_in_database():
    from backend.database import _build_typed_tuples
    parsed = _build_typed_tuples('tb_saldo_material_mb', [['2026', '111111', 'FICTICIO', '111111', 'FICTICIO', '', '0']])
    assert parsed[0][5] is None and parsed[0][6] == 0

def test_minimal_activity_recognized_and_ambiguous_structure_rejected():
    from backend.engine_secao10 import process_table_secao10
    result = process_table_secao10(b'ano_emissao;ug_emitente;ug_emitente_nome;ug_responsavel;valor_dh\n2026;111111;FICTICIO;111111;1.25\n', 'synthetic.csv')
    assert result['file_code'] == '03'
    with pytest.raises(ValueError, match='insuficiente'):
        process_table_secao10(b'ano;ug_emitente;ug_responsavel\n2026;111111;111111\n', 'synthetic.csv')

def test_paths_reject_repository_and_cloud(tmp_path, monkeypatch):
    from backend.private_paths import REPOSITORY, private_root, private_path
    monkeypatch.setenv('SCM_PRIVATE_DIR', str(REPOSITORY / 'private'))
    with pytest.raises(ValueError): private_root()
    monkeypatch.setenv('SCM_PRIVATE_DIR', str(tmp_path / 'OneDrive' / 'private'))
    with pytest.raises(ValueError): private_root()
    monkeypatch.setenv('SCM_PRIVATE_DIR', str(tmp_path / 'private'))
    with pytest.raises(ValueError): private_path('..', 'outside')

def test_manifest_integrity_blocks_modified_runtime(tmp_path, monkeypatch):
    import json
    from backend.ai_model import REQUIRED_CODE, validate_manifest
    root = tmp_path / 'private'
    monkeypatch.setenv('SCM_PRIVATE_DIR', str(root))
    runtime, base = root / 'runtime', root / 'base'
    runtime.mkdir(parents=True)
    (base / 'modelos').mkdir(parents=True)
    files = []
    for name in REQUIRED_CODE:
        path = runtime / name;path.write_text('# synthetic\n');files.append(path)
    report = base / 'modelos/resultado_treinamento.json';report.write_text('{"selected":{"name":"lexical"}}');files.append(report)
    lexical = base / 'modelos/lexical.joblib';lexical.write_bytes(b'synthetic');files.append(lexical)
    manifest = runtime / 'manifest.json'
    manifest.write_text(json.dumps({'runtime_dir': str(runtime), 'base_dir': str(base), 'files': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}))
    assert validate_manifest(manifest) == (runtime, base)
    (runtime / 'assistente.py').write_text('# changed\n')
    with pytest.raises(ValueError): validate_manifest(manifest)
