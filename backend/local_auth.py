"""Acesso do operador local. A chave nunca e incluida no repositorio ou logs."""
import hashlib
import hmac
import os
import secrets
import time
from backend.private_paths import ensure_private_directory, private_path

COOKIE = 'scm_local_session'
TTL = 8 * 60 * 60

def local_secret():
    directory = ensure_private_directory(private_path('portal'))
    path = directory / 'acesso_local.secret'
    if not path.exists():
        value = secrets.token_hex(32)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w', encoding='ascii') as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
    value = path.read_text(encoding='ascii').strip()
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Chave local invalida; revise a configuracao privada.')
    return value

def same_secret(value):
    return isinstance(value, str) and value.isascii() and hmac.compare_digest(value, local_secret())

def make_cookie():
    payload = f'{int(time.time()) + TTL}:{secrets.token_hex(16)}'
    signature = hmac.new(local_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + ':' + signature

def health_proof(nonce, port=8082):
    return hmac.new(local_secret().encode(), f'health:{port}:{nonce}'.encode(), hashlib.sha256).hexdigest()

def valid_cookie(cookie):
    try:
        expiration, nonce, signature = cookie.split(':')
        if not (0 < int(expiration) - time.time() <= TTL) or len(nonce) != 32:
            return False
        expected = hmac.new(local_secret().encode(), f'{expiration}:{nonce}'.encode(), hashlib.sha256).hexdigest()
        return signature.isascii() and hmac.compare_digest(expected, signature)
    except (AttributeError, TypeError, ValueError):
        return False

def authorized(request):
    header = request.headers.get('authorization', '')
    if header.startswith('Bearer ') and same_secret(header[7:]):
        return True
    return valid_cookie(request.cookies.get(COOKIE))
