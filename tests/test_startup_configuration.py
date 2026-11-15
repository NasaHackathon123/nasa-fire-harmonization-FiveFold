"""Fresh-process startup tests use only a temporary .env, never the real file."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


STARTUP = r'''
import json, os, sys
from pathlib import Path
real_env = Path.cwd() / '.env'
def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if Path(os.fsdecode(args[0])).resolve() == real_env.resolve():
            raise AssertionError('Real .env access is forbidden')
sys.addaudithook(guard)
import requests
def no_network(*a, **k):
    raise AssertionError('NASA/network access is forbidden')
requests.get = no_network
requests.Session.request = no_network
try:
    # Even a resource-settings-first import must load the selected environment.
    import pipeline.limits as limits
    from pipeline.config import DATA
    from backend.app.main import app, origins
except ValueError as error:
    print(json.dumps({'error': str(error)}))
    sys.exit(2)
from fastapi.testclient import TestClient
client = TestClient(app)
token = os.environ.get('EXPLORER_ADMIN_TOKEN', '')
responses = [client.get('/api/regions'), client.get('/openapi.json')]
denied = client.post('/api/explorer/load', json={
    'sources':['MODIS_SP'], 'start':'2023-09-01', 'end':'2023-09-01'
})
responses.append(denied)
authorized = client.post('/api/explorer/load', headers={'Authorization':'Bearer '+token}, json={
    'sources':['MODIS_SP'], 'start':'2023-09-01', 'end':'2023-09-01'
})
responses.append(authorized)
for response in responses:
    for name in ('EXPLORER_ADMIN_TOKEN', 'FIRMS_MAP_KEY'):
        secret = os.environ.get(name)
        assert not secret or secret not in response.text
preflight = client.options('/api/regions', headers={
    'Origin': origins[0] if origins else 'https://unconfigured.example',
    'Access-Control-Request-Method': 'GET'
})
print(json.dumps({'origins': origins, 'data': str(DATA),
    'bytes': limits.MAX_FILE_BYTES, 'denied': denied.status_code,
    'authorized': authorized.status_code,
    'cors': preflight.headers.get('access-control-allow-origin')}))
'''


def startup(tmp_path, text='', overrides=None):
    envfile = tmp_path / 'test.env'
    envfile.write_text(text)
    # Never inherit workstation server settings or secrets into these tests.
    env = {k:v for k,v in os.environ.items() if not k.startswith(('FIRE_', 'FIRMS_', 'EXPLORER_'))}
    env.update(FIRE_ENV_FILE=str(envfile), FIRE_DATA_DIR=str(tmp_path/'data'))
    env.update(overrides or {})
    result = subprocess.run([sys.executable, '-c', STARTUP], env=env,
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30)
    assert 'Real .env access is forbidden' not in result.stderr
    return result, json.loads(result.stdout)


def test_dotenv_loaded_before_startup_settings(tmp_path):
    result, values = startup(tmp_path, '\n'.join([
        'FIRE_CORS_ORIGINS=https://frontend.example,http://localhost:3000',
        'EXPLORER_HTTP_INGEST_ENABLED=true',
        'EXPLORER_ADMIN_TOKEN=TEST_ONLY_ADMIN_SENTINEL',
        'FIRMS_MAP_KEY=TEST_ONLY_NASA_SENTINEL',
        'FIRE_MAX_FILE_BYTES=123456',
    ]))
    assert result.returncode == 0, result.stderr
    assert values['origins'] == ['https://frontend.example', 'http://localhost:3000']
    assert values['cors'] == 'https://frontend.example'
    assert values['bytes'] == 123456
    assert values['denied'] == 403 and values['authorized'] == 503
    assert 'TEST_ONLY_ADMIN_SENTINEL' not in result.stdout + result.stderr
    assert 'TEST_ONLY_NASA_SENTINEL' not in result.stdout + result.stderr


def test_os_environment_takes_precedence(tmp_path):
    result, values = startup(tmp_path, '\n'.join([
        'FIRE_CORS_ORIGINS=*', 'EXPLORER_HTTP_INGEST_ENABLED=true',
        'EXPLORER_ADMIN_TOKEN=FILE_ONLY_TOKEN', 'FIRE_MAX_FILE_BYTES=123',
        'FIRE_DATA_DIR=unused-file-directory',
    ]), {'FIRE_CORS_ORIGINS':'https://os.example',
         'EXPLORER_HTTP_INGEST_ENABLED':'false', 'FIRE_MAX_FILE_BYTES':'456'})
    assert result.returncode == 0, result.stderr
    assert values['origins'] == ['https://os.example'] and values['cors'] == 'https://os.example'
    assert values['bytes'] == 456 and values['data'] == str(tmp_path/'data')
    assert values['authorized'] == 403


def test_ingestion_disabled_by_default(tmp_path):
    result, values = startup(tmp_path, 'EXPLORER_ADMIN_TOKEN=TEST_ONLY_TOKEN\n')
    assert result.returncode == 0, result.stderr
    assert values['origins'] == [] and values['cors'] is None
    assert values['denied'] == values['authorized'] == 403


@pytest.mark.parametrize('text', [
    'FIRE_CORS_ORIGINS=*', 'FIRE_CORS_ORIGINS=https://*.example',
    'FIRE_CORS_ORIGINS=not-an-origin', 'FIRE_CORS_ORIGINS=https://host.example/path',
    'FIRE_CORS_ORIGINS=https://user:PRIVATE_SENTINEL@host.example',
    'FIRE_CORS_ORIGINS=https://host.example:invalid',
    'EXPLORER_HTTP_INGEST_ENABLED=yes', 'EXPLORER_HTTP_INGEST_ENABLED=true',
    'EXPLORER_ADMIN_TOKEN="PRIVATE_SENTINEL invalid token"',
    'FIRE_MAX_FILE_BYTES=PRIVATE_SENTINEL', 'FIRE_MAX_OBSERVATIONS=0',
    'FIRE_MAX_CACHE_BYTES=-1', 'FIRE_CACHE_RETENTION_DAYS=-1',
])
def test_invalid_configuration_fails_safely(tmp_path, text):
    result, values = startup(tmp_path, text)
    assert result.returncode == 2
    assert 'error' in values
    assert 'PRIVATE_SENTINEL' not in result.stdout + result.stderr
