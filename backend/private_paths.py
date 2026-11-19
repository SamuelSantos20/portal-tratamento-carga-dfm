"""Locais privados do operador; nenhum arquivo de dados pertence ao Git."""
import os
import ctypes
import stat
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

def private_root() -> Path:
    default = Path(os.environ['LOCALAPPDATA']) / 'SCM-Confidencial' if os.name == 'nt' else Path.home() / '.local/share/scm-confidencial'
    root = Path(os.environ.get('SCM_PRIVATE_DIR', default)).expanduser()
    if not root.is_absolute():
        raise ValueError('SCM_PRIVATE_DIR deve ser absoluto.')
    root = root.resolve()
    if root.is_relative_to(REPOSITORY):
        raise ValueError('Dados privados devem ficar fora do repositorio.')
    if any(p.casefold().replace(' ', '').startswith(('onedrive', 'dropbox', 'googledrive', 'google-drive')) for p in root.parts):
        raise ValueError('Escolha um diretorio privado sem sincronizacao.')
    return root

def private_path(*parts) -> Path:
    root = private_root()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Caminho fora da area privada.')
    return path

def configured_private_path(name, *default_parts) -> Path:
    path = Path(os.environ.get(name, private_path(*default_parts))).expanduser()
    if not path.is_absolute():
        raise ValueError('Caminho privado deve ser absoluto.')
    path = path.resolve()
    if not path.is_relative_to(private_root()):
        raise ValueError('Caminho fora da area privada.')
    return path

def ensure_private_directory(path) -> Path:
    path = Path(path).resolve()
    if not path.is_relative_to(private_root()):
        raise ValueError('Diretorio fora da area privada.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'nt':
        attributes = path.stat().st_file_attributes
        if not attributes & stat.FILE_ATTRIBUTE_ENCRYPTED:
            if not ctypes.windll.advapi32.EncryptFileW(str(path)):
                raise OSError('Ative a criptografia EFS da area privada antes de iniciar o portal.')
    else:
        path.chmod(0o700)
    return path
