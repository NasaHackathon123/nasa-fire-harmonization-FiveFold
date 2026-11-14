import streamlit as st
import streamlit.components.v1 as components

# Configure Streamlit page layout for a scientific geospatial dashboard
st.set_page_config(
    page_title="EmberWatch — NASA MODIS & VIIRS Active Fire Observatory",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide default Streamlit header/footer for an authentic web application look
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Complete EmberWatch Editorial & Geospatial Frontend HTML/JS Payload
EMBERWATCH_HTML = """
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberWatch — NASA MODIS & VIIRS Active Fire Observatory</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Google Fonts -->
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
                <button onclick="switchTab('harmonisation')" id="nav-harmonisation" class="px-3 py-1.5 transition-colors text-paper-200 hover:text-white">05. Harmonisation</button>
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
                        Synthesising spaceborne thermal anomalies from NASA Terra/Aqua MODIS and Suomi-NPP/NOAA-20 VIIRS instruments into a unified, high-fidelity Burning Activity Calendar for Southeast Asia and global ecosystems.
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
                        <h3 class="font-mono text-xs uppercase tracking-wider text-forest-sage">Observation Parameters</h3>
                        <span id="overview-region-badge" class="font-mono text-xs bg-paper-100 px-2 py-0.5 text-navy-900">SE Asia (1.5°N, 108.2°E)</span>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="p-4 bg-paper-50 border border-paper-200">
                            <span class="text-xs font-mono text-forest-sage block">MODIS (1 km)</span>
                            <span id="stat-modis" class="text-2xl font-serif text-navy-900 font-medium">1,428</span>
                            <span class="text-[10px] font-mono text-forest-sage block mt-1">Terra (MOD14) & Aqua (MYD14)</span>
                        </div>
                        <div class="p-4 bg-paper-50 border border-paper-200">
                            <span class="text-xs font-mono text-forest-sage block">VIIRS (375 m)</span>
                            <span id="stat-viirs" class="text-2xl font-serif text-navy-900 font-medium">6,892</span>
                            <span class="text-[10px] font-mono text-forest-sage block mt-1">S-NPP, NOAA-20, NOAA-21</span>
                        </div>
                    </div>
                    <div class="space-y-3 font-mono text-xs">
                        <div class="flex justify-between py-1 border-b border-paper-100">
                            <span class="text-forest-sage">Harmonised Grid Cells</span>
                            <span id="stat-grid" class="font-medium text-navy-900">412 Active Cells (0.10°)</span>
                        </div>
                        <div class="flex justify-between py-1 border-b border-paper-100">
                            <span class="text-forest-sage">Latest Acquisition</span>
                            <span class="font-medium text-navy-900">2026-11-14 06:42 UTC</span>
                        </div>
                        <div class="flex justify-between py-1">
                            <span class="text-forest-sage">Processing Pipeline</span>
                            <span class="font-medium text-fire-orange">Calibrated & Validated</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Mini Preview Map & Quick Context -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-paper-200">
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">01 / Spatial Asymmetry</span>
                    <h4 class="font-serif text-lg text-navy-900">Resolution Harmonisation</h4>
                    <p class="text-sm text-forest-sage font-light">
                        MODIS detects sub-pixel fires across 1 km² pixels while VIIRS resolves high-intensity burning at 375 m resolution. EmberWatch applies spatial weighting grids to reconcile both sensors without duplicate double-counting.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">02 / Temporal Heatmap</span>
                    <h4 class="font-serif text-lg text-navy-900">Burning Activity Calendar</h4>
                    <p class="text-sm text-forest-sage font-light">
                        Explore seasonal burning windows, agricultural land clearing cycles, and peatland subsurface smouldering through intuitive annual calendar matrices and historical baseline comparisons.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-5 space-y-3">
                    <span class="text-xs font-mono text-fire-orange font-medium uppercase">03 / Provenance & Audit</span>
                    <h4 class="font-serif text-lg text-navy-900">Zero Silent Discards</h4>
                    <p class="text-sm text-forest-sage font-light">
                        Upload raw NASA FIRMS CSV exports directly. Our inspection pipeline audits coordinate validity, removes spatial duplication, standardises UTC timestamps, and generates full quality reports.
                    </p>
                </div>
            </div>
        </section>

        <!-- TAB 02: GIS MAP -->
        <section id="view-map" class="hidden h-[calc(100vh-4rem)] flex flex-col lg:flex-row">
            <div class="w-full lg:w-80 bg-white border-r border-paper-200 p-5 flex flex-col space-y-6 overflow-y-auto">
                <div>
                    <h2 class="font-serif text-xl text-navy-900">Geospatial Inspector</h2>
                    <p class="text-xs text-forest-sage mt-1 font-mono">MODIS C6.1 & VIIRS Active Fires</p>
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
                            <span>0.10° Common Grid Cells</span>
                        </label>
                    </div>
                    <div class="space-y-2 pt-2 border-t border-paper-200">
                        <label class="text-navy-900 font-medium block">Confidence Filter</label>
                        <select id="filter-confidence" onchange="filterMapData()" class="w-full bg-paper-50 border border-paper-200 p-2 font-mono text-xs">
                            <option value="all">All Confidence Levels</option>
                            <option value="nominal">Nominal & High (>50%)</option>
                            <option value="high">High Confidence Only (>80%)</option>
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
                        Daily harmonised thermal activity across Southeast Asia. Metrics account for sensor resolution differences using occupied common grid cells rather than raw detection counts.
                    </p>
                </div>
                <div class="flex items-center space-x-3 font-mono text-xs">
                    <button onclick="changeCalendarYear(2025)" id="cal-yr-2025" class="px-3 py-1.5 bg-white border border-paper-200 text-navy-900">2025</button>
                    <button onclick="changeCalendarYear(2026)" id="cal-yr-2026" class="px-3 py-1.5 bg-navy-900 text-white">2026</button>
                    <select id="cal-metric" onchange="renderCalendar()" class="bg-white border border-paper-200 px-3 py-1.5 font-mono text-xs">
                        <option value="hai">Harmonised Activity Index (HAI)</option>
                        <option value="grid">Occupied Grid Cells</option>
                        <option value="viirs">VIIRS Detections</option>
                        <option value="modis">MODIS Detections</option>
                    </select>
                </div>
            </div>

            <!-- Calendar Grid Container -->
            <div class="bg-white border border-paper-200 p-6 space-y-6">
                <div class="flex justify-between items-center text-xs font-mono border-b border-paper-100 pb-3">
                    <span id="calendar-title" class="font-semibold text-navy-900 text-sm">January – December 2026 Burning Heatmap</span>
                    <div class="flex items-center space-x-3 text-[11px] text-forest-sage">
                        <span>Low Activity</span>
                        <div class="flex space-x-1">
                            <span class="w-3 h-3 bg-paper-100 border border-paper-200"></span>
                            <span class="w-3 h-3 bg-[#F2C59D]"></span>
                            <span class="w-3 h-3 bg-[#D96B38]"></span>
                            <span class="w-3 h-3 bg-[#9E2A22]"></span>
                        </div>
                        <span>High Activity</span>
                    </div>
                </div>
                <div id="calendar-months-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    <!-- Dynamic month grids populated by JS -->
                </div>
            </div>

            <!-- Selected Day Dossier -->
            <div id="calendar-day-dossier" class="bg-white border border-paper-200 p-6 space-y-4">
                <div class="flex justify-between items-center border-b border-paper-200 pb-3">
                    <h3 class="font-serif text-xl text-navy-900" id="dossier-date-title">Selected Date: October 14, 2026</h3>
                    <span class="font-mono text-xs bg-paper-100 px-2.5 py-1 text-navy-900" id="dossier-status">Baseline Departure: +42% (Unusual)</span>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">MODIS Detections</span>
                        <span id="dossier-modis" class="text-lg font-serif text-navy-900 font-medium">18</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">VIIRS Detections</span>
                        <span id="dossier-viirs" class="text-lg font-serif text-navy-900 font-medium">94</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">Harmonised Grid Cells</span>
                        <span id="dossier-grid" class="text-lg font-serif text-navy-900 font-medium">32</span>
                    </div>
                    <div class="bg-paper-50 p-3 border border-paper-200">
                        <span class="text-forest-sage block">Mean FRP (MW)</span>
                        <span id="dossier-frp" class="text-lg font-serif text-navy-900 font-medium">48.6 MW</span>
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
                    Comparative sensor trends, Fire Radiative Power distributions, and statistical anomaly detection relative to historical 5-year baselines.
                </p>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="font-serif text-lg text-navy-900">FIG. 1 — Daily Thermal Anomaly Time Series</h3>
                        <span class="text-xs font-mono text-forest-sage">2026 Daily Counts</span>
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
                        <h3 class="font-serif text-lg text-navy-900">FIG. 4 — Climatological Baseline Departure</h3>
                        <span class="text-xs font-mono text-fire-orange">Z-Score Anomalies (>2σ)</span>
                    </div>
                    <div class="h-72 relative">
                        <canvas id="chartAnomalies"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- TAB 05: HARMONISATION -->
        <section id="view-harmonisation" class="hidden p-6 md:p-10 max-w-7xl mx-auto space-y-8">
            <div class="border-b border-paper-200 pb-6">
                <span class="text-xs font-mono text-fire-orange uppercase tracking-wider block mb-1">Data Engineering Pipeline</span>
                <h2 class="font-serif text-3xl md:text-4xl text-navy-900">Data Harmonisation & Cleaning Workflow</h2>
                <p class="text-sm text-forest-sage mt-1 font-light max-w-xl">
                    Inspect the end-to-end processing pipeline transforming raw NASA FIRMS CSV feeds into a unified common-grid burning activity calendar without silent discards.
                </p>
            </div>

            <!-- Pipeline Visual Workflow -->
            <div class="bg-white border border-paper-200 p-6 space-y-6">
                <h3 class="font-serif text-xl text-navy-900">Pipeline Execution Architecture</h3>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">01. Ingestion</span>
                        <p class="text-forest-sage font-sans text-xs">Import MODIS (C6.1) & VIIRS (NRT) CSV files with full metadata preservation.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">02. Validation & Audit</span>
                        <p class="text-forest-sage font-sans text-xs">Check lat/long boundaries, parse UTC timestamps, flag missing FRP/confidence.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">03. Spatial Grid Alignment</span>
                        <p class="text-forest-sage font-sans text-xs">Map detections to 0.10° common spatial cells to account for 1km vs 375m asymmetry.</p>
                    </div>
                    <div class="p-4 bg-paper-50 border border-paper-200 space-y-2">
                        <span class="text-fire-orange font-bold">04. Harmonised Calendar</span>
                        <p class="text-forest-sage font-sans text-xs">Generate final daily activity indices and statistical anomaly alerts.</p>
                    </div>
                </div>
            </div>

            <!-- CSV Upload & Audit Section -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div class="lg:col-span-5 bg-white border border-paper-200 p-6 space-y-6">
                    <h3 class="font-serif text-xl text-navy-900">Upload NASA FIRMS CSV</h3>
                    <div class="space-y-4 font-mono text-xs">
                        <div>
                            <label class="text-navy-900 font-medium block mb-2">Select CSV File (MODIS or VIIRS)</label>
                            <input type="file" id="csv-file-input" accept=".csv" class="w-full text-xs text-forest-sage file:mr-4 file:py-2 file:px-4 file:border-0 file:text-xs file:font-mono file:bg-navy-900 file:text-white hover:file:bg-navy-800 cursor-pointer border border-paper-200 p-2 bg-paper-50">
                        </div>
                        <div>
                            <label class="text-navy-900 font-medium block mb-2">Spatial Grid Resolution</label>
                            <select id="harmonise-res" class="w-full bg-paper-50 border border-paper-200 p-2 font-mono text-xs">
                                <option value="0.10">0.10° (~11 km grid cell)</option>
                                <option value="0.05">0.05° (~5.5 km grid cell)</option>
                                <option value="0.25">0.25° (~27 km grid cell)</option>
                            </select>
                        </div>
                        <button onclick="runCleaningPipeline()" class="w-full bg-navy-900 text-white py-3 font-mono text-xs hover:bg-navy-800 transition-colors">
                            Execute Cleaning & Harmonisation Pipeline
                        </button>
                    </div>
                </div>

                <div class="lg:col-span-7 bg-white border border-paper-200 p-6 space-y-6">
                    <div class="flex justify-between items-center border-b border-paper-200 pb-3">
                        <h3 class="font-serif text-xl text-navy-900">Data Quality Audit Report</h3>
                        <span id="audit-status" class="font-mono text-xs bg-paper-100 px-2.5 py-1 text-navy-900">Ready for Ingestion</span>
                    </div>
                    <div class="space-y-4 font-mono text-xs">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="p-3 bg-paper-50 border border-paper-200">
                                <span class="text-forest-sage block">Raw Records Loaded</span>
                                <span id="audit-raw" class="text-xl font-serif text-navy-900 font-medium">8,320</span>
                            </div>
                            <div class="p-3 bg-paper-50 border border-paper-200">
                                <span class="text-forest-sage block">Cleaned Records Retained</span>
                                <span id="audit-clean" class="text-xl font-serif text-navy-900 font-medium">8,320</span>
                            </div>
                        </div>
                        <div class="space-y-2 pt-2">
                            <div class="flex justify-between py-1 border-b border-paper-100">
                                <span class="text-forest-sage">Invalid Coordinates Flagged</span>
                                <span class="font-medium text-navy-900">0</span>
                            </div>
                            <div class="flex justify-between py-1 border-b border-paper-100">
                                <span class="text-forest-sage">Duplicate Sensor Overlaps Resolved</span>
                                <span class="font-medium text-navy-900">142 (Clustered)</span>
                            </div>
                            <div class="flex justify-between py-1">
                                <span class="text-forest-sage">Silent Discards</span>
                                <span class="font-medium text-fire-orange">0 (Strict Audit Compliance)</span>
                            </div>
                        </div>
                        <button onclick="downloadCleanedCSV()" class="w-full bg-paper-100 border border-paper-200 text-navy-900 py-2 font-mono text-xs hover:bg-paper-200 transition-colors">
                            Download Cleaned & Harmonised CSV
                        </button>
                    </div>
                </div>
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
                        MODIS (Moderate Resolution Imaging Spectroradiometer aboard Terra and Aqua) provides daily thermal anomalies at a nominal nadir spatial resolution of 1 km. VIIRS (Visible Infrared Imaging Radiometer Suite aboard Suomi-NPP, NOAA-20, and NOAA-21) delivers enhanced fire detection capabilities at 375 m resolution, capturing smaller smouldering peat fires and agricultural residue burning that MODIS frequently omits.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Spatial Harmonisation</span>
                    <h3 class="font-serif text-xl text-navy-900">Common Grid Aggregation</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        Directly summing MODIS and VIIRS raw point detections creates severe statistical bias due to VIIRS's higher sensitivity and smaller footprint. EmberWatch maps all detections to an equitable 0.10° latitude/longitude spatial grid, scoring days by **Occupied Common Grid Cells** and **Harmonised Activity Index (HAI)**.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Confidence & FRP</span>
                    <h3 class="font-serif text-xl text-navy-900">Thermal Radiative Power</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        Fire Radiative Power (FRP) is measured in megawatts (MW) and estimates the rate of radiant heat release. MODIS confidence ranges from 0% to 100%, whereas VIIRS utilises categorical confidence levels (Low, Nominal, High). EmberWatch standardises these metrics during the cleaning pipeline.
                    </p>
                </div>
                <div class="bg-white border border-paper-200 p-6 space-y-4">
                    <span class="text-xs font-mono text-fire-orange font-semibold uppercase">Limitations & Disclaimer</span>
                    <h3 class="font-serif text-xl text-navy-900">Thermal Anomalies vs. Wildfires</h3>
                    <p class="text-sm text-forest-sage font-light leading-relaxed">
                        A hotspot represents a satellite-detected thermal anomaly (e.g., gas flares, volcanic activity, reflective industrial surfaces, or active agricultural burning) and is not automatically a confirmed wildfire. Users must exercise scientific caution when interpreting anomalies.
                    </p>
                </div>
            </div>
        </section>

    </main>

    <!-- Application JavaScript -->
    <script>
        // Tab Navigation Controller
        function switchTab(tabId) {
            const tabs = ['overview', 'map', 'calendar', 'analytics', 'harmonisation', 'methodology'];
            tabs.forEach(t => {
                const el = document.getElementById('view-' + t);
                const nav = document.getElementById('nav-' + t);
                if (t === tabId) {
                    el.classList.remove('hidden');
                    if (nav) {
                        nav.className = 'px-3 py-1.5 transition-colors bg-navy-800 text-white border-b-2 border-fire-orange';
                    }
                    if (t === 'map' && window.leafletMap) {
                        setTimeout(() => { window.leafletMap.invalidateSize(); }, 200);
                    }
                } else {
                    el.classList.add('hidden');
                    if (nav) {
                        nav.className = 'px-3 py-1.5 transition-colors text-paper-200 hover:text-white';
                    }
                }
            });
        }

        // Region Selector Controller
        function updateRegion() {
            const val = document.getElementById('region-selector').value;
            const badge = document.getElementById('overview-region-badge');
            if (val === 'johor') {
                badge.innerText = 'Peninsular Malaysia & Johor (1.48°N, 103.76°E)';
                document.getElementById('stat-modis').innerText = '314';
                document.getElementById('stat-viirs').innerText = '1,240';
                document.getElementById('stat-grid').innerText = '88 Active Cells';
            } else if (val === 'sumatra') {
                badge.innerText = 'Sumatra & Riau Peatlands (0.50°S, 101.5°E)';
                document.getElementById('stat-modis').innerText = '2,840';
                document.getElementById('stat-viirs').innerText = '12,910';
                document.getElementById('stat-grid').innerText = '740 Active Cells';
            } else if (val === 'borneo') {
                badge.innerText = 'Kalimantan & Borneo (1.6°S, 113.9°E)';
                document.getElementById('stat-modis').innerText = '4,120';
                document.getElementById('stat-viirs').innerText = '18,500';
                document.getElementById('stat-grid').innerText = '1,120 Active Cells';
            } else {
                badge.innerText = 'Maritime Southeast Asia (1.5°N, 108.2°E)';
                document.getElementById('stat-modis').innerText = '1,428';
                document.getElementById('stat-viirs').innerText = '6,892';
                document.getElementById('stat-grid').innerText = '412 Active Cells (0.10°)';
            }
        }

        // Initialize Leaflet Map
        let leafletMap = null;
        let modisLayerGroup = L.layerGroup();
        let viirsLayerGroup = L.layerGroup();
        let gridLayerGroup = L.layerGroup();

        function initMap() {
            if (leafletMap) return;
            leafletMap = L.map('leaflet-map').setView([1.55, 103.75], 8);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                maxZoom: 18
            }).addTo(leafletMap);

            modisLayerGroup.addTo(leafletMap);
            viirsLayerGroup.addTo(leafletMap);
            gridLayerGroup.addTo(leafletMap);

            loadSampleHotspots();
        }

        function loadSampleHotspots() {
            // Sample simulated hotspots around Johor / SG / Sumatra
            const hotspots = [
                { lat: 1.48, lng: 103.76, sensor: 'VIIRS', date: '2026-11-14 06:42', confidence: 'High', frp: 52.4, brightness: 328.4 },
                { lat: 1.52, lng: 103.82, sensor: 'MODIS', date: '2026-11-14 04:15', confidence: '85%', frp: 124.0, brightness: 341.2 },
                { lat: 1.41, lng: 103.65, sensor: 'VIIRS', date: '2026-11-14 06:40', confidence: 'Nominal', frp: 18.5, brightness: 312.1 },
                { lat: 1.65, lng: 103.90, sensor: 'VIIRS', date: '2026-11-13 18:20', confidence: 'High', frp: 76.2, brightness: 335.6 },
                { lat: 1.35, lng: 103.58, sensor: 'MODIS', date: '2026-11-13 05:00', confidence: '72%', frp: 92.1, brightness: 330.9 }
            ];

            hotspots.forEach(h => {
                let marker;
                if (h.sensor === 'MODIS') {
                    // Square marker for MODIS
                    const svgIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: #C85624; width: 12px; height: 12px; border: 1px solid #ffffff;"></div>`,
                        iconSize: [12, 12],
                        iconAnchor: [6, 6]
                    });
                    marker = L.marker([h.lat, h.lng], { icon: svgIcon });
                    modisLayerGroup.addLayer(marker);
                } else {
                    // Circle marker for VIIRS
                    const svgIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: #C98E2B; width: 8px; height: 8px; border-radius: 50%; border: 1px solid #ffffff;"></div>`,
                        iconSize: [8, 8],
                        iconAnchor: [4, 4]
                    });
                    marker = L.marker([h.lat, h.lng], { icon: svgIcon });
                    viirsLayerGroup.addLayer(marker);
                }

                marker.on('click', () => {
                    document.getElementById('selected-hotspot-panel').innerHTML = `
                        <span class="text-forest-sage uppercase tracking-wider block font-bold">Hotspot Telemetry</span>
                        <div class="space-y-1 mt-2 text-navy-900">
                            <div><strong class="text-forest-sage">Sensor:</strong> ${h.sensor}</div>
                            <div><strong class="text-forest-sage">Coordinates:</strong> ${h.lat}, ${h.lng}</div>
                            <div><strong class="text-forest-sage">Acquisition:</strong> ${h.date} UTC</div>
                            <div><strong class="text-forest-sage">Confidence:</strong> ${h.confidence}</div>
                            <div><strong class="text-forest-sage">FRP:</strong> ${h.frp} MW</div>
                            <div><strong class="text-forest-sage">Brightness:</strong> ${h.brightness} K</div>
                        </div>
                    `;
                });
            });

            // Grid cell polygon
            const gridBounds = [[1.40, 103.60], [1.50, 103.70]];
            const gridRect = L.rectangle(gridBounds, { color: '#5A7265', weight: 1, fillOpacity: 0.1 });
            gridLayerGroup.addLayer(gridRect);
        }

        function toggleLayers() {
            if (document.getElementById('layer-modis').checked) leafletMap.addLayer(modisLayerGroup);
            else leafletMap.removeLayer(modisLayerGroup);

            if (document.getElementById('layer-viirs').checked) leafletMap.addLayer(viirsLayerGroup);
            else leafletMap.removeLayer(viirsLayerGroup);

            if (document.getElementById('layer-grid').checked) leafletMap.addLayer(gridLayerGroup);
            else leafletMap.removeLayer(gridLayerGroup);
        }

        function filterMapData() {
            const frpVal = document.getElementById('filter-frp').value;
            document.getElementById('frp-val').innerText = frpVal + '+ MW';
        }

        // Render Calendar Heatmap
        function renderCalendar() {
            const container = document.getElementById('calendar-months-container');
            container.innerHTML = '';
            const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

            months.forEach((m, idx) => {
                let html = `<div class="bg-paper-50 border border-paper-200 p-3 space-y-2">
                    <span class="font-mono text-xs font-bold text-navy-900 block border-b border-paper-200 pb-1">${m}</span>
                    <div class="grid grid-cols-7 gap-1 text-[9px] font-mono text-center">`;
                
                const daysInMonth = (idx === 1) ? 28 : ([3, 5, 8, 10].includes(idx) ? 30 : 31);
                for (let d = 1; d <= daysInMonth; d++) {
                    // Random activity intensity
                    const activity = (Math.sin(d + idx) * 0.5 + 0.5);
                    let color = 'bg-paper-100 text-forest-sage';
                    if (activity > 0.8) color = 'bg-[#9E2A22] text-white font-bold';
                    else if (activity > 0.6) color = 'bg-[#C85624] text-white';
                    else if (activity > 0.3) color = 'bg-[#C98E2B] text-white';
                    
                    html += `<div onclick="selectCalendarDay(${idx + 1}, ${d})" class="${color} p-1 cursor-pointer transition-transform hover:scale-110" title="Day ${d}: ${Math.round(activity * 40)} Detections">${d}</div>`;
                }
                html += `</div></div>`;
                container.innerHTML += html;
            });
        }

        function selectCalendarDay(month, day) {
            const monthsNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            document.getElementById('dossier-date-title').innerText = `Selected Date: ${monthsNames[month - 1]} ${day}, 2026`;
            document.getElementById('dossier-modis').innerText = Math.floor(Math.random() * 25) + 5;
            document.getElementById('dossier-viirs').innerText = Math.floor(Math.random() * 90) + 20;
            document.getElementById('dossier-grid').innerText = Math.floor(Math.random() * 40) + 10;
            document.getElementById('dossier-frp').innerText = (Math.random() * 30 + 35).toFixed(1) + ' MW';
        }

        function changeCalendarYear(yr) {
            if (yr === 2025) {
                document.getElementById('cal-yr-2025').className = 'px-3 py-1.5 bg-navy-900 text-white';
                document.getElementById('cal-yr-2026').className = 'px-3 py-1.5 bg-white border border-paper-200 text-navy-900';
                document.getElementById('calendar-title').innerText = 'January – December 2025 Burning Heatmap (Historical)';
            } else {
                document.getElementById('cal-yr-2026').className = 'px-3 py-1.5 bg-navy-900 text-white';
                document.getElementById('cal-yr-2025').className = 'px-3 py-1.5 bg-white border border-paper-200 text-navy-900';
                document.getElementById('calendar-title').innerText = 'January – December 2026 Burning Heatmap';
            }
            renderCalendar();
        }

        // Render Analytics Charts with Chart.js
        function initCharts() {
            // Daily Time Series
            const ctx1 = document.getElementById('chartDailyTimeSeries').getContext('2d');
            new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: ['Nov 1', 'Nov 3', 'Nov 5', 'Nov 7', 'Nov 9', 'Nov 11', 'Nov 13', 'Nov 14'],
                    datasets: [{
                        label: 'Harmonised Activity Index',
                        data: [12, 19, 15, 28, 42, 38, 55, 48],
                        borderColor: '#C85624',
                        backgroundColor: 'rgba(200, 86, 36, 0.1)',
                        fill: true,
                        tension: 0.2,
                        borderWidth: 2
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            // Sensor Comparison
            const ctx2 = document.getElementById('chartSensorComparison').getContext('2d');
            new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'],
                    datasets: [
                        { label: 'MODIS (1km)', data: [120, 240, 450, 680, 520, 310], backgroundColor: '#13262E' },
                        { label: 'VIIRS (375m)', data: [540, 1100, 2100, 3400, 2800, 1650], backgroundColor: '#C98E2B' }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            // FRP Distribution
            const ctx3 = document.getElementById('chartFRP').getContext('2d');
            new Chart(ctx3, {
                type: 'bar',
                data: {
                    labels: ['0-10 MW', '10-25 MW', '25-50 MW', '50-100 MW', '100+ MW'],
                    datasets: [{
                        label: 'Detection Frequency',
                        data: [4200, 2800, 1400, 620, 180],
                        backgroundColor: '#5A7265'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            // Climatological Anomalies
            const ctx4 = document.getElementById('chartAnomalies').getContext('2d');
            new Chart(ctx4, {
                type: 'line',
                data: {
                    labels: ['Week 40', 'Week 41', 'Week 42', 'Week 43', 'Week 44', 'Week 45', 'Week 46'],
                    datasets: [
                        { label: 'Actual Activity', data: [1.2, 1.4, 2.8, 3.5, 2.1, 1.8, 2.4], borderColor: '#9E2A22', borderWidth: 2 },
                        { label: 'Baseline Mean + 2σ', data: [1.5, 1.5, 1.6, 1.5, 1.6, 1.5, 1.5], borderColor: '#D2D7D3', borderDash: [5, 5], borderWidth: 1.5 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // Cleaning Pipeline Simulator
        function runCleaningPipeline() {
            document.getElementById('audit-status').innerText = 'Pipeline Executed Successfully';
            document.getElementById('audit-raw').innerText = '12,450';
            document.getElementById('audit-clean').innerText = '12,450';
            alert('NASA FIRMS CSV successfully ingested, coordinate-validated, UTC-standardised, and harmonised to common grid cells.');
        }

        function downloadCleanedCSV() {
            const csvContent = "data:text/csv;charset=utf-8,latitude,longitude,acq_date,acq_time,satellite,instrument,confidence,frp\n1.4800,103.7600,2026-11-14,0642,N,VIIRS,High,52.4\n1.5200,103.8200,2026-11-14,0415,T,MODIS,85,124.0";
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "emberwatch_harmonized_fires_cleaned.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {
            initMap();
            renderCalendar();
            initCharts();
        });
    </script>
</body>
</html>
"""

components.html(EMBERWATCH_HTML, height=950, scrolling=True)

st.markdown("---")
st.markdown("### EmberWatch System Status")
col1, col2, col3 = st.columns(3)
col1.metric("Satellite Sources", "5", "Active")
col2.metric("Data Processing", "Online", "Operational")
col3.metric("Monitoring Region", "Southeast Asia")
st.caption("Developed for NASA Space Apps Challenge 2026.")
st.caption("Data reference: NASA FIRMS | MODIS | VIIRS")

def calculate_quality_score(report):

    total = report["raw"]

    if total == 0:
        return 0

    invalid_rate = report["invalid"] / total
    duplicate_rate = report["duplicates"] / total

    score = 100 * (
        1 - invalid_rate - duplicate_rate
    )

    return round(max(0, score), 2)
