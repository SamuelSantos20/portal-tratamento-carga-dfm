"""Copia consistente do armazenamento antigo; nao apaga ou sobrescreve a origem."""
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.private_paths import ensure_private_directory, private_path

def migrate():
    source = (ROOT / 'data').resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError('Diretorio legado fora do projeto.')
    targets = [(source / name, private_path('portal', name)) for name in ('dfm_scm.db', 'pg_config.json') if (source / name).is_file()]
    if not targets:
        print('Nenhum banco ou configuracao legado encontrado.')
        return
    if any(destination.exists() for _, destination in targets):
        raise FileExistsError('Destino existente. Nenhum arquivo sera sobrescrito.')
    ensure_private_directory(private_path('portal'))
    for original, destination in targets:
        if original.suffix == '.db':
            with sqlite3.connect(original.as_uri() + '?mode=ro', uri=True) as old, sqlite3.connect(destination) as new:
                old.backup(new)
        else:
            shutil.copyfile(original, destination)
    print('Copia privada concluida. Origens preservadas; nenhuma exclusao realizada.')

if __name__ == '__main__':
    migrate()
