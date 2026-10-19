"""Fail closed on missing production configuration; never expose its values."""
import os
from urllib.parse import urlparse


def production():
    return os.getenv('APP_ENV','development').lower() == 'production'


def validate_production():
    if not production():return
    missing=[key for key in ('DATABASE_URL','FRONTEND_URL','PUBLIC_BASE_URL','CORS_ORIGINS') if not os.getenv(key)]
    if missing:raise RuntimeError('Missing production settings: '+', '.join(missing))
    for key in ('FRONTEND_URL','PUBLIC_BASE_URL'):
        parsed=urlparse(os.environ[key])
        if parsed.scheme!='https' or not parsed.hostname or parsed.hostname in ('localhost','127.0.0.1'):
            raise RuntimeError(key+' must be a public HTTPS origin in production')
    if os.getenv('COOKIE_SECURE','false').lower()!='true':
        raise RuntimeError('Production requires COOKIE_SECURE=true')
    if '*' in os.environ['CORS_ORIGINS']:
        raise RuntimeError('Production requires explicit CORS origins')


def browser_assistant_enabled():
    return os.getenv('APPLICATION_ASSISTANT_ENABLED','false' if production() else 'true').lower()=='true'
