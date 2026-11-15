"""Explicit footer inspection using remaining approved ranges, never remote Arrow IO."""
import io
import hashlib
import json
import os
from pathlib import Path
import struct
import threading
import time

import pyarrow.parquet as pq

from experiments.phase2_acquisition import Acquisition, ROOT, Stop, load_manifest
from pipeline.locking import exclusive


def saved_or_fetch(client, case_id, extent, etag):
    previous = next((e for e in client.entries if e['id'] == case_id and e['range'] == list(extent)), None)
    if previous:
        if previous['status'] != 'complete':
            return None  # Never retry a failed range.
        raw = (client.folder / previous['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != previous['sha256'] or previous.get('etag') != etag:
            raise Stop('saved_range_integrity')
        return raw
    return client.fetch(case_id, extent, etag)


def inspect_footers(client):
    results = []
    for spec in client.manifest['mirror_objects']:
        item = {'id': spec['id'], 'status': 'unverified'}
        results.append(item)
        head = next((e for e in client.entries if e['id'] == spec['id'] and e['method'] == 'HEAD'), None)
        if not head or head['status'] != 'complete' or not head.get('etag') or head['etag'].startswith('W/'):
            item['reason'] = 'stable_HEAD_snapshot_missing'
            continue
        size = int(head.get('content-length', '0'))
        if size < 12:
            item['reason'] = 'invalid_object_size'
            continue
        tail = saved_or_fetch(client, spec['id'], (size - 8, size - 1), head['etag'])
        if not tail or tail[-4:] != b'PAR1':
            item['reason'] = 'footer_tail_unavailable_or_invalid'
            continue
        footer_length = struct.unpack('<I', tail[:4])[0]
        # Refuse metadata above one response cap, before issuing the request.
        if footer_length > 2 * 1024 * 1024 or footer_length < 1 or footer_length + 12 > size:
            item['reason'] = 'footer_size_budget_or_invalid'
            item['footer_bytes'] = footer_length
            continue
        raw = saved_or_fetch(client, spec['id'], (size - 8 - footer_length, size - 9), head['etag'])
        if raw is None:
            item['reason'] = 'footer_request_failed'
            continue
        metadata = pq.ParquetFile(io.BytesIO(b'PAR1' + raw + tail), thrift_string_size_limit=8*1024*1024, thrift_container_size_limit=1_000_000).metadata
        columns = metadata.schema.names
        item.update(status='footer_verified', footer_bytes=footer_length, rows=metadata.num_rows,
                    row_groups=metadata.num_row_groups, columns=columns, schema=str(metadata.schema), groups=[])
        for i in range(metadata.num_row_groups):
            group = metadata.row_group(i)
            info = {'index': i, 'rows': group.num_rows, 'columns': {}}
            for j in range(group.num_columns):
                column = group.column(j)
                offsets = [x for x in (column.dictionary_page_offset, column.data_page_offset) if x is not None and x > 0]
                record = {'start': min(offsets), 'bytes': column.total_compressed_size,
                          'uncompressed_bytes': column.total_uncompressed_size}
                stats = column.statistics
                if stats and stats.has_min_max:
                    record.update(min=str(stats.min), max=str(stats.max), null_count=stats.null_count)
                info['columns'][column.path_in_schema] = record
            item['groups'].append(info)
    client.write('mirror-footers.json', json.dumps(results, indent=2).encode())
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(ROOT / 'docs/PHASE2_ACQUISITION_MANIFEST.json')
    with exclusive(args.run / '.ranges.lock'):
        if (args.run / 'mirror-footers.json').exists():
            raise Stop('footer_stage_already_complete')
        client = Acquisition.resume_ranges(manifest, args.run)
        watchdog = threading.Timer(max(0, client.deadline - time.monotonic()), lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        try:
            results = inspect_footers(client)
            print(json.dumps([{k:v for k,v in r.items() if k not in ('groups', 'schema')} for r in results]))
        finally:
            watchdog.cancel()
            client.save()


if __name__ == '__main__':
    main()
