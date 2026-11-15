"""Offline transport fault injection; no real requests or credentials."""
import io
import json
import time
import pytest
from experiments.phase2_acquisition import Acquisition, Stop, ROOT, load_manifest, eligible


class Response:
    def __init__(self, body=b'abc', status=200, headers=None):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = {'Content-Length': str(len(body)), **(headers or {})}
        self.reads = 0

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read1(self, count):
        self.reads += 1
        return self.body.read(count)


def client(tmp_path, response=None):
    response = response or Response()
    calls = []
    class Connection:
        sock = None
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): calls.append((args, kwargs))
        def getresponse(self): return response
        def close(self): pass
    manifest = load_manifest(ROOT / 'docs/PHASE2_ACQUISITION_MANIFEST.json')
    return Acquisition(manifest, tmp_path / 'run', 'testsecret', Connection), calls


def test_original_and_no_retry(tmp_path):
    c, calls = client(tmp_path)
    assert c.fetch('NASA-01') == b'abc'
    assert (c.folder / 'NASA-01.body').read_bytes() == b'abc'
    assert c.body_bytes == 3
    with pytest.raises(Stop, match='retry'): c.fetch('NASA-01')
    assert len(calls) == 1
    assert 'testsecret' not in (c.folder / 'ledger.json').read_text()


@pytest.mark.parametrize('status', [301, 302, 404, 429, 500])
def test_failure_no_body_redirect_or_retry(tmp_path, status):
    response = Response(status=status)
    c, calls = client(tmp_path, response)
    assert c.fetch('NASA-01') is None
    assert response.reads == 0 and c.body_bytes == 0 and len(calls) == 1
    assert not list(c.folder.glob('*.body'))


@pytest.mark.parametrize('headers,reason', [
    ({'Content-Length': '2097153'}, 'declared_response_exceeds_cap'),
    ({'Content-Length': 'bad'}, 'invalid_content_length'),
    ({'Content-Encoding': 'gzip'}, 'encoded_body_refused'),
])
def test_refuse_before_body(tmp_path, headers, reason):
    response = Response(headers=headers)
    c, calls = client(tmp_path, response)
    assert c.fetch('NASA-01') is None
    assert c.entries[-1]['status'] == reason and response.reads == 0


def test_partial_counted_no_complete_original(tmp_path):
    c, calls = client(tmp_path, Response(headers={'Content-Length': '7'}))
    assert c.fetch('NASA-01') is None
    assert c.body_bytes == 3 and c.entries[-1]['status'] == 'incomplete_body'
    assert not list(c.folder.glob('*.body'))


def test_unknown_length_bounded(tmp_path):
    c, calls = client(tmp_path, Response(headers={'Content-Length': None}))
    assert c.fetch('NASA-01') == b'abc'
    assert c.body_bytes == 3


@pytest.mark.parametrize('kind', ['url', 'time', 'requests', 'transfer', 'range_count', 'range_bytes', 'storage'])
def test_budgets_stop_before_request(tmp_path, kind):
    c, calls = client(tmp_path)
    name = 'NASA-01'; kwargs = {}
    if kind == 'url': name = 'unlisted'
    if kind == 'time': c.deadline = time.monotonic() - 1
    if kind == 'requests': c.entries = [{}] * 65
    if kind == 'transfer': c.body_bytes = 128 * 1024 * 1024
    if kind == 'storage': c.manifest['budgets']['max_new_local_phase2_storage_bytes'] = 1
    if kind in ('range_count', 'range_bytes'):
        name = 'MIRROR-YEAR-2023'; kwargs = {'byte_range': (0, 7)}
        if kind == 'range_count': c.range_count = 32
        else: c.range_bytes = 64 * 1024 * 1024
    with pytest.raises(Stop): c.fetch(name, **kwargs)
    assert not calls


@pytest.mark.parametrize('status,headers,success', [
    (206, {'Content-Range': 'bytes 10-12/100', 'ETag': 'v1'}, True),
    (200, {}, False),
    (206, {'Content-Range': 'bytes 11-13/100', 'ETag': 'v1'}, False),
    (206, {'Content-Range': 'bytes 10-12/100', 'ETag': 'v2'}, False),
])
def test_range_snapshot_and_no_full_object(tmp_path, status, headers, success):
    response = Response(status=status, headers=headers)
    c, calls = client(tmp_path, response)
    assert (c.fetch('MIRROR-YEAR-2023', (10, 12), 'v1') is not None) == success
    assert calls[0][1]['headers']['Range'] == 'bytes=10-12'
    assert calls[0][1]['headers']['If-Match'] == 'v1'
    if not success: assert response.reads == 0


def test_credential_echo_not_persisted(tmp_path):
    c, calls = client(tmp_path, Response(b'testsecret'))
    assert c.fetch('NASA-META-02') is None
    assert c.body_bytes == len('testsecret')
    assert all(b'testsecret' not in p.read_bytes() for p in c.folder.iterdir())


def test_scope_availability_is_exact(tmp_path):
    available = [{'data_id': 'MODIS_SP', 'min_date': '2023-01-01', 'max_date': '2023-12-31'}]
    assert eligible(available, {'source': 'MODIS_SP', 'day': '2023-09-01'})
    assert not eligible(available, {'source': 'MODIS_NRT', 'day': '2023-09-01'})
    assert not eligible(available, {'source': 'MODIS_SP', 'day': '2024-01-01'})
    assert not eligible([], {'source': 'MODIS_SP', 'day': '2023-09-01'})


def test_changed_manifest_rejected(tmp_path):
    path = tmp_path / 'manifest.json'
    path.write_text('{}')
    with pytest.raises(Stop, match='digest'): load_manifest(path)


def test_transport_error_text_never_logged(tmp_path):
    c, calls = client(tmp_path)
    def fail(*args, **kwargs): raise OSError('https://example/testsecret')
    c.connection_factory = fail
    assert c.fetch('NASA-01') is None
    assert c.entries[-1]['error_type'] == 'OSError'
    assert 'testsecret' not in (c.folder / 'ledger.json').read_text()
