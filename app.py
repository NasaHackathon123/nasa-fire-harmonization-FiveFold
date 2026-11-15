import streamlit as st
import streamlit.components.v1 as components
import os

# Comprehensive environment injection for all possible backend variable names
try:
    key_val = st.secrets["FIRMS_MAP_KEY"]
    os.environ["FIRMS_MAP_KEY"] = key_val
    os.environ["NASA_FIRMS_KEY"] = key_val
    os.environ["FIRMS_API_KEY"] = key_val
    os.environ["MAP_KEY"] = key_val
    os.environ["EMBERWATCH_MODE"] = st.secrets.get("EMBERWATCH_MODE", "live")
except Exception:
    pass

import json
from pathlib import Path
import sys

# Ensure src/ is importable so `emberwatch` works without `pip install -e .`
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
  sys.path.insert(0, str(SRC_DIR))

from emberwatch.cli import main as emberwatch_cli
from emberwatch.config import REGIONS, load_settings
from emberwatch.db import connect, init_db
from emberwatch.exports import export_all

st.set_page_config(
    page_title="EmberWatch — NASA MODIS & VIIRS Active Fire Observatory",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def _read_json(path: Path, default):
  if path.exists():
    try:
      return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      return default
  return default


@st.cache_data(ttl=300, show_spinner="Loading harmonised observatory data...")
def load_observatory_payload():
  """Load pre-generated backend exports; auto-bootstrap demo or live data."""
  cfg = load_settings(dotenv_path=ROOT_DIR / ".env")
  export_dir = cfg.export_dir

  audit_path = export_dir / "audit.json"
  audit_data = _read_json(audit_path, {})
  is_synthetic_export = audit_data.get("meta", {}).get("is_synthetic", True)
  
  target_mode = os.environ.get("EMBERWATCH_MODE", "synthetic")
  has_key = bool(os.environ.get("FIRMS_MAP_KEY"))

  # Force live fetch & harmonize if live mode is active and current data is synthetic
  if target_mode == "live" and has_key and is_synthetic_export:
    try:
      emberwatch_cli(["fetch"])
      emberwatch_cli(["harmonize"])
    except Exception as e:
      print(f"Live FIRMS fetch error: {e}")
  elif not audit_path.exists():
    emberwatch_cli(["fetch"])
    emberwatch_cli(["harmonize"])
  elif not (export_dir / "overview_sea.json").exists():
    cfg.ensure_dirs()
    conn = connect(cfg.db_path)
    init_db(conn)
    export_all(conn, cfg)
    conn.close()

  regions_data = {}
  for rid in REGIONS.keys():
    regions_data[rid] = {
        "overview": _read_json(export_dir / f"overview_{rid}.json", {}),
        "hotspots": _read_json(
            export_dir / f"hotspots_{rid}.json", {"hotspots": []}
        ),
        "analytics": _read_json(export_dir / f"analytics_{rid}.json", {}),
        "calendar_0.10": _read_json(
            export_dir / f"calendar_{rid}_0.10.json", {"days": {}}
        ),
        "calendar_0.05": _read_json(
            export_dir / f"calendar_{rid}_0.05.json", {"days": {}}
        ),
        "calendar_0.25": _read_json(
            export_dir / f"calendar_{rid}_0.25.json", {"days": {}}
        ),
    }

  audit_data = _read_json(export_dir / "audit.json", {})
  csv_path = export_dir / "harmonised_fires.csv"
  csv_text = csv_path.read_text(encoding="utf-8") if csv_path.exists() else ""

  return {
      "regions": regions_data,
      "audit": audit_data,
      "csv_text": csv_text,
  }


payload = load_observatory_payload()
payload_json = json.dumps(payload, default=str).replace("</", "<\\/")

EMBERWATCH_HTML = """
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberWatch — NASA MODIS & VIIRS Active Fire Observatory</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        navy: { 900: '#13262E', 800: '#1A333E', 700: '#234453' },
                        paper: { 50: '#F6F7F5', 100: '#ECEEE9', 200: '#D2D7D3' },
                        fire: { orange: '#C85624', amber: '#C98E2B', crimson: '#9E2A22' },
                        forest: { sage: '#5A7265', dark: '#1F3129' }
                    },
                    fontFamily: {
                        serif: ['Newsreader', 'serif'],
                        sans: ['IBM Plex Sans', 'sans-serif'],
                        mono: ['IBM Plex Mono', 'monospace']
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-paper-50 text-navy-900 font-sans antialiased h-full flex flex-col selection:bg-fire-orange selection:text-white">

    <!-- Data Mode Banner (shown automatically if synthetic demo data is active) -->
    <div id="data-mode-banner" class="hidden bg-fire-amber text-navy-900 font-mono text-xs px-6 py-2 text-center font-medium border-b border-navy-900/10"></div>

    <!-- Top Archival Navigation Bar -->
    <header class="bg-navy-900 text-paper-50 border-b border-navy-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <div class="w-8 h-8 bg-fire-orange flex items-center justify-center font-serif font-bold text-white text-lg tracking-tighter">E</div>
                <div>
                    <span class="font-serif text-xl tracking-tight font-medium text-white">EmberWatch</span>
                    <span class="text-xs font-mono uppercase tracking-widest text-paper-200 ml-3 pl-3 border-l border-navy-700 hidden sm:inline">NASA MODIS & VIIRS Observatory</span>
                </div>
            </div>
            <nav class="hidden md:flex items-center space-x-1 font-mono text-xs">
                <button onclick="switchTab('overview')" id="nav-overview" class="px-3 py-1.5 transition-colors bg-navy-800 text-white border-b-2 border-fire-orange">01. Overview</button>
                <button onclick="switchTab('map')" id="nav-map" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">02. GIS Map</button>
                <button onclick="switchTab('calendar')" id="nav-calendar" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">03. Activity Calendar</button>
                <button onclick="switchTab('analytics')" id="nav-analytics" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">04. Analytics</button>
                <button onclick="switchTab('harmonisation')" id="nav-harmonisation" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">05. Harmonisation & Audit</button>
                <button onclick="switchTab('methodology')" id="nav-methodology" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">06. Methodology</button>
            </nav>
            <div class="flex items-center space-x-3 text-xs font-mono">
                <span class="hidden lg:inline text-paper-200">Region:</span>
                <select id="region-selector" onchange="updateRegion()" class="bg-navy-800 text-white border border-navy-700 px-2.5 py-1 text-xs focus:outline-none focus:border-fire-orange font-mono">
                    <option value="sea">Maritime Southeast Asia (Default)</option>
                    <option value="johor">Peninsular Malaysia & Johor</option>
                    <option value="sumatra">Sumatra & Riau Peatlands</option>
                    <option value="borneo">Kalimantan & Borneo</option>
                </select>
            </div>
        </div>
    </header>

    <!-- Main Content Viewport -->
    <main class="flex-1 overflow-y-auto">

        <!-- TAB 01: OVERVIEW -->
        <section id="view-overview" class="p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                <div class="lg:col-span-7 space-y-6">
                    <div class="inline-flex items-center space-x-2 text-xs font-mono bg-paper-100 text-navy-800 px-3 py-1 border border-paper-200">
                        <span class="w-2 h-2 rounded-full bg-fire-orange animate-pulse"></span>
                        <span>NASA Space Apps Challenge 2026 • Harmonised Hotspot Engine</span>
                    </div>
                    <h1 class="font-serif text-4xl md:text-5xl lg:text-6xl font-normal leading-tight text-navy-900">
                        Understanding Earth's Burning Activity.
                    </h1>
                    <p class="text-lg text-forest-sage font-light leading-relaxed max-w-2xl">
                        Synthesising spaceborne thermal anomalies from NASA Terra/Aqua MODIS and NOAA-20/NOAA-21/Suomi-NPP VIIRS instruments into a unified, high-fidelity Burning Activity Calendar for Southeast Asia and global ecosystems.
                    </p>
                    <div class="flex flex-wrap gap-4 pt-2">
                        <button onclick="switchTab('map')" class="bg-navy-900 text-white px-6 py-3 font-mono text-xs hover:bg-navy-800 transition-colors flex items-center space-x-2">
                            <span>Launch GIS Map Explorer</span>
                            <span class="text-fire-orange">→</span>
                        </button>
                        <button onclick="switchTab('calendar')" class="bg-white border border-paper-200 text-navy-900 px-6 py-3 font-mono text-xs hover:bg-paper-100 transition-colors">
                            View Burning Activity Calendar
                        </button>
                    </div>
                </div>

                <!-- Live Regional Summary Card -->
                <div class="lg:col-span-5 bg-white border border-paper-200 p-6 space-y-6 shadow-sm">
                    <div class="flex justify-between items-center border-b border-paper-200 pb-4">
                        <h3 class="font-mono text-xs uppercase tracking-wider text-forest-sage">Observation Parameters (30d)</h3>
                        <span id="overview-region-badge" class="font-mono text-xs bg-paper-100 px-2 py-0.5 text-navy-900">SE Asia</span>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="p-4 bg-paper-50 border border-paper-200">
                            <span class="text-xs font-mono text-forest-sage block">MODIS (1 km)</span>
                            <span id="stat-modis" class="text-2xl font-serif text-navy-900 font-medium">—</span>
                            <span class="text-[10px] font-mono text-forest-sage block mt-1">Terra & Aqua</span>
                        </div>
                        <div class="p-4 bg-paper-50 border border-paper-200">
                            <span class="text-xs font-mono text-forest-sage block">VIIRS (375 m)</span>
                            <span id="stat-viirs" class="text-2xl font-serif text-navy-900 font-medium">—</span>
                            <span class="text-[10px] font-mono text-forest-sage block mt-1">NOAA-20, NOAA-21 & S-NPP</span>
                        </div>
                    </div>
                    <div class="space-y-3 font-mono text-xs">
                        <div class="flex justify-between py-1 border-b border-paper-100">
                            <span class="text-forest-sage">Harmonised Grid Cells</span>
                            <span id="stat-grid" class="font-medium text-navy-900">—</span>
                        </div>
                        <div class="flex justify-between py-1 border-b border-paper-100">
                            <span class="text-forest-sage">Latest Acquisition</span>
                            <span id="stat-latest-acq" class="font-medium text-navy-900">—</span>
                        </div>
                        <div class="flex justify-between py-1">
                            <span class="text-forest-sage">Pipeline Data Mode</span>
                            <span id="stat-data-mode" class="font-medium text-fire-orange">—</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Methodology Pillars -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-paper-200">
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">01 / Spatial Asymmetry</span>
                    <h4 class="font-serif text-lg text-navy-900">Resolution Harmonisation</h4>
                    <p class="text-sm text-forest-sage font-light">
                        MODIS detects sub-pixel fires across 1 km² pixels while VIIRS resolves active burning at 375 m resolution. EmberWatch aggregates detections onto common spatial grid cells so high-density VIIRS clusters never skew comparisons.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">02 / Temporal Heatmap</span>
                    <h4 class="font-serif text-lg text-navy-900">Burning Activity Calendar</h4>
                    <p class="text-sm text-forest-sage font-light">
                        Explore daily thermal activity across Southeast Asia using occupied common grid cells, Harmonised Activity Index (HAI), and historical baseline departures.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">03 / Provenance & Audit</span>
                    <h4 class="font-serif text-lg text-navy-900">Zero Silent Discards</h4>
                    <p class="text-sm text-forest-sage font-light">
                        Every raw NASA FIRMS feed is checksum-verified (SHA-256) in SQLite. Invalid records are quarantined with explicit reason codes while cross-sensor overlaps are linked without deleting observations.
                    </p>
                </div>
            </div>
        </section>

        <!-- TAB 02: GIS MAP -->
        <section id="view-map" class="hidden h-[calc(100vh-4rem)] flex flex-col lg:flex-row">
            <div class="w-full lg:w-80 bg-white border-r border-paper-200 p-5 flex flex-col space-y-6 overflow-y-auto">
                <div>
                    <h2 class="font-serif text-xl text-navy-900">Geospatial Inspector</h2>
                    <p id="map-period-label" class="text-xs text-forest-sage mt-1 font-mono">MODIS & VIIRS Active Fires</p>
                </div>
                <div class="space-y-4 font-mono text-xs">
                    <div class="space-y-2">
                        <label class="text-navy-900 font-medium block">Sensor Layers</label>
                        <label class="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" id="layer-modis" checked onchange="toggleLayers()" class="rounded border-paper-200 text-navy-900 focus:ring-0">
                            <span>MODIS 1km Detections (Squares)</span>
                        </label>
                        <label class="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" id="layer-viirs" checked onchange="toggleLayers()" class="rounded border-paper-200 text-navy-900 focus:ring-0">
                            <span>VIIRS 375m Detections (Circles)</span>
                        </label>
                        <label class="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" id="layer-grid" checked onchange="toggleLayers()" class="rounded border-paper-200 text-navy-900 focus:ring-0">
                            <span>0.10° Occupied Grid Cells</span>
                        </label>
                    </div>
                    <div class="space-y-2 pt-2 border-t border-paper-200">
                        <label class="text-navy-900 font-medium block">Confidence Filter</label>
                        <select id="filter-confidence" onchange="filterMapData()" class="w-full bg-paper-50 border border-paper-200 p-2 font-mono text-xs">
                            <option value="all">All Confidence Levels</option>
                            <option value="nominal">Nominal & High</option>
                            <option value="high">High Confidence Only</option>
                        </select>
                    </div>
                    <div class="space-y-2 pt-2 border-t border-paper-200">
                        <label class="text-navy-900 font-medium block">Min Fire Radiative Power (MW)</label>
                        <input type="range" id="filter-frp" min="0" max="100" value="0" oninput="filterMapData()" class="w-full accent-fire-orange">
                        <div class="flex justify-between text-[10px] text-forest-sage">
                            <span>0 MW</span>
                            <span id="frp-val">0+ MW</span>
                            <span>100+ MW</span>
                        </div>
                    </div>
                    <div class="text-[11px] text-forest-sage pt-1">
                        Showing <span id="map-visible-count" class="text-navy-900 font-semibold">0</span> filtered hotspots
                    </div>
                </div>
                <div id="selected-hotspot-panel" class="mt-auto bg-paper-50 border border-paper-200 p-4 space-y-3 text-xs font-mono">
                    <span class="text-forest-sage uppercase tracking-wider block">Selected Hotspot Telemetry</span>
                    <p class="text-navy-900 italic">Click any marker on the map to inspect satellite acquisition data, brightness temperatures, and FRP.</p>
                </div>
            </div>
            <div class="flex-1 relative">
                <div id="leaflet-map" class="w-full h-full z-0"></div>
            </div>
        </section>

        <!-- TAB 03: CALENDAR -->
        <section id="view-calendar" class="hidden p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-paper-200 pb-6 gap-4">
                <div>
                    <span class="text-xs font-mono text-fire-orange uppercase tracking-wider block mb-1">Core Analytical Engine</span>
                    <h2 class="font-serif text-3xl md:text-4xl text-navy-900">Burning Activity Calendar</h2>
                    <p class="text-sm text-forest-sage mt-1 font-light max-w-xl">
                        Daily harmonised thermal activity. Metrics account for sensor resolution differences using occupied common grid cells and Harmonised Activity Index (HAI).
                    </p>
                </div>
                <div class="flex flex-wrap items-center gap-2 font-mono text-xs">
                    <select id="cal-year-select" onchange="renderCalendar()" class="bg-white border border-paper-200 px-3 py-1.5 font-mono text-xs"></select>
                    <select id="cal-res-select" onchange="renderCalendar()" class="bg-white border border-paper-200 px-3 py-1.5 font-mono text-xs">
                        <option value="0.10">0.10° Grid (~11 km)</option>
                        <option value="0.05">0.05° Grid (~5.5 km)</option>
                        <option value="0.25">0.25° Grid (~27 km)</option>
                    </select>
                    <select id="cal-metric" onchange="renderCalendar()" class="bg-white border border-paper-200 px-3 py-1.5 font-mono text-xs">
                        <option value="hai">Harmonised Activity Index (HAI)</option>
                        <option value="grid">Occupied Grid Cells</option>
                        <option value="viirs">VIIRS Detections</option>
                        <option value="modis">MODIS Detections</option>
                    </select>
                </div>
            </div>

            <div class="bg-white border border-paper-200 p-6 space-y-6">
                <div class="flex justify-between items-center text-xs font-mono border-b border-paper-100 pb-3">
                    <span id="calendar-title" class="font-semibold text-navy-900 text-sm">Burning Heatmap</span>
                    <div class="flex items-center space-x-3 text-[11px] text-forest-sage">
                        <span>No Data / Low</span>
                        <div class="flex space-x-1">
                            <span class="w-3 h-3 bg-paper-100 border border-paper-200"></span>
                            <span class="w-3 h-3 bg-[#C98E2B]"></span>
                            <span class="w-3 h-3 bg-[#C85624]"></span>
                            <span class="w-3 h-3 bg-[#9E2A22]"></span>
                        </div>
                        <span>High Activity</span>
                    </div>
                </div>
                <div id="calendar-months-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"></div>
            </div>

            <!-- Selected Day Dossier -->
            <div id="calendar-day-dossier" class="bg-white border border-paper-200 p-6 space-y-4">
                <div class="flex justify-between items-center border-b border-paper-200 pb-3">
                    <h3 class="font-serif text-xl text-navy-900" id="dossier-date-title">Select a covered date on the calendar</h3>
                    <span class="font-mono text-xs bg-paper-100 px-2.5 py-1 text-navy-900" id="dossier-status">Baseline Departure: n/a</span>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4 font-mono text-xs">
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">Harmonised Activity Index</span>
                        <span id="dossier-hai" class="text-lg font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">Occupied Grid Cells</span>
                        <span id="dossier-grid" class="text-lg font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">MODIS Detections</span>
                        <span id="dossier-modis" class="text-lg font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">VIIRS Detections</span>
                        <span id="dossier-viirs" class="text-lg font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">Mean FRP (MW)</span>
                        <span id="dossier-frp" class="text-lg font-serif text-navy-900 font-medium">—</span>
                    </div>
                </div>
            </div>
        </section>

        <!-- TAB 04: ANALYTICS -->
        <section id="view-analytics" class="hidden p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="border-b border-paper-200 pb-6">
                <span class="text-xs font-mono text-fire-orange uppercase tracking-wider block mb-1">Statistical Intelligence</span>
                <h2 class="font-serif text-3xl md:text-4xl text-navy-900">Fire Analytics & Climatological Baselines</h2>
                <p class="text-sm text-forest-sage mt-1 font-light max-w-xl">
                    Comparative sensor trends, Fire Radiative Power distributions, and weekly Z-score anomaly detection derived from the backend SQLite warehouse.
                </p>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="font-serif text-lg text-navy-900">FIG. 1 — Daily Harmonised Activity Index (Last 90d)</h3>
                        <span class="text-xs font-mono text-forest-sage">HAI Score</span>
                    </div>
                    <div class="h-72 relative">
                        <canvas id="chartDailyTimeSeries"></canvas>
                    </div>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="font-serif text-lg text-navy-900">FIG. 2 — MODIS vs. VIIRS Sensor Asymmetry</h3>
                        <span class="text-xs font-mono text-forest-sage">Monthly Detections</span>
                    </div>
                    <div class="h-72 relative">
                        <canvas id="chartSensorComparison"></canvas>
                    </div>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="font-serif text-lg text-navy-900">FIG. 3 — Fire Radiative Power (FRP) Distribution</h3>
                        <span class="text-xs font-mono text-forest-sage">Megawatts (MW)</span>
                    </div>
                    <div class="h-72 relative">
                        <canvas id="chartFRP"></canvas>
                    </div>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="font-serif text-lg text-navy-900">FIG. 4 — Weekly Mean HAI & Baseline Z-Score</h3>
                        <span class="text-xs font-mono text-fire-orange">ISO Weekly Series</span>
                    </div>
                    <div class="h-72 relative">
                        <canvas id="chartAnomalies"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- TAB 05: HARMONISATION & AUDIT (READ-ONLY BACKEND REPORT + CSV EXPORT) -->
        <section id="view-harmonisation" class="hidden p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="border-b border-paper-200 pb-6">
                <span class="text-xs font-mono text-fire-orange uppercase tracking-wider block mb-1">Data Engineering Pipeline</span>
                <h2 class="font-serif text-3xl md:text-4xl text-navy-900">Data Harmonisation & Provenance Audit</h2>
                <p class="text-sm text-forest-sage mt-1 font-light max-w-2xl">
                    Verified accounting from the EmberWatch backend pipeline (`audit.json` & `harmonised_fires.csv`). Every raw FIRMS record is either accepted with full provenance or quarantined with explicit reason codes—zero silent discards.
                </p>
            </div>

            <!-- Pipeline Visual Workflow -->
            <div class="bg-white border border-paper-200 p-6 space-y-6">
                <h3 class="font-serif text-xl text-navy-900">Pipeline Execution Architecture</h3>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">01. Ingestion & SHA-256</span>
                        <p class="text-forest-sage font-sans text-xs">Raw FIRMS CSVs stored byte-for-byte with SHA-256 checksum verification in SQLite.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">02. Schema & Quarantine</span>
                        <p class="text-forest-sage font-sans text-xs">Validates lat/lon, normalises UTC timestamps, and quarantines malformed rows transparently.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">03. Spatial Grid Alignment</span>
                        <p class="text-forest-sage font-sans text-xs">Maps MODIS (1 km) & VIIRS (375 m) detections onto 0.05°, 0.10°, and 0.25° common grid cells.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">04. Derived Exports</span>
                        <p class="text-forest-sage font-sans text-xs">Computes Harmonised Activity Index (HAI), baseline departures, and read-only JSON/CSV artifacts.</p>
                    </div>
                </div>
            </div>

            <!-- Live Backend Audit Report -->
            <div class="bg-white border border-paper-200 p-6 space-y-6">
                <div class="flex flex-col sm:flex-row justify-between sm:items-center border-b border-paper-200 pb-3 gap-2">
                    <h3 class="font-serif text-xl text-navy-900">Backend Data Quality Audit Report</h3>
                    <span id="audit-status" class="font-mono text-xs bg-paper-100 px-2.5 py-1 text-navy-900">Pipeline Verified</span>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
                    <div class="p-4 bg-paper-50 border border-paper-200">
                        <span class="text-forest-sage block">Raw Records Loaded</span>
                        <span id="audit-raw" class="text-2xl font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200">
                        <span class="text-forest-sage block">Cleaned Records Retained</span>
                        <span id="audit-clean" class="text-2xl font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200">
                        <span class="text-forest-sage block">Quarantined Records</span>
                        <span id="audit-quarantined" class="text-2xl font-serif text-navy-900 font-medium">—</span>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200">
                        <span class="text-forest-sage block">Silent Discards</span>
                        <span id="audit-silent" class="text-2xl font-serif text-fire-orange font-medium">0</span>
                    </div>
                </div>
                <div class="space-y-2 pt-2 font-mono text-xs">
                    <div class="flex justify-between py-1.5 border-b border-paper-100">
                        <span class="text-forest-sage">Retained with QC Flags</span>
                        <span id="audit-qc" class="font-medium text-navy-900">—</span>
                    </div>
                    <div class="flex justify-between py-1.5 border-b border-paper-100">
                        <span class="text-forest-sage">Invalid Coordinate Records Quarantined</span>
                        <span id="audit-invalid-coord" class="font-medium text-navy-900">—</span>
                    </div>
                    <div class="flex justify-between py-1.5 border-b border-paper-100">
                        <span class="text-forest-sage">Exact Duplicates Skipped</span>
                        <span id="audit-dupes" class="font-medium text-navy-900">—</span>
                    </div>
                    <div class="flex justify-between py-1.5 border-b border-paper-100">
                        <span class="text-forest-sage">Cross-Sensor Proximity Links (Analysis Only)</span>
                        <span id="audit-links" class="font-medium text-navy-900">—</span>
                    </div>
                    <div class="flex justify-between py-1.5">
                        <span class="text-forest-sage">Accounting Reconciled</span>
                        <span id="audit-reconciled" class="font-medium text-navy-900">—</span>
                    </div>
                </div>
                <button onclick="downloadCleanedCSV()" class="w-full bg-navy-900 text-white py-3 font-mono text-xs hover:bg-navy-800 transition-colors">
                    Download Harmonised Observations CSV (Last 30 Days)
                </button>
            </div>
        </section>

        <!-- TAB 06: METHODOLOGY -->
        <section id="view-methodology" class="hidden p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="border-b border-paper-200 pb-6">
                <span class="text-xs font-mono text-fire-orange uppercase tracking-wider block mb-1">Scientific Documentation</span>
                <h2 class="font-serif text-3xl md:text-4xl text-navy-900">Methodology & Sensor Specifications</h2>
                <p class="text-sm text-forest-sage mt-1 font-light max-w-xl">
                    Comprehensive technical documentation detailing sensor physics, spatial resolution weighting, confidence non-equivalence, and mathematical harmonisation.
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Sensor Physics</span>
                    <h3 class="font-serif text-xl text-navy-900">MODIS vs. VIIRS Architecture</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        MODIS (Terra and Aqua) provides daily thermal anomalies at a nominal nadir spatial resolution of 1 km. VIIRS (NOAA-20, NOAA-21, and historical Suomi-NPP) delivers enhanced fire detection at 375 m resolution, capturing smaller smouldering peat fires and agricultural residue burning that MODIS frequently omits.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Spatial Harmonisation</span>
                    <h3 class="font-serif text-xl text-navy-900">Common Grid Aggregation</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        Directly summing MODIS and VIIRS raw point detections creates statistical bias due to VIIRS's higher sensitivity and smaller pixel footprint. EmberWatch maps all detections to equitable 0.05°, 0.10°, and 0.25° latitude/longitude spatial grids, scoring days by Occupied Common Grid Cells and Harmonised Activity Index (HAI).
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Confidence & FRP</span>
                    <h3 class="font-serif text-xl text-navy-900">Thermal Radiative Power</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        Fire Radiative Power (FRP) is measured in megawatts (MW) and estimates the rate of radiant heat release. MODIS confidence ranges from 0% to 100%, whereas VIIRS utilises categorical confidence levels (Low, Nominal, High). EmberWatch preserves raw values while deriving a unified display tier.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Limitations & Disclaimer</span>
                    <h3 class="font-serif text-xl text-navy-900">Thermal Anomalies vs. Wildfires</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        A hotspot represents a satellite-detected thermal anomaly (e.g., agricultural burning, peatland fire, gas flares, or industrial heat) and is not automatically a confirmed wildfire. Users should examine FRP, persistence across days, and baseline departures together.
                    </p>
                </div>
            </div>
        </section>

    </main>

    <!-- Application JavaScript Wired to Backend Payload -->
    <script>
        const PAYLOAD = __PAYLOAD_JSON__;

        const REGION_META = {
            sea: { label: 'Maritime Southeast Asia (1.5°N, 108.2°E)', center: [1.5, 108.2], zoom: 5 },
            johor: { label: 'Peninsular Malaysia & Johor (2.5°N, 102.5°E)', center: [2.5, 102.5], zoom: 7 },
            sumatra: { label: 'Sumatra & Riau Peatlands (0.5°S, 101.5°E)', center: [-0.5, 101.5], zoom: 6 },
            borneo: { label: 'Kalimantan & Borneo (1.0°S, 114.0°E)', center: [-1.0, 114.0], zoom: 6 }
        };

        let currentRegion = 'sea';
        let leafletMap = null;
        let modisLayerGroup = L.layerGroup();
        let viirsLayerGroup = L.layerGroup();
        let gridLayerGroup = L.layerGroup();
        let charts = {};

        function switchTab(tabId) {
            const tabs = ['overview', 'map', 'calendar', 'analytics', 'harmonisation', 'methodology'];
            tabs.forEach(t => {
                const el = document.getElementById('view-' + t);
                const nav = document.getElementById('nav-' + t);
                if (t === tabId) {
                    el.classList.remove('hidden');
                    if (nav) nav.className = 'px-3 py-1.5 transition-colors bg-navy-800 text-white border-b-2 border-fire-orange';
                    if (t === 'map' && leafletMap) {
                        setTimeout(() => { leafletMap.invalidateSize(); }, 150);
                    }
                } else {
                    el.classList.add('hidden');
                    if (nav) nav.className = 'px-3 py-1.5 transition-colors text-paper-200 hover:text-white';
                }
            });
        }

        function getRegionBundle() {
            return PAYLOAD.regions[currentRegion] || PAYLOAD.regions['sea'] || {};
        }

        function updateRegion() {
            currentRegion = document.getElementById('region-selector').value;
            const bundle = getRegionBundle();
            const ov = bundle.overview || {};
            const meta = ov.meta || {};
            const rMeta = REGION_META[currentRegion] || REGION_META.sea;

            document.getElementById('overview-region-badge').innerText = rMeta.label;
            document.getElementById('stat-modis').innerText = (ov.modis_detections ?? 0).toLocaleString();
            document.getElementById('stat-viirs').innerText = (ov.viirs_detections ?? 0).toLocaleString();
            document.getElementById('stat-grid').innerText = `${(ov.occupied_cells_0_10deg ?? 0).toLocaleString()} Active Cells (0.10°)`;
            document.getElementById('stat-latest-acq').innerText = ov.latest_acquisition_utc ? ov.latest_acquisition_utc.replace('T', ' ').replace('Z', ' UTC') : 'No records';
            document.getElementById('stat-data-mode').innerText = meta.is_synthetic ? 'Synthetic Demo Mode' : 'Live NASA FIRMS';

            if (leafletMap) {
                leafletMap.setView(rMeta.center, rMeta.zoom);
                filterMapData();
            }
            populateYearSelector();
            renderCalendar();
            updateCharts();
        }

        function initMap() {
            if (leafletMap) return;
            const rMeta = REGION_META[currentRegion];
            leafletMap = L.map('leaflet-map').setView(rMeta.center, rMeta.zoom);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }).addTo(leafletMap);

            modisLayerGroup.addTo(leafletMap);
            viirsLayerGroup.addTo(leafletMap);
            gridLayerGroup.addTo(leafletMap);
            filterMapData();
        }

        function filterMapData() {
            if (!leafletMap) return;
            const bundle = getRegionBundle();
            const hsPayload = bundle.hotspots || {};
            const allHotspots = hsPayload.hotspots || [];
            const period = (hsPayload.meta && hsPayload.meta.period) || {};
            if (period.from && period.to) {
                document.getElementById('map-period-label').innerText = `Window: ${period.from} to ${period.to} UTC`;
            }

            const confFilter = document.getElementById('filter-confidence').value;
            const minFrp = parseFloat(document.getElementById('filter-frp').value) || 0;
            document.getElementById('frp-val').innerText = `${minFrp}+ MW`;

            modisLayerGroup.clearLayers();
            viirsLayerGroup.clearLayers();
            gridLayerGroup.clearLayers();

            const occupiedCells = new Set();
            let visibleCount = 0;

            allHotspots.forEach(h => {
                const frp = h.frp ?? 0;
                if (frp < minFrp) return;

                const tier = (h.confidence_class_derived || '').toLowerCase();
                if (confFilter === 'high' && tier !== 'high') return;
                if (confFilter === 'nominal' && tier !== 'high' && tier !== 'nominal') return;

                visibleCount++;
                const cellLat = Math.floor((h.lat + 90.0) / 0.10) * 0.10 - 90.0;
                const cellLng = Math.floor((h.lng + 180.0) / 0.10) * 0.10 - 180.0;
                occupiedCells.add(`${cellLat.toFixed(2)},${cellLng.toFixed(2)}`);

                let marker;
                if (h.sensor === 'MODIS') {
                    const icon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: #C85624; width: 10px; height: 10px; border: 1px solid #ffffff;"></div>`,
                        iconSize: [10, 10],
                        iconAnchor: [5, 5]
                    });
                    marker = L.marker([h.lat, h.lng], { icon });
                    modisLayerGroup.addLayer(marker);
                } else {
                    const icon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: #C98E2B; width: 7px; height: 7px; border-radius: 50%; border: 1px solid #ffffff;"></div>`,
                        iconSize: [7, 7],
                        iconAnchor: [3.5, 3.5]
                    });
                    marker = L.marker([h.lat, h.lng], { icon });
                    viirsLayerGroup.addLayer(marker);
                }

                marker.on('click', () => {
                    document.getElementById('selected-hotspot-panel').innerHTML = `
                        <span class="text-forest-sage uppercase tracking-wider block font-bold">Hotspot Telemetry</span>
                        <div class="space-y-1 mt-2 text-navy-900">
                            <div><strong class="text-forest-sage">Sensor:</strong> ${h.sensor} (${h.satellite || 'n/a'})</div>
                            <div><strong class="text-forest-sage">Product:</strong> ${h.source_product || 'n/a'}</div>
                            <div><strong class="text-forest-sage">Coordinates:</strong> ${Number(h.lat).toFixed(4)}, ${Number(h.lng).toFixed(4)}</div>
                            <div><strong class="text-forest-sage">Acquisition:</strong> ${h.date} UTC</div>
                            <div><strong class="text-forest-sage">Confidence:</strong> ${h.confidence}</div>
                            <div><strong class="text-forest-sage">FRP:</strong> ${h.frp !== null ? h.frp + ' MW' : 'n/a'}</div>
                            <div><strong class="text-forest-sage">Brightness:</strong> ${h.brightness !== null ? h.brightness + ' K' : 'n/a'}</div>
                        </div>
                    `;
                });
            });

            occupiedCells.forEach(key => {
                const [cLat, cLng] = key.split(',').map(Number);
                const rect = L.rectangle([[cLat, cLng], [cLat + 0.10, cLng + 0.10]], {
                    color: '#5A7265',
                    weight: 1,
                    fillOpacity: 0.08
                });
                gridLayerGroup.addLayer(rect);
            });

            document.getElementById('map-visible-count').innerText = visibleCount.toLocaleString();
        }

        function toggleLayers() {
            if (!leafletMap) return;
            document.getElementById('layer-modis').checked ? leafletMap.addLayer(modisLayerGroup) : leafletMap.removeLayer(modisLayerGroup);
            document.getElementById('layer-viirs').checked ? leafletMap.addLayer(viirsLayerGroup) : leafletMap.removeLayer(viirsLayerGroup);
            document.getElementById('layer-grid').checked ? leafletMap.addLayer(gridLayerGroup) : leafletMap.removeLayer(gridLayerGroup);
        }

        function getCalendarDaysMap() {
            const bundle = getRegionBundle();
            const res = document.getElementById('cal-res-select').value;
            const calObj = bundle[`calendar_${res}`] || bundle['calendar_0.10'] || {};
            return calObj.days || {};
        }

        function populateYearSelector() {
            const daysMap = getCalendarDaysMap();
            const yearsSet = new Set();
            Object.keys(daysMap).forEach(d => yearsSet.add(d.slice(0, 4)));
            if (yearsSet.size === 0) yearsSet.add('2026');
            const years = Array.from(yearsSet).sort().reverse();

            const sel = document.getElementById('cal-year-select');
            const prev = sel.value;
            sel.innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');
            if (years.includes(prev)) sel.value = prev;
        }

        function renderCalendar() {
            const container = document.getElementById('calendar-months-container');
            container.innerHTML = '';
            const daysMap = getCalendarDaysMap();
            const year = document.getElementById('cal-year-select').value || '2026';
            const metric = document.getElementById('cal-metric').value;

            document.getElementById('calendar-title').innerText = `January – December ${year} Burning Heatmap`;

            let maxVal = 0;
            Object.entries(daysMap).forEach(([dstr, info]) => {
                if (dstr.startsWith(year) && info.data_covered) {
                    const v = Number(info[metric]) || 0;
                    if (v > maxVal) maxVal = v;
                }
            });

            const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            let latestCoveredDate = null;

            months.forEach((m, idx) => {
                const mm = String(idx + 1).padStart(2, '0');
                const yrNum = Number(year);
                const isLeap = (yrNum % 4 === 0 && yrNum % 100 !== 0) || (yrNum % 400 === 0);
                const daysInMonth = (idx === 1) ? (isLeap ? 29 : 28) : ([3, 5, 8, 10].includes(idx) ? 30 : 31);

                let html = `<div class="bg-paper-50 border border-paper-200 p-3 space-y-2">
                    <span class="font-mono text-xs font-bold text-navy-900 block border-b border-paper-200 pb-1">${m}</span>
                    <div class="grid grid-cols-7 gap-1 text-[9px] font-mono text-center">`;

                for (let d = 1; d <= daysInMonth; d++) {
                    const dd = String(d).padStart(2, '0');
                    const isoDate = `${year}-${mm}-${dd}`;
                    const info = daysMap[isoDate];

                    let color = 'bg-paper-100 text-forest-sage/60';
                    let title = `${isoDate}: Not covered`;

                    if (info && info.data_covered) {
                        latestCoveredDate = isoDate;
                        const val = Number(info[metric]) || 0;
                        const ratio = maxVal > 0 ? val / maxVal : 0;
                        if (val === 0) color = 'bg-paper-100 text-navy-900 border border-paper-200';
                        else if (ratio > 0.75) color = 'bg-[#9E2A22] text-white font-bold';
                        else if (ratio > 0.40) color = 'bg-[#C85624] text-white';
                        else color = 'bg-[#C98E2B] text-white';
                        title = `${isoDate} | HAI: ${info.hai ?? 'n/a'} | Cells: ${info.grid} | VIIRS: ${info.viirs} | MODIS: ${info.modis}`;
                    }

                    html += `<div onclick="selectCalendarDay('${isoDate}')" class="${color} p-1 cursor-pointer transition-transform hover:scale-110" title="${title}">${d}</div>`;
                }
                html += `</div></div>`;
                container.innerHTML += html;
            });

            if (latestCoveredDate) {
                selectCalendarDay(latestCoveredDate);
            }
        }

        function selectCalendarDay(isoDate) {
            const daysMap = getCalendarDaysMap();
            const info = daysMap[isoDate];
            document.getElementById('dossier-date-title').innerText = `Selected Date: ${isoDate} (UTC)`;

            if (!info || !info.data_covered) {
                document.getElementById('dossier-status').innerText = 'No Data Coverage';
                document.getElementById('dossier-hai').innerText = '—';
                document.getElementById('dossier-grid').innerText = '—';
                document.getElementById('dossier-modis').innerText = '—';
                document.getElementById('dossier-viirs').innerText = '—';
                document.getElementById('dossier-frp').innerText = '—';
                return;
            }

            const dep = info.baseline_departure_pct;
            document.getElementById('dossier-status').innerText = (dep !== null && dep !== undefined)
                ? `Baseline Departure: ${dep >= 0 ? '+' : ''}${dep}% (${info.baseline_years} yr baseline)`
                : 'Baseline Departure: Insufficient prior-year history';

            document.getElementById('dossier-hai').innerText = info.hai !== null ? info.hai : 'n/a';
            document.getElementById('dossier-grid').innerText = info.grid ?? 0;
            document.getElementById('dossier-modis').innerText = info.modis ?? 0;
            document.getElementById('dossier-viirs').innerText = info.viirs ?? 0;
            document.getElementById('dossier-frp').innerText = info.mean_frp_mw !== null ? `${info.mean_frp_mw} MW` : 'n/a';
        }

        function updateCharts() {
            const bundle = getRegionBundle();
            const an = bundle.analytics || {};

            Object.values(charts).forEach(c => c.destroy());
            charts = {};

            const daily = an.daily_series_last_90d || [];
            charts.daily = new Chart(document.getElementById('chartDailyTimeSeries').getContext('2d'), {
                type: 'line',
                data: {
                    labels: daily.map(d => d.date),
                    datasets: [{
                        label: 'Harmonised Activity Index',
                        data: daily.map(d => d.hai),
                        borderColor: '#C85624',
                        backgroundColor: 'rgba(200, 86, 36, 0.1)',
                        fill: true,
                        tension: 0.2,
                        borderWidth: 2
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            const monthly = an.monthly_sensor_comparison || [];
            charts.sensor = new Chart(document.getElementById('chartSensorComparison').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: monthly.map(m => m.month),
                    datasets: [
                        { label: 'MODIS (1km)', data: monthly.map(m => m.modis), backgroundColor: '#13262E' },
                        { label: 'VIIRS (375m)', data: monthly.map(m => m.viirs), backgroundColor: '#C98E2B' }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            const frp = an.frp_distribution || [];
            charts.frp = new Chart(document.getElementById('chartFRP').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: frp.map(b => b.bin ? b.bin + ' MW' : ''),
                    datasets: [{
                        label: 'Detection Frequency',
                        data: frp.map(b => b.count ?? 0),
                        backgroundColor: '#5A7265'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            const weekly = (an.weekly_anomalies || []).slice(-26);
            charts.anomalies = new Chart(document.getElementById('chartAnomalies').getContext('2d'), {
                type: 'line',
                data: {
                    labels: weekly.map(w => `${w.iso_year}-W${String(w.iso_week).padStart(2, '0')}`),
                    datasets: [{
                        label: 'Weekly Mean HAI',
                        data: weekly.map(w => w.mean_hai),
                        borderColor: '#9E2A22',
                        borderWidth: 2,
                        tension: 0.2
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        function populateAuditReport() {
            const audit = PAYLOAD.audit || {};
            const meta = audit.meta || {};

            if (meta.is_synthetic && meta.banner) {
                const bannerEl = document.getElementById('data-mode-banner');
                bannerEl.innerText = meta.banner + ' — Add FIRMS_MAP_KEY to fetch live NASA satellite telemetry.';
                bannerEl.classList.remove('hidden');
            }

            document.getElementById('audit-raw').innerText = (audit.raw_records_loaded ?? 0).toLocaleString();
            document.getElementById('audit-clean').innerText = (audit.cleaned_records_retained ?? 0).toLocaleString();
            document.getElementById('audit-quarantined').innerText = (audit.quarantined_records ?? 0).toLocaleString();
            document.getElementById('audit-silent').innerText = (audit.silent_discards ?? 0).toLocaleString();
            document.getElementById('audit-qc').innerText = (audit.retained_with_qc_flags ?? 0).toLocaleString();
            document.getElementById('audit-invalid-coord').innerText = (audit.invalid_coordinate_records ?? 0).toLocaleString();
            document.getElementById('audit-dupes').innerText = (audit.exact_duplicates_not_inserted ?? 0).toLocaleString();
            document.getElementById('audit-links').innerText = (audit.cross_sensor_proximity_links ?? 0).toLocaleString();
            document.getElementById('audit-reconciled').innerText = audit.reconciled ? 'Yes (100% Accounted)' : 'Check Logs';
        }

        function downloadCleanedCSV() {
            if (!PAYLOAD.csv_text) {
                alert('No harmonised CSV export found yet.');
                return;
            }
            const blob = new Blob([PAYLOAD.csv_text], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.setAttribute('href', url);
            link.setAttribute('download', 'emberwatch_harmonised_fires.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }

        window.addEventListener('DOMContentLoaded', () => {
            populateAuditReport();
            updateRegion();
            initMap();
        });
    </script>
</body>
</html>
"""

rendered_html = EMBERWATCH_HTML.replace("__PAYLOAD_JSON__", payload_json)
components.html(rendered_html, height=950, scrolling=True)

audit_meta = payload.get("audit", {}).get("meta", {})
mode_label = (
    "Synthetic Demo"
    if audit_meta.get("is_synthetic")
    else "Live NASA FIRMS"
)

st.markdown("---")
st.markdown("### 🔥 EmberWatch System Status")
col1, col2, col3 = st.columns(3)
col1.metric("Satellite Platforms", "5", "Terra, Aqua, NOAA-20, NOAA-21, S-NPP")
col2.metric("Data Mode", mode_label, "Operational")
col3.metric("Monitoring Regions", "4", "SE Asia, Johor, Sumatra, Borneo")
st.caption("Developed for NASA Space Apps Challenge 2026.")
st.caption("Data reference: NASA FIRMS | MODIS | VIIRS")
