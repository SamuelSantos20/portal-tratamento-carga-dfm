"""Bloqueia publicacao acidental de dados e pesos. Nao envia arquivos a servicos."""
from __future__ import annotations
import argparse
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys

DATA_EXTENSIONS={'.csv','.tsv','.xls','.xlsx','.ods','.parquet','.feather','.db','.sqlite','.sqlite3','.dump','.backup','.zip','.7z','.rar','.tar','.tgz','.pt','.pth','.safetensors','.joblib','.pkl','.pickle','.npz','.scmvault','.scmenc','.secret'}
PRIVATE_PARTS={'artefatos','data','data_inbox','data_export','resultados_colab','scm-confidencial'}
SECRET_PATTERNS=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'"private_key"\s*:\s*"-----BEGIN'),re.compile(rb'(?:postgres(?:ql)?|mysql)://[^\s/:]+:[^\s/@]+@')]

def git(*args,input=None):
    result=subprocess.run(['git',*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:raise RuntimeError('Nao foi possivel verificar o conteudo Git. Publicacao bloqueada.')
    return result.stdout

def reason(path,content=b''):
    p=PurePosixPath(path);parts={s.casefold() for s in p.parts}
    if p.suffix.casefold() in DATA_EXTENSIONS:return 'arquivo de dados, modelo ou pacote confidencial'
    if parts & PRIVATE_PARTS:return 'diretorio reservado a dados privados'
    if p.name.casefold().startswith('.env') or p.name.casefold() in {'credentials.json','service-account.json'}:return 'arquivo de credenciais'
    if p.suffix.casefold()=='.pdf' and ('ia_scm' in parts or p.name.casefold().startswith('manual_v2')):return 'documento de origem confidencial'
    if len(content)>8*1024*1024:return 'arquivo grande exige revisao manual fora da publicacao automatica'
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):return 'possivel credencial embutida'
    if p.suffix.casefold()=='.ipynb':
        try:nb=json.loads(content)
        except (ValueError,UnicodeDecodeError):return 'notebook invalido'
        if nb.get('metadata',{}).get('widgets'):return 'notebook com estado de widgets salvo'
        for cell in nb.get('cells',[]):
            if cell.get('outputs'):return 'notebook com resultados salvos'
            source=''.join(cell.get('source',[]))
            if re.search(r'data:(?:application|image)/[^;]+;base64,',source):return 'notebook com conteudo binario embutido'
    return None

def inspect(ref=None,full_tree=False):
    if full_tree:
        paths=git('ls-tree','-r','--name-only','-z',ref).split(b'\0')
    elif ref:
        paths=git('diff-tree','--root','-m','--no-commit-id','--name-only','--diff-filter=ACMR','-r','-z',ref).split(b'\0')
    else:paths=git('diff','--cached','--name-only','--diff-filter=ACMR','-z').split(b'\0')
    violations=[]
    for raw in paths:
        if not raw:continue
        path=raw.decode('utf-8',errors='surrogateescape')
        finding=reason(path)
        if not finding:
            spec=f'{ref}:{path}' if ref else ':'+path
            size=int(git('cat-file','-s',spec))
            finding=reason(path,b' '*(8*1024*1024+1)) if size>8*1024*1024 else reason(path,git('show',spec))
        if finding:violations.append((path,finding))
    return violations

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pre-push',action='store_true');args=parser.parse_args()
    try:
        violations=[]
        if args.pre_push:
            commits=set()
            for line in sys.stdin:
                fields=line.split()
                if len(fields)!=4:continue
                local,remote=fields[1],fields[3]
                if set(local)=={'0'}:continue
                # Conferir tambem a arvore completa enviada, mesmo em outro remoto.
                violations.extend(inspect(local,full_tree=True))
                if set(remote)=={'0'}:revisions=git('rev-list',local,'--not','--remotes')
                else:revisions=git('rev-list',remote+'..'+local)
                commits.update(revisions.decode().split())
            for commit in commits:violations.extend(inspect(commit))
        else:violations=inspect()
        if violations:
            print('BLOQUEADO: foram encontrados arquivos privados, resultados ou credenciais.',file=sys.stderr)
            for path,finding in sorted(set(violations)):
                print(f'  {path}: {finding}',file=sys.stderr)
            print('Retire esses arquivos do Git. Dados e pesos devem ficar na area privada local.',file=sys.stderr)
            return 1
        return 0
    except (RuntimeError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
