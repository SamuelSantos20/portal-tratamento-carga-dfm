"""Todos os dados destes testes sao sinteticos e ficam em diretorio temporario."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def client(tmp_path, monkeypatch):
    root = tmp_path / 'private'
    monkeypatch.setenv('SCM_PRIVATE_DIR', str(root))
    monkeypatch.setenv('PG_ENABLED', 'false')
    monkeypatch.delenv('SCM_SEED_LEGACY', raising=False)
    from backend import database, main, local_auth
    monkeypatch.setattr(database, 'DATA_DIR', str(root / 'portal'))
    monkeypatch.setattr(database, 'TREATED_EXPORT_DIR', str(root / 'portal/tratados'))
    monkeypatch.setattr(main, 'TREATED_EXPORT_DIR', str(root / 'portal/tratados'))
    monkeypatch.setattr(database, 'DB_PATH', str(root / 'portal/dfm_scm.db'))
    monkeypatch.setattr(database, 'PG_CONFIG_PATH', str(root / 'portal/pg_config.json'))
    main.STAGED_BATCHES.clear()
    from fastapi.testclient import TestClient
    with TestClient(main.app, base_url='http://localhost', client=('127.0.0.1', 50000)) as browser:
        browser.headers['authorization'] = 'Bearer ' + local_auth.local_secret()
        yield browser
    main.STAGED_BATCHES.clear()
