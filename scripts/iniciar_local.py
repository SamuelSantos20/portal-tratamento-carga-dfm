"""Inicia somente em loopback e abre o acesso local sem imprimir a chave."""
import json
import hmac
import os
from pathlib import Path
import subprocess
import secrets
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.local_auth import local_secret, health_proof

def main():
    secret = local_secret()
    address = 'http://127.0.0.1:8082'
    # Nunca encerrar processos que nao pertencam a este inicializador.
    nonce = secrets.token_hex(16)
    try:
        with urlopen(address + '/health?nonce=' + nonce, timeout=1) as response:
            proof = json.load(response).get('prova', '')
            existing = hmac.compare_digest(proof, health_proof(nonce))
    except Exception:
        existing = False
    process = None
    if not existing:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8082', '--no-proxy-headers', '--no-access-log'], cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for attempt in range(50):
            if process.poll() is not None:
                raise RuntimeError('O servidor nao iniciou. Revise a configuracao local.')
            try:
                with urlopen(address + '/health?nonce=' + nonce, timeout=.5) as response:
                    if response.status == 200 and hmac.compare_digest(json.load(response).get('prova', ''), health_proof(nonce)):
                        break
            except Exception:
                time.sleep(.2)
        else:
            process.terminate()
            raise RuntimeError('Tempo excedido ao iniciar o portal.')
    webbrowser.open(address + '/#acesso=' + secret)
    print('Portal aberto no navegador local. A chave de acesso nao foi exibida.')
    if process:
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait(timeout=10)

if __name__ == '__main__':
    main()
