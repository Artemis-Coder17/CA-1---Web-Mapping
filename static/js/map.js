// =========================================================
// Flood Watch Ireland — map.js
// =========================================================

const MAP_CENTRE = [53.1424, -7.6921]; // centre of Ireland
const MAP_ZOOM   = 7;

// --- Initialise map ---
const map = L.map('map', {
  center: MAP_CENTRE,
  zoom: MAP_ZOOM,
  zoomControl: true,
});

// --- OpenStreetMap tile layer (exactly as used in Lab 4) ---
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors',
  maxZoom: 19,
  referrerPolicy: 'strict-origin-when-cross-origin',
}).addTo(map);

// --- Layer groups (populated in later commits) ---
const floodZoneLayer = L.layerGroup().addTo(map);
const riverLayer     = L.layerGroup().addTo(map);
const assetLayer     = L.layerGroup().addTo(map);

// --- Stats counters ---
function updateStats(zones, rivers, assets) {
  document.getElementById('statZones').textContent  = zones  ?? '—';
  document.getElementById('statRivers').textContent = rivers ?? '—';
  document.getElementById('statAssets').textContent = assets ?? '—';
}

// --- Layer toggle listeners (sidebar checkboxes) ---
document.getElementById('toggleFloodZones').addEventListener('change', function () {
  this.checked ? map.addLayer(floodZoneLayer) : map.removeLayer(floodZoneLayer);
});

document.getElementById('toggleRivers').addEventListener('change', function () {
  this.checked ? map.addLayer(riverLayer) : map.removeLayer(riverLayer);
});

document.getElementById('toggleAssets').addEventListener('change', function () {
  this.checked ? map.addLayer(assetLayer) : map.removeLayer(assetLayer);
});

// --- Reset filters ---
document.getElementById('resetFilters').addEventListener('click', function () {
  document.getElementById('riskFilter').value      = '';
  document.getElementById('countyFilter').value    = '';
  document.getElementById('assetTypeFilter').value = '';
  loadAllLayers();
});

// --- Bootstrap: load all layers on page ready ---
document.addEventListener('DOMContentLoaded', loadAllLayers);

function loadAllLayers() {
  // individual layer loaders added in subsequent commits
}
