"""Generate actual application schema and read-only response examples, without NASA."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app


def main():
    output = Path(__file__).resolve().parents[1] / 'docs'
    (output / 'openapi.json').write_text(json.dumps(app.openapi(), indent=2) + '\n')
    examples = []
    with TestClient(app, raise_server_exceptions=False) as client:
        for url in [
            '/api/health', '/api/regions', '/api/methodology',
            '/api/calendar?sensor=MODIS&start=2023-09-01&end=2023-09-05',
            '/api/hotspots?start=2023-09-01&end=2023-09-05&limit=1',
            '/api/explorer/view?dataset=invalid',
        ]:
            response = client.get(url)
            examples.append({'request': 'GET ' + url, 'status': response.status_code,
                             'response': response.json()})
    (output / 'api-response-examples.json').write_text(json.dumps(examples, indent=2) + '\n')


if __name__ == '__main__':
    main()
