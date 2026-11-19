"""Processo de inferencia CPU com perguntas recebidas somente por pipe local."""
import json
from pathlib import Path
import socket
import sys

def deny_network(*args, **kwargs):
    raise PermissionError('Rede desativada no processo de inferencia.')

# Defesa adicional para a rede Python; nao substitui isolamento do SO.
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
socket.getaddrinfo = deny_network

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.ai_model import validate_manifest

def main():
    runtime, base = validate_manifest(Path(sys.argv[1]))
    sys.path.insert(0, str(runtime))
    from assistente import Assistente
    from conhecimento import FACTS
    import torch
    torch.set_num_threads(2)
    assistant = Assistente(base=base)
    print(json.dumps({'ready': True}), flush=True)
    for line in sys.stdin:
        try:
            question = json.loads(line)['pergunta']
            if not isinstance(question, str) or not 1 <= len(question) <= 2000:
                raise ValueError('Pergunta invalida.')
            label, confidence, margin = assistant.classify(question)
            fact = FACTS[label]
            accepted = confidence >= assistant.report['threshold'] and margin >= .10 and fact[0] != 'fora_escopo'
            result = {'intencao': fact[0], 'pontuacao': confidence, 'margem': margin, 'aceita': accepted, 'regra': fact[2] if accepted else None, 'pagina': fact[1] or None}
            print(json.dumps(result, ensure_ascii=True), flush=True)
        except Exception:
            print(json.dumps({'error': 'modelo_indisponivel'}), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'error': 'modelo_indisponivel'}), flush=True)
