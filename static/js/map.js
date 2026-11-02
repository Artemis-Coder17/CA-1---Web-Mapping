// =========================================================
// Flood Watch Ireland — map.js
// =========================================================

const MAP_CENTRE = [52.97, -6.35]; // Wicklow county centre
const MAP_ZOOM   = 10;

// --- Initialise map ---
const map = L.map('map', {
  center: MAP_CENTRE,
  zoom: MAP_ZOOM,
  zoomControl: true,
});

// --- OpenStreetMap tile layer (exactly as used in Lab 4) ---
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
  referrerPolicy: 'strict-origin-when-cross-origin',
}).addTo(map);

// --- Layer groups ---
const floodZoneLayer = L.layerGroup().addTo(map);
const riverLayer     = L.layerGroup().addTo(map);
const assetLayer     = L.layerGroup().addTo(map);

// --- Risk level colour palette ---
function floodZoneStyle(feature) {
  const colours = {
    A:  { fillColor: '#d73027', color: '#a50f15', fillOpacity: 0.45, weight: 1 },
    B:  { fillColor: '#fc8d59', color: '#e34a33', fillOpacity: 0.40, weight: 1 },
    AO: { fillColor: '#fee090', color: '#d95f0e', fillOpacity: 0.45, weight: 1 },
  };
  const level = feature.properties.risk_level || 'A';
  return colours[level] || colours['A'];
}

// --- Asset type marker colours ---
const ASSET_COLOURS = {
  fire_station: '#e74c3c',
  hospital:     '#8e44ad',
  garda:        '#2980b9',
  school:       '#27ae60',
  community:    '#f39c12',
  utility:      '#7f8c8d',
};

function assetIcon(type) {
  const colour = ASSET_COLOURS[type] || '#555';
  const icons = {
    fire_station: 'bi-fire',
    hospital:     'bi-heart-pulse-fill',
    garda:        'bi-shield-fill',
    school:       'bi-book-fill',
    community:    'bi-people-fill',
    utility:      'bi-lightning-fill',
  };
  const iconClass = icons[type] || 'bi-geo-alt-fill';
  const html = `
    <div style="
      background:${colour};width:28px;height:28px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);">
      <i class="${iconClass}" style="color:#fff;font-size:13px;"></i>
    </div>`;
  return L.divIcon({ html, className: '', iconSize: [28, 28], iconAnchor: [14, 14] });
}

// --- Stats counters ---
function updateStats(zones, rivers, assets) {
  document.getElementById('statZones').textContent  = zones  ?? '—';
  document.getElementById('statRivers').textContent = rivers ?? '—';
  document.getElementById('statAssets').textContent = assets ?? '—';
}

// --- API fetch helpers ---
function buildUrl(endpoint, params = {}) {
  const base = `/api/${endpoint}/`;
  const qs   = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
  return qs.toString() ? `${base}?${qs}` : base;
}

async function fetchGeoJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = await res.json();
  // DRF-GIS wraps in { results: { type, features } }
  return data.results ?? data;
}

// --- Load flood zones ---
async function loadFloodZones() {
  floodZoneLayer.clearLayers();
  const risk   = document.getElementById('riskFilter').value;
  const county = document.getElementById('countyFilter').value;

  const params = {};
  if (risk)   params.risk_level = risk;
  if (county) params.county     = county;

  try {
    const geojson = await fetchGeoJSON(buildUrl('flood-zones', params));
    const count = (geojson.features || []).length;

    L.geoJSON(geojson, {
      style: floodZoneStyle,
      onEachFeature(feature, layer) {
        const p = feature.properties;
        layer.bindPopup(`
          <strong>${p.name}</strong><br>
          Risk level: <span class="badge" style="background:${floodZoneStyle(feature).fillColor}">${p.risk_level}</span><br>
          County: ${p.county}<br>
          Catchment: ${p.river_catchment}<br>
          Area: ${p.area_km2} km²
        `);
        layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.7 }));
        layer.on('mouseout',  () => layer.setStyle(floodZoneStyle(feature)));
      },
    }).addTo(floodZoneLayer);

    return count;
  } catch (e) {
    console.error('loadFloodZones:', e);
    return 0;
  }
}

// --- Load rivers ---
async function loadRivers() {
  riverLayer.clearLayers();
  const county = document.getElementById('countyFilter').value;
  const params = {};
  if (county) params.county = county;

  try {
    const geojson = await fetchGeoJSON(buildUrl('rivers', params));
    const count = (geojson.features || []).length;

    L.geoJSON(geojson, {
      style: { color: '#1a6faf', weight: 3, opacity: 0.8 },
      onEachFeature(feature, layer) {
        const p = feature.properties;
        layer.bindPopup(`
          <strong>${p.name}</strong><br>
          County: ${p.county}<br>
          Length: ${p.length_km} km
        `);
      },
    }).addTo(riverLayer);

    return count;
  } catch (e) {
    console.error('loadRivers:', e);
    return 0;
  }
}

// --- Load risk assets ---
async function loadRiskAssets() {
  assetLayer.clearLayers();
  const county    = document.getElementById('countyFilter').value;
  const assetType = document.getElementById('assetTypeFilter').value;

  const params = {};
  if (county)    params.county     = county;
  if (assetType) params.asset_type = assetType;

  try {
    const geojson = await fetchGeoJSON(buildUrl('risk-assets', params));
    const count = (geojson.features || []).length;

    L.geoJSON(geojson, {
      pointToLayer(feature, latlng) {
        return L.marker(latlng, { icon: assetIcon(feature.properties.asset_type) });
      },
      onEachFeature(feature, layer) {
        const p = feature.properties;
        const critical = p.is_critical
          ? '<span class="badge bg-danger ms-1">Critical</span>' : '';
        layer.bindPopup(`
          <strong>${p.name}</strong>${critical}<br>
          Type: ${p.asset_type.replace('_', ' ')}<br>
          County: ${p.county}<br>
          ${p.address ? `Address: ${p.address}<br>` : ''}
          Population served: ${(p.population_served || 0).toLocaleString()}
        `);
      },
    }).addTo(assetLayer);

    return count;
  } catch (e) {
    console.error('loadRiskAssets:', e);
    return 0;
  }
}

// --- Load all layers and update stats ---
async function loadAllLayers() {
  const [zones, rivers, assets] = await Promise.all([
    loadFloodZones(),
    loadRivers(),
    loadRiskAssets(),
  ]);
  updateStats(zones, rivers, assets);
}

// --- Populate county dropdown from API ---
async function populateCounties() {
  try {
    const data = await fetch('/api/flood-zones/?limit=500').then(r => r.json());
    const features = (data.results?.features || data.features || []);
    const counties = [...new Set(features.map(f => f.properties.county).filter(Boolean))].sort();
    const sel = document.getElementById('countyFilter');
    counties.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.warn('Could not populate counties:', e);
  }
}

// --- Layer toggle listeners ---
document.getElementById('toggleFloodZones').addEventListener('change', function () {
  this.checked ? map.addLayer(floodZoneLayer) : map.removeLayer(floodZoneLayer);
});
document.getElementById('toggleRivers').addEventListener('change', function () {
  this.checked ? map.addLayer(riverLayer) : map.removeLayer(riverLayer);
});
document.getElementById('toggleAssets').addEventListener('change', function () {
  this.checked ? map.addLayer(assetLayer) : map.removeLayer(assetLayer);
});

// --- Filter change listeners ---
['riskFilter', 'countyFilter', 'assetTypeFilter'].forEach(id => {
  document.getElementById(id).addEventListener('change', loadAllLayers);
});

// --- Reset filters ---
document.getElementById('resetFilters').addEventListener('click', function () {
  document.getElementById('riskFilter').value      = '';
  document.getElementById('countyFilter').value    = '';
  document.getElementById('assetTypeFilter').value = '';
  loadAllLayers();
});

// --- Bootstrap: load on page ready ---
document.addEventListener('DOMContentLoaded', async () => {
  await populateCounties();
  await loadAllLayers();
});
