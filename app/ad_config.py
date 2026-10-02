"""Load only AD settings, without logging or interpolating passwords."""
import os
from pathlib import Path
from dotenv import dotenv_values


def process_environment():
    local = dotenv_values(Path(__file__).resolve().parent.parent / '.env', interpolate=False)
    env = os.environ.copy()
    for key in ('AD_HOST', 'AD_USERNAME', 'AD_PASSWORD', 'AD_DOMAIN'):
        if key not in os.environ and local.get(key) is not None:
            env[key] = local[key]
    user = env.get('AD_USERNAME', '').strip()
    password = env.get('AD_PASSWORD', '')
    if bool(user) != bool(password):
        raise RuntimeError('Completa AD_USERNAME y AD_PASSWORD en .env. No se utilizara otra cuenta como alternativa.')
    env['AD_USERNAME'] = user
    env.setdefault('AD_HOST', 'DC02.cafedcallao.gob.pe')
    return env


def redact(message, env):
    password = env.get('AD_PASSWORD', '')
    return message.replace(password, '[REDACTADO]') if password else message
