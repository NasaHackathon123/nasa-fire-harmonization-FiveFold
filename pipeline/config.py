from pathlib import Path
import os
from dotenv import load_dotenv
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Load once, before any consumer reads settings. OS-provided values always win.
# An explicit file supports isolated deployments and startup regression tests.
load_dotenv(Path(os.environ.get('FIRE_ENV_FILE', ROOT / '.env')), override=False)


def cors_origins():
    origins = [value.strip() for value in os.environ.get('FIRE_CORS_ORIGINS', '').split(',') if value.strip()]
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            port = parsed.port
            valid = (parsed.scheme in ('http', 'https') and parsed.hostname
                     and not any(c.isspace() for c in origin) and '*' not in origin
                     and parsed.username is None and parsed.password is None
                     and not parsed.path and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('FIRE_CORS_ORIGINS requires explicit HTTP(S) origins') from None
    return origins


def validate_admin_settings():
    enabled = os.environ.get('EXPLORER_HTTP_INGEST_ENABLED', 'false').lower()
    if enabled not in ('true', 'false'):
        raise ValueError('EXPLORER_HTTP_INGEST_ENABLED must be true or false')
    token = os.environ.get('EXPLORER_ADMIN_TOKEN', '')
    if (enabled == 'true' and not token) or (token and (not token.isascii() or any(c.isspace() or not c.isprintable() for c in token))):
        raise ValueError('Invalid server administrator token configuration')


DATA = Path(os.environ.get("FIRE_DATA_DIR", ROOT / "data"))
VERSION = "1.0.0"
SOURCES = {"MODIS_SP": "MODIS", "VIIRS_SNPP_SP": "VIIRS", "VIIRS_NOAA20_SP": "VIIRS", "VIIRS_NOAA21_SP": "VIIRS"}
REGIONS = {
    "central-kalimantan": {"id": "central-kalimantan", "name": "Central Kalimantan study box", "bbox": [112, -3, 114, -1]},
    "central-kalimantan-west": {"id": "central-kalimantan-west", "name": "Western study subregion", "bbox": [112, -3, 113, -1]},
}
POLICIES = ("all", "nominal", "strict")
METHOD = "sensor-separated-utm49s-1km-v1"
