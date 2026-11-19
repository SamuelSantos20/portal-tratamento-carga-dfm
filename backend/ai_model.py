"""IPC local com o classificador privado. Sem API de IA ou trafego externo."""
import atexit
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

from backend.private_paths import configured_private_path, private_root

REQUIRED_CODE = {'assistente.py', 'conhecimento.py', 'modelo.py', 'processamento.py', 'runtime_security.py'}

def validate_manifest(path):
    root = private_root()
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Manifesto fora da area privada.')
    data = json.loads(path.read_text(encoding='utf-8'))
    runtime = Path(data['runtime_dir']).resolve()
    base = Path(data['base_dir']).resolve()
    if not all(p.is_relative_to(root) for p in (runtime, base)):
        raise ValueError('Instalacao fora da area privada.')
    report_path = base / 'modelos/resultado_treinamento.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    selected = report['selected']['name']
    if not selected.replace('_', '').isalnum():
        raise ValueError('Modelo invalido.')
    required = {runtime / name for name in REQUIRED_CODE} | {report_path, base / 'modelos/lexical.joblib'}
    if selected != 'lexical':
        required.add(base / 'modelos' / (selected + '.pt'))
    receipts = {Path(item['path']).resolve(): item['sha256'] for item in data['files']}
    if not required <= receipts.keys():
        raise ValueError('Instalacao privada incompleta.')
    for file in required:
        if not file.resolve().is_relative_to(root):
            raise ValueError('Link fora da area privada.')
        with file.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != receipts[file]:
                raise ValueError('Integridade da instalacao nao confere.')
    return runtime, base

class LocalModel:
    def __init__(self):
        self.process = None
        self.responses = queue.Queue()
        self.lock = threading.Lock()
        atexit.register(self.close)

    def manifest_path(self):
        return configured_private_path('SCM_AI_MANIFEST', 'runtime', 'ia_scm', 'manifest.json')

    def status(self):
        try:
            validate_manifest(self.manifest_path())
            if not all(importlib.util.find_spec(name) for name in ('torch', 'joblib', 'sklearn', 'numpy')):
                return 'dependencias_ausentes'
            return 'carregado' if self.process and self.process.poll() is None else 'pronto_para_carregar'
        except (OSError, ValueError, KeyError, TypeError):
            return 'nao_configurado'

    def close(self):
        process, self.process = self.process, None
        if process is not None:
            if process.stdin:
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def _read(self, process, responses):
        try:
            for line in process.stdout:
                responses.put(json.loads(line))
        except (ValueError, OSError):
            pass
        finally:
            responses.put({'error': 'modelo_indisponivel'})

    def _response(self):
        try:
            result = self.responses.get(timeout=45)
        except queue.Empty:
            self.close()
            raise RuntimeError('modelo_indisponivel') from None
        if 'error' in result:
            self.close()
            raise RuntimeError('modelo_indisponivel')
        return result

    def classify(self, question):
        if not self.lock.acquire(timeout=2):
            raise RuntimeError('modelo_ocupado')
        try:
            if self.process is None or self.process.poll() is not None:
                self.close()
                manifest = self.manifest_path()
                validate_manifest(manifest)
                self.responses = queue.Queue()
                allowed_environment = {'SYSTEMROOT', 'WINDIR', 'PATH', 'LOCALAPPDATA', 'USERPROFILE', 'HOME', 'TEMP', 'TMP', 'SCM_PRIVATE_DIR'}
                worker_environment = {key: value for key, value in os.environ.items() if key.upper() in allowed_environment}
                worker_environment['OMP_NUM_THREADS'] = '2'
                worker_environment['MKL_NUM_THREADS'] = '2'
                self.process = subprocess.Popen(
                    [sys.executable, '-I', '-B', '-u', str(Path(__file__).with_name('ai_worker.py')), str(manifest)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, encoding='utf-8', bufsize=1,
                    env=worker_environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )
                threading.Thread(target=self._read, args=(self.process, self.responses), daemon=True).start()
                if not self._response().get('ready'):
                    raise RuntimeError('modelo_indisponivel')
            self.process.stdin.write(json.dumps({'pergunta': question}, ensure_ascii=True) + '\n')
            self.process.stdin.flush()
            return self._response()
        except (OSError, ValueError, KeyError):
            self.close()
            raise RuntimeError('modelo_indisponivel') from None
        finally:
            self.lock.release()

model = LocalModel()
