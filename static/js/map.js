// Flood Watch Ireland — map.js
// Leaflet handles all the map rendering; the Django API does the spatial queries

const MAP_CENTRE = [52.97, -6.35]; // centred on Wicklow/Dublin area where our data is
const MAP_ZOOM   = 10;

const map = L.map('map', { center: MAP_CENTRE, zoom: MAP_ZOOM, zoomControl: true });

// OpenStreetMap tile layer — free and no API key needed
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
  referrerPolicy: 'strict-origin-when-cross-origin',
}).addTo(map);

// separate layer groups so we can toggle each one on/off independently
const floodZoneLayer = L.layerGroup().addTo(map);
const riverLayer     = L.layerGroup().addTo(map);
const assetLayer     = L.layerGroup().addTo(map);
const highlightLayer = L.layerGroup().addTo(map); // used for query result highlights

// prevents the map click handler (Q4) from firing straight after a zone click (Q1-Q3)
let zoneClickHandled = false;

// colour and weight per risk level — matches the OPW colour convention
const ZONE_STYLES = {
  A:  { fillColor: '#d73027', color: '#a50f15', fillOpacity: 0.45, weight: 1 },
  B:  { fillColor: '#fc8d59', color: '#e34a33', fillOpacity: 0.40, weight: 1 },
  AO: { fillColor: '#fee090', color: '#d95f0e', fillOpacity: 0.45, weight: 1 },
};

function zoneStyle(feature) {
  return ZONE_STYLES[feature.properties.risk_level] || ZONE_STYLES['A'];
}

// --- Asset icons ---
const ASSET_COLOURS = { fire_station: '#e74c3c', hospital: '#8e44ad', garda: '#2980b9' };
const ASSET_ICONS   = { fire_station: 'bi-fire', hospital: 'bi-heart-pulse-fill', garda: 'bi-shield-fill' };

function assetIcon(type, highlighted = false) {
  const colour = highlighted ? '#f39c12' : (ASSET_COLOURS[type] || '#555');
  const cls    = ASSET_ICONS[type] || 'bi-geo-alt-fill';
  return L.divIcon({
    html: `<div style="background:${colour};width:28px;height:28px;border-radius:50%;
             display:flex;align-items:center;justify-content:center;
             border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">
             <i class="${cls}" style="color:#fff;font-size:13px"></i></div>`,
    className: '', iconSize: [28, 28], iconAnchor: [14, 14],
  });
}

// --- Stats ---
function updateStats(zones, rivers, assets) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; };
  set('statZones',    zones);  set('statZonesMob',  zones);
  set('statRivers',   rivers); set('statRiversMob', rivers);
  set('statAssets',   assets); set('statAssetsMob', assets);
}

// --- API helpers ---
// unwraps DRF's paginated envelope — returns features array whether paginated or not
async function apiFetch(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.results ?? data;       // unwrap DRF pagination envelope
}

function apiUrl(endpoint, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
  return `/api/${endpoint}/${qs.toString() ? '?' + qs : ''}`;
}

// --- Load flood zones ---
async function loadFloodZones() {
  floodZoneLayer.clearLayers();
  const params = {};
  const risk   = document.getElementById('riskFilter').value;
  const county = document.getElementById('countyFilter').value;
  if (risk)   params.risk_level = risk;
  if (county) params.county     = county;

  try {
    const geojson = await apiFetch(apiUrl('flood-zones', params));
    const features = geojson.features || [];

    L.geoJSON(geojson, {
      style: zoneStyle,
      onEachFeature(feature, layer) {
        const p  = feature.properties;
        const id = feature.id;
        layer.bindPopup(
          `<strong>${p.name}</strong><br>
           Risk: <b>${p.risk_level}</b> &mdash; ${p.county}<br>
           Catchment: ${p.river_catchment}<br>
           Area: ${p.area_km2} km²<br>
           <small class="text-muted">Click to run spatial queries</small>`
        );
        layer.on('mouseover', () => layer.setStyle({ ...zoneStyle(feature), fillOpacity: 0.75, weight: 2 }));
        layer.on('mouseout',  () => layer.setStyle(zoneStyle(feature)));
        layer.on('click', (e) => {
          L.DomEvent.stopPropagation(e);   // prevent map click firing
          zoneClickHandled = true;
          runZoneQueries(id, p.name);
        });
      },
    }).addTo(floodZoneLayer);

    return features.length;
  } catch (err) {
    console.error('loadFloodZones:', err);
    return 0;
  }
}

// --- Load rivers ---
async function loadRivers() {
  riverLayer.clearLayers();
  const county = document.getElementById('countyFilter').value;
  try {
    const geojson = await apiFetch(apiUrl('rivers', county ? { county } : {}));
    L.geoJSON(geojson, {
      style: { color: '#1a6faf', weight: 3, opacity: 0.8 },
      onEachFeature(feature, layer) {
        const p = feature.properties;
        layer.bindPopup(`<strong>${p.name}</strong><br>County: ${p.county}<br>Length: ${p.length_km} km`);
      },
    }).addTo(riverLayer);
    return (geojson.features || []).length;
  } catch (err) {
    console.error('loadRivers:', err);
    return 0;
  }
}

// --- Load risk assets ---
async function loadRiskAssets() {
  assetLayer.clearLayers();
  const params = {};
  const county    = document.getElementById('countyFilter').value;
  const assetType = document.getElementById('assetTypeFilter').value;
  if (county)    params.county     = county;
  if (assetType) params.asset_type = assetType;

  try {
    const geojson = await apiFetch(apiUrl('risk-assets', params));
    L.geoJSON(geojson, {
      pointToLayer: (f, ll) => L.marker(ll, { icon: assetIcon(f.properties.asset_type) }),
      onEachFeature(feature, layer) {
        const p = feature.properties;
        layer.bindPopup(
          `<strong>${p.name}</strong>
           ${p.is_critical ? '<span class="badge bg-danger ms-1">Critical</span>' : ''}<br>
           Type: ${p.asset_type.replace('_', ' ')}<br>
           County: ${p.county}<br>
           ${p.address ? p.address + '<br>' : ''}
           Population served: ${(p.population_served || 0).toLocaleString()}`
        );
      },
    }).addTo(assetLayer);
    return (geojson.features || []).length;
  } catch (err) {
    console.error('loadRiskAssets:', err);
    return 0;
  }
}

// --- Load all layers ---
async function loadAllLayers() {
  const [zones, rivers, assets] = await Promise.all([
    loadFloodZones(), loadRivers(), loadRiskAssets(),
  ]);
  updateStats(zones, rivers, assets);
}

// =========================================================
// SPATIAL QUERIES
// =========================================================

function showResults(title, html) {
  const el = document.getElementById('queryResults');
  if (!el) return;
  el.innerHTML = `
    <hr class="my-2">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <span class="small fw-semibold">${title}</span>
      <button onclick="clearResults()" class="btn btn-sm btn-outline-secondary py-0 px-2" style="font-size:0.7rem;">Clear</button>
    </div>
    ${html}`;
  el.classList.remove('d-none');
}

function clearResults() {
  const el = document.getElementById('queryResults');
  if (!el) return;
  el.classList.add('d-none');
  el.innerHTML = '';
}

function showLoading() {
  showResults('Running queries…',
    '<div class="text-center text-muted py-3"><div class="spinner-border spinner-border-sm me-1"></div> Querying PostGIS…</div>'
  );
}

// Q1 + Q2 + Q3 — all three zone queries run in parallel when a flood zone is clicked
async function runZoneQueries(zoneId, zoneName) {
  highlightLayer.clearLayers();
  showLoading();

  const radiusKm = parseFloat(document.getElementById('bufferRadius').value) || 2;

  const safeJson = async (url) => {
    const r = await fetch(url);
    const text = await r.text();
    try { return JSON.parse(text); } catch { return { error: `HTTP ${r.status}` }; }
  };

  try {
    const [withinRes, riversRes, bufferRes] = await Promise.all([
      safeJson(`/api/flood-zones/${zoneId}/assets-within/`),
      safeJson(`/api/flood-zones/${zoneId}/intersecting-rivers/`),
      safeJson(`/api/flood-zones/${zoneId}/buffer/?radius_km=${radiusKm}`),
    ]);

    const withinFeats = withinRes.error ? [] : (withinRes.assets?.features || []);
    const riversList  = riversRes.error ? [] : (riversRes.rivers?.features || []);
    const bufferFeats = bufferRes.error ? [] : (bufferRes.assets?.features || []);

    bufferFeats.forEach(f => {
      const [lng, lat] = f.geometry.coordinates;
      L.marker([lat, lng], { icon: assetIcon(f.properties.asset_type, true) })
        .bindPopup(`<strong>${f.properties.name}</strong><br>${f.properties.distance_km} km from zone`)
        .addTo(highlightLayer);
    });

    const none = '<li class="list-group-item text-muted fst-italic py-1">None found</li>';

    const assetRows = (feats) => feats.length
      ? feats.map(f => `
          <li class="list-group-item d-flex justify-content-between align-items-start py-1 gap-2">
            <span>${f.properties.name}</span>
            <span class="badge bg-secondary rounded-pill flex-shrink-0">${f.properties.asset_type.replace('_',' ')}</span>
          </li>`).join('') : none;

    const riverRows = riversList.length
      ? riversList.map(r => `
          <li class="list-group-item d-flex justify-content-between align-items-start py-1 gap-2">
            <span>${r.properties.name}</span>
            <span class="badge bg-primary rounded-pill flex-shrink-0">${r.properties.length_km} km</span>
          </li>`).join('') : none;

    const bufferRows = bufferRes.error
      ? '<li class="list-group-item text-muted fst-italic py-1">Unavailable for this zone</li>'
      : (bufferFeats.length
          ? bufferFeats.map(f => `
              <li class="list-group-item d-flex justify-content-between align-items-start py-1 gap-2">
                <span>${f.properties.name}</span>
                <span class="badge bg-warning text-dark rounded-pill flex-shrink-0">${f.properties.distance_km} km</span>
              </li>`).join('')
          : none);

    showResults(zoneName, `
      <p class="text-muted mb-1" style="font-size:0.7rem;text-transform:uppercase;font-weight:600;">Assets inside zone</p>
      <ul class="list-group list-group-flush mb-3" style="font-size:0.8rem;">${assetRows(withinFeats)}</ul>

      <p class="text-muted mb-1" style="font-size:0.7rem;text-transform:uppercase;font-weight:600;">Rivers crossing zone</p>
      <ul class="list-group list-group-flush mb-3" style="font-size:0.8rem;">${riverRows}</ul>

      <p class="text-muted mb-1" style="font-size:0.7rem;text-transform:uppercase;font-weight:600;">Assets within ${radiusKm} km</p>
      <ul class="list-group list-group-flush" style="font-size:0.8rem;">${bufferRows}</ul>
    `);
  } catch (err) {
    showResults(zoneName, `<p class="text-danger small">Could not run queries: ${err.message}</p>`);
  }
}

// Q4 — proximity query: clicking anywhere on the map finds the nearest assets to that point
map.on('click', async function (e) {
  if (zoneClickHandled) { zoneClickHandled = false; return; }

  const { lat, lng } = e.latlng;
  highlightLayer.clearLayers();
  showLoading();

  L.circleMarker([lat, lng], {
    radius: 8, color: '#f39c12', fillColor: '#f39c12', fillOpacity: 0.9, weight: 2,
  }).bindPopup('Search point').addTo(highlightLayer);

  try {
    const limit = parseInt(document.getElementById('proximityLimit').value) || 3;
    const r    = await fetch(`/api/risk-assets/nearest/?lat=${lat}&lng=${lng}&limit=${limit}`);
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { assets: null }; }

    const features = data.assets?.features || [];

    features.forEach(f => {
      const [fLng, fLat] = f.geometry.coordinates;
      L.polyline([[lat, lng], [fLat, fLng]], {
        color: '#f39c12', weight: 2, dashArray: '5,5',
      }).addTo(highlightLayer);
      L.marker([fLat, fLng], { icon: assetIcon(f.properties.asset_type, true) })
        .bindPopup(`<strong>${f.properties.name}</strong><br>${f.properties.distance_km} km away`)
        .addTo(highlightLayer);
    });

    const rows = features.length
      ? features.map(f => `
          <li class="list-group-item d-flex justify-content-between align-items-start py-1 gap-2">
            <span>${f.properties.name}</span>
            <span class="badge bg-success rounded-pill flex-shrink-0">${f.properties.distance_km} km</span>
          </li>`).join('')
      : '<li class="list-group-item text-muted fst-italic py-1">None found</li>';

    showResults(`Nearest to (${lat.toFixed(3)}, ${lng.toFixed(3)})`, `
      <p class="text-muted mb-1" style="font-size:0.7rem;text-transform:uppercase;font-weight:600;">Nearest assets</p>
      <ul class="list-group list-group-flush" style="font-size:0.8rem;">${rows}</ul>
    `);
  } catch (err) {
    showResults('Proximity query', `<p class="text-danger small">Query error: ${err.message}</p>`);
  }
});

// =========================================================
// UI WIRING — all inside DOMContentLoaded
// =========================================================

async function populateCounties() {
  try {
    const data     = await fetch('/api/flood-zones/').then(r => r.json());
    const features = data.results?.features || [];
    const counties = [...new Set(features.map(f => f.properties.county).filter(Boolean))].sort();
    const sel      = document.getElementById('countyFilter');
    counties.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c; opt.textContent = c;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.warn('populateCounties:', err);
  }
}

document.addEventListener('DOMContentLoaded', async () => {

  // Mobile sidebar toggle
  const sidebar  = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const openSidebar  = () => { sidebar.classList.add('open');  backdrop.classList.add('open'); };
  const closeSidebar = () => { sidebar.classList.remove('open'); backdrop.classList.remove('open'); };
  document.getElementById('sidebarToggle')?.addEventListener('click', openSidebar);
  document.getElementById('sidebarClose')?.addEventListener('click', closeSidebar);
  backdrop?.addEventListener('click', closeSidebar);

  // Layer toggles
  document.getElementById('toggleFloodZones').addEventListener('change', function () {
    this.checked ? map.addLayer(floodZoneLayer) : map.removeLayer(floodZoneLayer);
  });
  document.getElementById('toggleRivers').addEventListener('change', function () {
    this.checked ? map.addLayer(riverLayer) : map.removeLayer(riverLayer);
  });
  document.getElementById('toggleAssets').addEventListener('change', function () {
    this.checked ? map.addLayer(assetLayer) : map.removeLayer(assetLayer);
  });

  // Filter dropdowns
  ['riskFilter', 'countyFilter', 'assetTypeFilter'].forEach(id => {
    document.getElementById(id).addEventListener('change', loadAllLayers);
  });

  // Reset button
  document.getElementById('resetFilters').addEventListener('click', () => {
    ['riskFilter', 'countyFilter', 'assetTypeFilter'].forEach(id => {
      document.getElementById(id).value = '';
    });
    highlightLayer.clearLayers();
    clearResults();
    loadAllLayers();
  });

  // clearQuery button no longer exists as a static element — handled inline by clearResults()

  // Populate counties then load map
  await populateCounties();
  await loadAllLayers();
});
