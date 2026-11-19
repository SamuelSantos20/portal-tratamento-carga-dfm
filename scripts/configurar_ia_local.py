"""Instala codigo e referencia pesos de origem local confiavel, fora do Git."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.ai_model import REQUIRED_CODE, validate_manifest
from backend.private_paths import private_path, private_root, ensure_private_directory

def configure(source, base):
    source, base = Path(source).resolve(), Path(base).resolve()
    if not base.is_relative_to(private_root()):
        raise ValueError('A base deve estar na area privada configurada.')
    report_path = base / 'modelos/resultado_treinamento.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    selected = report['selected']['name']
    if not selected.replace('_', '').isalnum():
        raise ValueError('Nome de modelo invalido.')
    model_files = [report_path, base / 'modelos/lexical.joblib']
    if selected != 'lexical':
        model_files.append(base / 'modelos' / (selected + '.pt'))
    sources = [source / name for name in sorted(REQUIRED_CODE)]
    for path in sources + model_files:
        if not path.is_file():
            raise ValueError('Instalacao incompleta. Nenhuma configuracao foi ativada.')
    runtime = private_path('runtime', 'ia_scm')
    if runtime.exists():
        raise FileExistsError('Runtime privado ja existe; preserve-o antes de configurar outra versao.')
    ensure_private_directory(runtime)
    for path in sources:
        shutil.copy2(path, runtime / path.name)
    files = [runtime / p.name for p in sources] + model_files
    entries = []
    for path in files:
        with path.open('rb') as stream:
            entries.append({'path': str(path), 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()})
    manifest = runtime / 'manifest.json'
    manifest.write_text(json.dumps({'version': 1, 'runtime_dir': str(runtime), 'base_dir': str(base), 'files': entries}, indent=2), encoding='utf-8')
    for path in [runtime / p.name for p in sources] + [manifest]:
        if os.name == 'nt':
            if not ctypes.windll.advapi32.EncryptFileW(str(path)):
                raise OSError('EFS nao aplicado ao runtime. Revise a protecao da pasta privada.')
        else:
            path.chmod(0o600)
    validate_manifest(manifest)
    print('IA configurada e integridade conferida. Codigo e pesos permanecem na area privada.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-origem', type=Path, required=True)
    parser.add_argument('--base', type=Path, required=True)
    args = parser.parse_args()
    configure(args.runtime_origem, args.base)
