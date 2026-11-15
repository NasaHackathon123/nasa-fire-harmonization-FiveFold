"""Isolated, single-use Phase 2 acquisition. Never imported by the application.

Only the approved manifest digest is executable. No retries, redirects, proxies,
remote DuckDB, or URL discovery. Counters are reserved before network access.
"""
import csv
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import ssl
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

MANIFEST_SHA = '7ce2a1c5f9c18306a5190aaef92d63468fb43907eecdf3d96a60ee24eebdeb4e'
ROOT = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat()


class Stop(Exception):
    """Safe fixed reason only; never include URLs or transport exceptions."""


def load_manifest(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise Stop('manifest_digest_mismatch')
    return json.loads(raw)


class Acquisition:
    def __init__(self, manifest, folder, key='', connection_factory=None):
        self.manifest = manifest
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=False)
        self.key = key
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self.started = time.monotonic()
        self.deadline = self.started + manifest['budgets']['wall_clock_acquisition_limit_seconds']
        self.entries = []
        self.used = set()
        self.body_bytes = 0
        self.range_count = 0
        self.range_bytes = 0
        self.allowed = {}
        for section in ('nasa_metadata_requests', 'nasa_observation_requests', 'mirror_metadata_requests'):
            for spec in manifest[section]:
                self.allowed[spec['id']] = (spec, 'metadata' if 'metadata' in section else 'observation')
        for spec in manifest['mirror_objects']:
            self.allowed[spec['id']] = (spec, 'object')
        self.save()

    @classmethod
    def resume_ranges(cls, manifest, folder):
        """Continue only unused ranges against original counters AND deadline.

        No second HEAD/metadata/observation request is permitted by this mode.
        Caller must hold an exclusive local lock across this continuation.
        """
        folder = Path(folder)
        journal = json.loads((folder / 'ledger.json').read_text(encoding='utf-8'))
        if journal['manifest_sha256'] != MANIFEST_SHA or any(e['status'] == 'reserved' for e in journal['requests']):
            raise Stop('unsafe_resume')
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(journal['requests'][0]['started_at'])).total_seconds()
        if elapsed >= manifest['budgets']['wall_clock_acquisition_limit_seconds']:
            raise Stop('elapsed_limit')
        obj = cls.__new__(cls)
        obj.manifest, obj.folder, obj.key = manifest, folder, ''
        obj.connection_factory = http.client.HTTPSConnection
        obj.started = time.monotonic() - elapsed
        obj.deadline = obj.started + manifest['budgets']['wall_clock_acquisition_limit_seconds']
        obj.entries = journal['requests']
        obj.body_bytes = journal['received_body_bytes']
        obj.range_count = journal['range_requests_reserved']
        obj.range_bytes = journal['range_body_bytes']
        obj.used = {e['id'] + (f":{e['range'][0]}-{e['range'][1]}" if e['range'] else ':' + e['method']) for e in obj.entries}
        obj.allowed = {s['id']: (s, 'object') for s in manifest['mirror_objects']}
        return obj

    def write(self, name, body):
        target = self.folder / name
        if target.parent != self.folder or target.exists():
            raise Stop('output_path_or_overwrite_refused')
        used = sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file())
        if used + len(body) + 1024 * 1024 > self.manifest['budgets']['max_new_local_phase2_storage_bytes']:
            raise Stop('storage_budget')
        with target.open('xb') as out:
            out.write(body)

    def save(self):
        record = {'manifest_id': self.manifest['manifest_id'], 'manifest_sha256': MANIFEST_SHA,
                  'approval': 'Explicit user approval in conversation; original manifest retained unchanged',
                  'requests_reserved': len(self.entries), 'received_body_bytes': self.body_bytes,
                  'range_requests_reserved': self.range_count, 'range_body_bytes': self.range_bytes,
                  'elapsed_seconds': time.monotonic() - self.started, 'requests': self.entries}
        raw = json.dumps(record, indent=2).encode()
        if self.key and self.key.encode() in raw:
            raise Stop('secret_in_evidence_refused')
        # Bounded journal (<1 MiB); immutable individual original response files.
        if len(raw) > 1024 * 1024:
            raise Stop('journal_budget')
        (self.folder / 'ledger.json').write_bytes(raw)

    def fetch(self, case_id, byte_range=None, etag=None):
        if case_id not in self.allowed:
            raise Stop('request_not_allowlisted')
        spec, category = self.allowed[case_id]
        is_range = byte_range is not None
        method = 'HEAD' if category == 'object' and not is_range else 'GET'
        if is_range and category != 'object':
            raise Stop('range_not_allowlisted')
        identity = case_id + (f':{byte_range[0]}-{byte_range[1]}' if is_range else ':' + method)
        if identity in self.used:
            raise Stop('retry_refused')
        budgets = self.manifest['budgets']
        if time.monotonic() >= self.deadline or len(self.entries) >= budgets['external_requests_max']:
            raise Stop('time_or_request_budget')
        cap = spec.get('hard_response_cap_bytes', 0)
        if is_range:
            start, end = byte_range
            cap = end - start + 1
            policy = self.manifest['mirror_range_policy']
            if start < 0 or cap < 1 or cap > policy['max_response_bytes_per_range']:
                raise Stop('range_size_budget')
            if self.range_count >= policy['max_total_get_range_requests'] or self.range_bytes + cap > policy['max_total_body_bytes']:
                raise Stop('range_budget')
        if self.body_bytes + cap > budgets['max_all_external_body_bytes']:
            raise Stop('cumulative_transfer_budget')
        # Reserve worst-case disk before request, including bounded journal overhead.
        used = sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file())
        if used + cap + 1024 * 1024 > budgets['max_new_local_phase2_storage_bytes']:
            raise Stop('storage_budget')
        template = spec.get('url_template', spec.get('url'))
        if '{FIRMS_MAP_KEY}' in template and (not self.key or not re.fullmatch(r'[A-Za-z0-9_-]+', self.key)):
            raise Stop('missing_or_invalid_local_key')
        url = urlsplit(template.replace('{FIRMS_MAP_KEY}', self.key))
        if url.scheme != 'https' or url.hostname not in ('firms.modaps.eosdis.nasa.gov', 'data.source.coop'):
            raise Stop('host_refused')
        self.used.add(identity)
        if is_range:
            self.range_count += 1
        entry = {'id': case_id, 'method': method, 'range': byte_range,
                 'started_at': utc(), 'status': 'reserved', 'received_body_bytes': 0}
        self.entries.append(entry)
        self.save()
        connection = None
        start_time = time.monotonic()
        try:
            timeout = min(20, self.deadline - time.monotonic())
            if timeout <= 0:
                raise Stop('elapsed_limit')
            connection = self.connection_factory(url.hostname, timeout=timeout, context=ssl.create_default_context())
            headers = {'Accept-Encoding': 'identity', 'User-Agent': 'NASA-Phase2-controlled-validation/1', 'Connection': 'close'}
            if is_range:
                headers['Range'] = f'bytes={byte_range[0]}-{byte_range[1]}'
                if etag:
                    headers['If-Match'] = etag
            connection.request(method, url.path + ('?' + url.query if url.query else ''), headers=headers)
            response = connection.getresponse()
            entry['http_status'] = response.status
            for header in ('ETag', 'Last-Modified', 'Date', 'Content-Length', 'Content-Range', 'Content-Type', 'Accept-Ranges'):
                value = response.getheader(header)
                if value is not None and len(value) < 1024 and (not self.key or self.key not in value):
                    entry[header.lower()] = value
            if response.status != (206 if is_range else 200):
                raise Stop('http_status_refused')  # No error/redirect bodies or Location logging.
            if method == 'HEAD':
                entry['status'] = 'complete'
                return b''
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise Stop('encoded_body_refused')
            length = response.getheader('Content-Length')
            if length is not None and not length.isdigit():
                raise Stop('invalid_content_length')
            length = int(length) if length is not None else None
            if length is not None and length > cap:
                raise Stop('declared_response_exceeds_cap')
            if is_range:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.getheader('Content-Range', ''))
                if not match or (int(match[1]), int(match[2])) != tuple(byte_range) or int(match[3]) <= byte_range[1] or length != cap:
                    raise Stop('invalid_content_range')
                if etag and response.getheader('ETag') != etag:
                    raise Stop('object_snapshot_changed')
            body = bytearray()
            while length is None or len(body) < length:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise Stop('elapsed_limit')
                if connection.sock:
                    connection.sock.settimeout(min(20, remaining))
                allowance = (length if length is not None else cap) - len(body)
                if allowance <= 0:
                    raise Stop('unknown_length_at_cap')
                block = response.read1(min(65536, allowance))
                if not block:
                    if length is not None:
                        raise Stop('incomplete_body')
                    break
                self.body_bytes += len(block)
                entry['received_body_bytes'] += len(block)
                if is_range:
                    self.range_bytes += len(block)
                body.extend(block)
            if self.key and self.key.encode() in body:
                raise Stop('credential_echo_body_not_saved')
            name = case_id + (f'-{byte_range[0]}-{byte_range[1]}' if is_range else '') + '.body'
            self.write(name, body)
            entry.update(status='complete', file=name, sha256=hashlib.sha256(body).hexdigest())
            return bytes(body)
        except Stop as exc:
            entry['status'] = str(exc)
        except Exception as exc:
            # Transport text can contain the NASA key; retain only the class name.
            entry['status'] = 'transport_error'
            entry['error_type'] = type(exc).__name__
        finally:
            if connection:
                connection.close()
            entry['finished_at'] = utc()
            entry['elapsed_seconds'] = time.monotonic() - start_time
            self.save()
        return None


def eligible(availability, spec):
    return any(r.get('data_id') == spec['source'] and r.get('min_date', '')[:10] <= spec['day'] <= r.get('max_date', '')[:10]
               for r in availability)


def acquire_metadata_and_nasa(manifest, folder, key):
    client = Acquisition(manifest, folder, key)
    # Hard wall clock, including DNS/connect stalls; every request is journaled first.
    watchdog = threading.Timer(manifest['budgets']['wall_clock_acquisition_limit_seconds'], lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    try:
        availability_body = client.fetch('NASA-META-01')
        status_body = client.fetch('NASA-META-02')
        availability = list(csv.DictReader(io.StringIO(availability_body.decode('utf-8-sig')))) if availability_body else []
        headroom = 0
        if status_body:
            try:
                status = json.loads(status_body)
                headroom = int(status['transaction_limit']) - int(status['current_transactions'])
            except (ValueError, KeyError, TypeError):
                pass
        decisions = []
        # Reserve conservative transaction headroom: up to 10 per exact one-day call
        # (large-area transaction accounting), plus two metadata calls.
        for spec in manifest['nasa_observation_requests']:
            reason = 'eligible' if eligible(availability, spec) else 'fresh_availability_does_not_confirm_scope'
            if reason == 'eligible' and headroom < 242:
                reason = 'transaction_headroom_not_confirmed'
            if reason == 'eligible':
                client.fetch(spec['id'])
            decisions.append({'id': spec['id'], 'decision': reason})
        client.fetch('NASA-META-03')
        for spec in manifest['mirror_metadata_requests']:
            client.fetch(spec['id'])
        for spec in manifest['mirror_objects']:
            client.fetch(spec['id'])
        client.write('eligibility.json', json.dumps(decisions, indent=2).encode())
    finally:
        watchdog.cancel()
        client.save()
    return client


def main():
    import argparse
    from dotenv import dotenv_values
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-manifest', required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.approved_manifest)
    config = dotenv_values(os.environ.get('FIRE_ENV_FILE', ROOT / '.env'))
    key = os.environ.get('FIRMS_MAP_KEY', config.get('FIRMS_MAP_KEY', '')) or ''
    parent = ROOT / 'data/phase2_validation' / manifest['manifest_id']
    # A second invocation would reset authorization counters: refuse it.
    if parent.exists():
        raise SystemExit('Existing Phase2 run: automatic restart/retry refused')
    folder = parent / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    try:
        client = acquire_metadata_and_nasa(manifest, folder, key)
        print(json.dumps({'run': folder.relative_to(ROOT).as_posix(), 'requests': len(client.entries),
                          'body_bytes': client.body_bytes, 'statuses': [{k: e[k] for k in ('id', 'status')} for e in client.entries]}))
    except Exception as exc:
        print(json.dumps({'run': folder.relative_to(ROOT).as_posix(), 'stopped': type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
