// static/js/maploader.js
// Pasture & paddock maps with robust inline editing + explicit Save/Cancel.
// Requires Leaflet + Leaflet.Draw + (optional) Turf.

(function (global) {
  const DEFAULT_CENTER = [34.0, -97.0];

  // ---------- Utils ----------
  const fmt = (n, d = 2) => (n == null || isNaN(n) ? "—" : Number(n).toFixed(d));
  const escapeHtml = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const readInlineJSON = (id) => {
    try {
      const el = typeof document !== "undefined" ? document.getElementById(id) : null;
      if (!el) return null;
      const txt = (el.textContent || "").trim();
      if (!txt) return null;
      return JSON.parse(txt);
    } catch { return null; }
  };

  const normalizeToFeature = (input) => {
    if (!input) return null;
    if (input.type === "Feature") return input;
    if (input.type === "FeatureCollection") {
      const first = (input.features || []).find(f => f && f.type === "Feature" && f.geometry);
      return first || null;
    }
    if (input.type && input.coordinates) return { type: "Feature", geometry: input, properties: {} };
    return null;
  };

  const acresFromFeature = (feature) => {
    if (!feature || !feature.geometry) return null;
    try {
      if (typeof turf !== "undefined" && turf.area) {
        const a_m2 = turf.area(feature);
        return a_m2 / 4046.8564224;
      }
    } catch {}
    const acresProp = feature.properties?.acres ?? feature.properties?.area_acres ?? feature.properties?.size_acres;
    return acresProp != null ? Number(acresProp) : null;
  };

  const buildFCFromRows = (rows) => {
    const feats = [];
    for (const row of rows || []) {
      const geom = row.geometry || row.boundary || row.geom || row.polygon || row.shape;
      if (!geom) continue;
      feats.push({
        type: "Feature",
        geometry: geom,
        properties: {
          id: row.id ?? row.pk,
          pk: row.pk ?? row.id,
          name: row.name ?? row.label ?? "",
          acres: row.acres ?? row.area_acres ?? null,
          pasture: row.pasture ?? row.pasture_id ?? row.pasture_pk ?? null
        }
      });
    }
    return { type: "FeatureCollection", features: feats };
  };

  // ---------- Sanitizers / validators ----------
  function _flattenLatLngs(latlngs, out = []) {
    if (!latlngs) return out;
    if (Array.isArray(latlngs)) { for (const it of latlngs) _flattenLatLngs(it, out); }
    else if (latlngs && typeof latlngs.lat === 'number' && typeof latlngs.lng === 'number'
          && Number.isFinite(latlngs.lat) && Number.isFinite(latlngs.lng)) { out.push(latlngs); }
    return out;
  }

  // Extract Leaflet polygon rings
  function _latLngRings(latlngs) {
    const rings = [];
    (function walk(arr) {
      if (!Array.isArray(arr) || !arr.length) return;
      const first = arr[0];
      if (first && typeof first === 'object' && 'lat' in first && 'lng' in first) { rings.push(arr); return; }
      for (const child of arr) walk(child);
    })(latlngs);
    return rings;
  }

  function _latLngsValidForEdit(layer) {
    if (!layer || typeof layer.getLatLngs !== 'function') return false;
    const rings = _latLngRings(layer.getLatLngs());
    if (!rings.length) return false;
    return rings.every((ring) => {
      const pts = ring.filter(ll => ll && Number.isFinite(ll.lat) && Number.isFinite(ll.lng));
      return pts.length >= 3;
    });
  }

  function sanitizeFeatureGroupForEdit(group) {
    if (!group) return;
    const isLL = (p) => p && typeof p.lat === 'number' && typeof p.lng === 'number' && Number.isFinite(p.lat) && Number.isFinite(p.lng);
    function cleanLatLngs(latlngs) {
      if (!Array.isArray(latlngs)) return [];
      const out = [];
      for (const item of latlngs) {
        if (Array.isArray(item)) {
          const inner = cleanLatLngs(item);
          if (inner.length) out.push(inner);
        } else if (isLL(item)) {
          out.push(item);
        }
      }
      const isRing = out.length && out.every(isLL);
      if (isRing) return out.length >= 3 ? out : [];
      return out.filter(x => Array.isArray(x) && x.length);
    }
    const toRemove = [];
    group.eachLayer(l => {
      try {
        if (typeof l.getLatLngs !== 'function') { toRemove.push(l); return; }
        const cleaned = cleanLatLngs(l.getLatLngs());
        if (!cleaned.length) { toRemove.push(l); return; }
        if (typeof l.setLatLngs === 'function') l.setLatLngs(cleaned);
      } catch (e) {
        console.warn('[MapLoader] sanitize failed on layer', e);
        toRemove.push(l);
      }
    });
    toRemove.forEach(l => group.removeLayer(l));
  }

  function onlyPolygons(group) {
    const toRemove = [];
    group.eachLayer(layer => {
      const isPoly = !!(layer && typeof layer.getLatLngs === 'function' && (layer instanceof L.Polygon));
      if (!isPoly) { toRemove.push(layer); return; }
      const flat = _flattenLatLngs(layer.getLatLngs());
      if (!Array.isArray(flat) || flat.length < 3) toRemove.push(layer);
    });
    toRemove.forEach(l => group.removeLayer(l));
  }

  function _cleanCoordsRing(ring) {
    if (!Array.isArray(ring)) return [];
    const pts = ring
      .filter(p => Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]))
      .map(([lng, lat]) => [lng, lat]);
    return pts.length >= 3 ? pts : [];
  }

  function rebuildPolygonLayer(layer, group) {
    try {
      const gj = layer.toGeoJSON();
      const g = gj && gj.geometry;
      if (!g || !g.type) return false;
      let latlngs;
      if (g.type === 'Polygon') {
        const rings = (g.coordinates || []).map(_cleanCoordsRing).filter(r => r.length >= 3);
        if (!rings.length) return false;
        latlngs = rings.map(r => r.map(([lng, lat]) => L.latLng(lat, lng)));
      } else if (g.type === 'MultiPolygon') {
        const polys = (g.coordinates || [])
          .map(poly => (poly || []).map(_cleanCoordsRing).filter(r => r.length >= 3))
          .filter(poly => poly.length);
        if (!polys.length) return false;
        latlngs = polys.map(rings => rings.map(r => r.map(([lng, lat]) => L.latLng(lat, lng))));
      } else { return false; }

      const fresh = L.polygon(latlngs); // Polygon or MultiPolygon (by nesting)
      try { fresh.setStyle(layer.options || {}); } catch {}
      if (group && group.hasLayer(layer)) group.removeLayer(layer);
      if (group) group.addLayer(fresh);
      return true;
    } catch (e) {
      console.warn('[MapLoader] rebuildPolygonLayer failed', e);
      return false;
    }
  }

  function rebuildGroupPolygons(group) {
    const layers = group.getLayers();
    layers.forEach(l => rebuildPolygonLayer(l, group));
  }

  // --- helper: stable id for logging ---
  function _featId(layer) {
    const f = layer && layer.feature;
    const p = f && f.properties;
    return String(p?.id ?? p?.pk ?? f?.id ?? '') || '';
  }

  // Split MultiPolygon layers into multiple Polygon layers; return info
  function splitMultiPolygons(group) {
    let split = 0;
    const toAdd = [], toRemove = [];
    const parents = []; // { id, parts }
    group.eachLayer((layer) => {
      if (!(layer instanceof L.Polygon)) return;
      const latlngs = layer.getLatLngs();
      const isMulti = Array.isArray(latlngs) && Array.isArray(latlngs[0]) && Array.isArray(latlngs[0][0]);
      if (!isMulti) return;

      const style = layer.options || {};
      const polyRingsArr = latlngs; // [poly][ring][LatLng]
      let parts = 0;

      for (const polyRings of polyRingsArr) {
        const rings = _latLngRings(polyRings);
        const validRings = rings.filter(r => r.filter(ll => Number.isFinite(ll?.lat) && Number.isFinite(ll?.lng)).length >= 3);
        if (!validRings.length) continue;
        toAdd.push(L.polygon(validRings, style));
        parts += 1;
      }

      if (parts > 0) {
        split += 1;
        parents.push({ id: _featId(layer), parts });
        toRemove.push(layer);
      }
    });
    toRemove.forEach(l => group.removeLayer(l));
    toAdd.forEach(l => group.addLayer(l));
    return { splitCount: split, parents };
  }

  function isValidFeature(feature) {
    if (!feature || !feature.geometry) return false;
    const g = feature.geometry;
    if (!g.type || !("coordinates" in g)) return false;
    if (!['Polygon','MultiPolygon'].includes(g.type)) return false;
    const isPair = (p) => Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]);
    const ringHas3 = (ring) => Array.isArray(ring) && ring.filter(isPair).length >= 3;
    if (g.type === 'Polygon') {
      const rings = Array.isArray(g.coordinates) ? g.coordinates : [];
      return rings.some(ringHas3);
    } else {
      const polys = Array.isArray(g.coordinates) ? g.coordinates : [];
      return polys.some(poly => Array.isArray(poly) && poly.some(ringHas3));
    }
  }

  // One-shot cleaner with stats + logs
  function cleanAndPrepareForEdit(group, label = "group") {
    const snap = () => new Set(group.getLayers());

    const beforeSet = snap();
    const before = beforeSet.size;

    sanitizeFeatureGroupForEdit(group);
    const afterSanSet = snap();
    const removedBySanitize = [...beforeSet].filter(l => !afterSanSet.has(l));
    const removedSanitizeIds = removedBySanitize.map(_featId).filter(Boolean);

    onlyPolygons(group);
    const afterOnlySet = snap();
    const removedByOnly = [...afterSanSet].filter(l => !afterOnlySet.has(l));
    const removedOnlyIds = removedByOnly.map(_featId).filter(Boolean);

    rebuildGroupPolygons(group);

    const splitInfo = splitMultiPolygons(group);

    let invalidRemoved = 0;
    const invalidDropped = [];
    group.getLayers().forEach(l => {
      if (!_latLngsValidForEdit(l)) {
        invalidRemoved += 1;
        invalidDropped.push(_featId(l));
        group.removeLayer(l);
      }
    });

    const afterSet = snap();
    const after = afterSet.size;

    try {
      console.info(`[MapLoader] ${label} clean`, {
        before,
        removedBySanitize: removedSanitizeIds,
        removedByOnlyPolygons: removedOnlyIds,
        split: splitInfo,
        invalidDropped,
        after
      });
    } catch {}

    return {
      before,
      removedBySanitize: removedSanitizeIds,
      removedByOnlyPolygons: removedOnlyIds,
      split: splitInfo,
      invalidDropped,
      after
    };
  }

  // ---------- Fetchers ----------
  async function fetchJSON(url) {
    try {
      const r = await fetch(url);
      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        console.warn(`[MapLoader] GET ${url} failed: ${r.status} ${txt}`);
        throw new Error(String(r.status));
      }
      return await r.json();
    } catch { return null; }
  }

  async function fetchPasturesFC(pk) {
    const inline = readInlineJSON("pasture-geojson");
    if (inline) {
      const feat = normalizeToFeature(inline);
      if (feat) return { type: "FeatureCollection", features: [feat] };
      if (inline.type === "FeatureCollection") return inline;
    }
    const detailCandidates = pk == null ? [] : [
      `/api/pastures/${pk}/`,
      `/api/pastures/${pk}`,
      `/api/pastures/detail/${pk}/`
    ];
    for (const u of detailCandidates) {
      const j = await fetchJSON(u);
      if (j && (j.geometry || j.boundary || j.geom || j.polygon || j.shape)) {
        return buildFCFromRows([j]);
      }
    }
    const listCandidates = ["/api/pastures/", "/api/pastures"];
    for (const u of listCandidates) {
      const j = await fetchJSON(u);
      if (!j) continue;
      const rows = Array.isArray(j?.results) ? j.results : (Array.isArray(j) ? j : null);
      if (rows) {
        if (pk != null) {
          const row = rows.find(o => String(o.id ?? o.pk) === String(pk));
          if (row) return buildFCFromRows([row]);
        } else {
          return buildFCFromRows(rows);
        }
      }
    }
    return { type: "FeatureCollection", features: [] };
  }

  async function fetchPaddocksFC(pk) {
    const inline = readInlineJSON("paddocks-geojson");
    if (inline) {
      if (inline.type === "FeatureCollection") {
        if (pk != null) {
          const feats = (inline.features || []).filter(f => {
            const pid = f?.properties?.pasture ?? f?.properties?.pasture_id ?? f?.properties?.pasture_pk;
            return pid == null ? true : String(pid) === String(pk);
          });
          return { type: "FeatureCollection", features: feats };
        }
        return inline;
      }
      const feat = normalizeToFeature(inline);
      if (feat) return { type: "FeatureCollection", features: [feat] };
    }
    const filtered = pk == null ? [] : [
      `/api/paddocks/?pasture=${encodeURIComponent(pk)}`,
      `/api/paddocks?pasture=${encodeURIComponent(pk)}`
    ];
    for (const u of filtered) {
      const j = await fetchJSON(u);
      if (!j) continue;
      const rows = Array.isArray(j?.results) ? j.results : (Array.isArray(j) ? j : null);
      if (rows) return buildFCFromRows(rows);
      if (j?.type === "FeatureCollection") return j;
    }
    const unfiltered = ["/api/paddocks/", "/api/paddocks"];
    for (const u of unfiltered) {
      const j = await fetchJSON(u);
      if (!j) continue;
      if (j?.type === "FeatureCollection") {
        let feats = j.features || [];
        if (pk != null) {
          const hasPastureProp = feats.some(f => f?.properties && (
            "pasture" in f.properties || "pasture_id" in f.properties || "pasture_pk" in f.properties
          ));
          if (hasPastureProp) {
            feats = feats.filter(f => {
              const pid = f?.properties?.pasture ?? f?.properties?.pasture_id ?? f?.properties?.pasture_pk;
              return String(pid) === String(pk);
            });
          }
        }
        return { type: "FeatureCollection", features: feats };
      }
      const rows = Array.isArray(j?.results) ? j.results : (Array.isArray(j) ? j : null);
      if (rows) {
        let fc = buildFCFromRows(rows);
        if (pk != null) {
          const hasPastureProp = fc.features.some(f => f?.properties && f.properties.pasture != null);
          if (hasPastureProp) fc.features = fc.features.filter(f => String(f.properties.pasture) === String(pk));
        }
        return fc;
      }
    }
    return { type: "FeatureCollection", features: [] };
  }

  // ---------- Basemap ----------
  function ensureLeafletControlIcons() {
    if (typeof document === "undefined") return;
    if (document.getElementById("ml-leaflet-icons-css")) return;
    const style = document.createElement("style");
    style.id = "ml-leaflet-icons-css";
    style.textContent = `
      .leaflet-control-layers-toggle{
        background-image:url("https://unpkg.com/leaflet@1.9.4/dist/images/layers.png");
      }
      .leaflet-retina .leaflet-control-layers-toggle{
        background-image:url("https://unpkg.com/leaflet@1.9.4/dist/images/layers-2x.png");
      }
    `;
    document.head.appendChild(style);
  }

  function createBaseLayers() {
    const street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 20, attribution: '&copy; OpenStreetMap'
    });
    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 20, attribution: 'Tiles © Esri & contributors' }
    );
    return { street, satellite };
  }

  function createMap(el, { center = DEFAULT_CENTER, zoom = 11, showLayerToggle = true } = {}) {
    if (el.offsetHeight === 0) el.style.minHeight = "420px";
    ensureLeafletControlIcons();
    const { street, satellite } = createBaseLayers();
    if (window.L && L.Icon && L.Icon.Default) {
      L.Icon.Default.imagePath = "https://unpkg.com/leaflet@1.9.4/dist/images/";
    }
    const map = L.map(el, { preferCanvas: false, center, zoom, layers: [street] });
    if (showLayerToggle) {
      L.control.layers({ "Street": street, "Satellite": satellite }, null, { position: "topleft" }).addTo(map);
    }
    const boundaryGroup = L.featureGroup().addTo(map);
    const paddockGroup  = L.featureGroup().addTo(map);
    const fitAll = () => {
      const bounds = L.latLngBounds([]);
      let any = false;
      [boundaryGroup, paddockGroup].forEach(g => g.eachLayer(l => {
        if (l.getBounds) { bounds.extend(l.getBounds()); any = true; }
        else if (l.getLatLng) { bounds.extend(l.getLatLng()); any = true; }
      }));
      if (any && bounds.isValid && bounds.isValid()) map.fitBounds(bounds.pad(0.1));
      else map.setView(center, zoom);
    };
    setTimeout(() => { try { map.invalidateSize(); } catch {} }, 0);
    return { map, boundaryGroup, paddockGroup, fitAll };
  }

  // ---------- Helpers ----------
  function collectGeometryFromGroup(group) {
    const geoms = [];
    group.eachLayer(l => {
      const g = l.toGeoJSON()?.geometry;
      if (g) geoms.push(g);
    });
    if (geoms.length === 0) return null;
    if (geoms.length === 1) return geoms[0];
    const polys = [];
    for (const g of geoms) {
      if (g.type === 'Polygon') polys.push(g.coordinates);
      else if (g.type === 'MultiPolygon') polys.push(...g.coordinates);
    }
    if (polys.length === 0) return geoms[0];
    return { type: 'MultiPolygon', coordinates: polys };
  }

  const coerceGeometryType = (geom, expectedType) => {
    try {
      if (!geom || !expectedType) return geom;
      if (geom.type === expectedType) return geom;
      if (expectedType === 'MultiPolygon' && geom.type === 'Polygon') {
        return { type: 'MultiPolygon', coordinates: [geom.coordinates] };
      }
      if (expectedType === 'Polygon' && geom.type === 'MultiPolygon') {
        const first = Array.isArray(geom.coordinates) ? geom.coordinates[0] : null;
        if (first) return { type: 'Polygon', coordinates: first };
      }
    } catch {}
    return geom;
  };

  function renderPaddockPopup({ name, pid, enableEdit }) {
    const safeName = escapeHtml(name ?? (pid ? `Paddock ${pid}` : "Paddock"));
    const link = pid ? `<a class="underline text-blue-600" href="/pastures/paddock/${encodeURIComponent(String(pid))}/">Open paddock</a>` : "";
    const editBtn = (enableEdit && pid) ? `<button data-edit="${String(pid)}" class="px-2 py-1 border rounded">✏️ Edit</button>` : "";
    return `<div style="display:grid;gap:6px;min-width:180px;">
      <strong>${safeName}</strong>
      ${link}
      ${editBtn}
    </div>`;
  }

  function _groupHasEditablePolygon(group) {
    const layers = group.getLayers();
    for (const l of layers) {
      if (l instanceof L.Polygon) {
        const flat = _flattenLatLngs(l.getLatLngs());
        if (flat.length >= 3) return true;
      }
    }
    return false;
  }

  function _mountCreatePolygon(map, boundaryGroup, onCreated) {
    if (!L || !L.Control || !L.Control.Draw) {
      alert("Leaflet.Draw is not loaded (need leaflet.draw.js + leaflet.draw.css).");
      return null;
    }
    const drawCtl = new L.Control.Draw({
      draw: {
        polygon: { allowIntersection: false, showArea: true, repeatMode: false },
        marker: false, polyline: false, rectangle: false, circle: false, circlemarker: false
      },
      edit: false
    });
    map.addControl(drawCtl);

    const onCreatedWrap = (e) => {
      const layer = e.layer;
      boundaryGroup.clearLayers();
      boundaryGroup.addLayer(layer);
      if (typeof onCreated === "function") onCreated(layer);
      map.off(L.Draw.Event.CREATED, onCreatedWrap);
      try { map.removeControl(drawCtl); } catch {}
      console.info("[MapLoader] create-mode: new boundary drawn, control removed.");
    };

    map.on(L.Draw.Event.CREATED, onCreatedWrap);
    alert("Use the polygon tool (✳️) to draw a new pasture boundary, then click 💾 to save.");
    return drawCtl;
  }

  // ---------- Pasture Detail ----------
  async function loadPastureDetail({
    el, pk,
    updateUrl,
    getCSRF = () => "",
    showLayerToggle = true,
    enableEdit = true,
    enablePaddockEdit = false,
    paddockUpdateUrlFor = (id) => null,
    onStats = () => {},
  } = {}) {
    const { map, boundaryGroup, paddockGroup, fitAll } = createMap(el, { showLayerToggle });

    const [pasturesFC, paddocksFC] = await Promise.all([fetchPasturesFC(pk), fetchPaddocksFC(pk)]);

    // Pasture boundary
    let pastureFeature = null;
    if (pasturesFC?.type === "FeatureCollection") {
      pastureFeature = (pasturesFC.features || []).find(f => {
        const id = f?.properties?.id ?? f?.properties?.pk ?? f?.id;
        return String(id) === String(pk);
      }) || (pasturesFC.features || [])[0] || null;
    }
    pastureFeature = normalizeToFeature(pastureFeature);

    if (pastureFeature) {
      L.geoJSON(pastureFeature, {
        filter: isValidFeature, style: { weight: 2.25, color: "#16a34a", fillOpacity: 0.08 } })
        .eachLayer(l => boundaryGroup.addLayer(l));
    }

    const stats = cleanAndPrepareForEdit(boundaryGroup, "pastureBoundary");
    if (!_groupHasEditablePolygon(boundaryGroup)) {
      console.info("[MapLoader] pastureBoundary: no editable polygons after clean; switching to create-mode.");
      _mountCreatePolygon(map, boundaryGroup, () => {});
    }

    // Paddocks
    let paddockFeatureCount = 0;
    const paddockEditableGroup = L.featureGroup().addTo(map);

    if (paddocksFC?.type === "FeatureCollection") {
      const tmpGroup = L.featureGroup();
      L.geoJSON(paddocksFC, {
        filter: isValidFeature,
        style: { weight: 1.2, color: "#3b82f6", fillOpacity: 0.12 },
        onEachFeature: (feat, layer) => {
          paddockFeatureCount += 1;
          const pid  = feat?.properties?.id ?? feat?.properties?.pk;
          const name = feat?.properties?.name ?? feat?.properties?.label ?? (pid ? `Paddock ${pid}` : "Paddock");
          layer.bindPopup(renderPaddockPopup({ name, pid, enableEdit: enablePaddockEdit }));

          layer.on("popupopen", (e) => {
            if (!enablePaddockEdit || !pid) return;
            const btn = e.popup?.getElement()?.querySelector(`button[data-edit="${String(pid)}"]`);
            if (!btn) return;

            btn.addEventListener("click", () => {
              paddockEditableGroup.clearLayers();
              paddockEditableGroup.addLayer(layer);
              map.closePopup();

              if (!window.L || !L.Control || !L.Control.Draw) {
                console.warn("[MapLoader] Leaflet.Draw not loaded; paddock edit disabled.");
                return;
              }

              sanitizeFeatureGroupForEdit(paddockEditableGroup);

              const drawCtl = new L.Control.Draw({
                draw: false,
                edit: { featureGroup: paddockEditableGroup, edit: true, remove: false }
              });
              map.addControl(drawCtl);

              const onEdited = async (evt) => {
                try {
                  evt.layers.eachLayer(async (editLayer) => {
                    if (!paddockEditableGroup.hasLayer(editLayer)) return;
                    const gjGeom = editLayer.toGeoJSON().geometry;
                    const url = paddockUpdateUrlFor(pid);
                    if (!url) throw new Error("paddockUpdateUrlFor() returned null");

                    const payload = {
                      field: "geometry",
                      value: gjGeom,
                      geometry: gjGeom,
                      boundary: gjGeom,
                      geom: gjGeom,
                      polygon: gjGeom,
                    };
                    const resp = await fetch(url, {
                      method: "POST",
                      headers: { "X-CSRFToken": getCSRF(), "Content-Type": "application/json" },
                      body: JSON.stringify(payload)
                    });
                    if (!resp.ok && resp.status !== 204) {
                      let text = ""; try { text = await resp.text(); } catch {}
                      console.error("[MapLoader] Paddock save failed", resp.status, text);
                      throw new Error(`Paddock save failed ${resp.status}`);
                    }
                  });
                } catch (err) {
                  console.error("[MapLoader] Paddock save error:", err);
                  alert("Could not save paddock boundary.");
                } finally {
                  try { map.removeControl(drawCtl); } catch {}
                  map.off(L.Draw.Event.EDITED, onEdited);
                }
              };
              map.on(L.Draw.Event.EDITED, onEdited);
            }, { once: true });
          });

          tmpGroup.addLayer(layer);
        }
      });

      if (!enablePaddockEdit) {
        const before = tmpGroup.getLayers().length;
        const split = splitMultiPolygons(tmpGroup);
        const after = tmpGroup.getLayers().length;
        console.info(`[MapLoader] paddocks(display): before=${before}, split=${split.splitCount}, after=${after}`);
      } else {
        console.info("[MapLoader] paddocks(edit): no split to preserve full geometry on save.");
      }

      tmpGroup.eachLayer(l => paddockGroup.addLayer(l));
    }

    // Stats callback
    let acres = null;
    const bl = boundaryGroup.getLayers();
    if (bl.length && typeof turf !== "undefined" && turf.area) {
      const fc = { type: "FeatureCollection", features: bl.map(l => l.toGeoJSON()) };
      acres = turf.area(fc) / 4046.8564224;
    } else if (pastureFeature) {
      acres = acresFromFeature(pastureFeature);
    }
    onStats({ paddockCount: paddockFeatureCount, acres, cleanStats: stats });

    // ---------- Pasture edit ----------
    let editToolbar = null;

    function enterEditMode() {
      if (!window.L || !L.EditToolbar || !L.EditToolbar.Edit) {
        console.warn("[MapLoader] Leaflet.Draw not loaded; pasture edit disabled.");
        alert('Leaflet.Draw is not loaded on this page. Include leaflet.draw.js and leaflet.draw.css after Leaflet.');
        return;
      }
      if (editToolbar && typeof editToolbar.enabled === "function" && editToolbar.enabled()) return;

      const s = cleanAndPrepareForEdit(boundaryGroup, "enterEdit");
      if (!_groupHasEditablePolygon(boundaryGroup)) {
        _mountCreatePolygon(map, boundaryGroup, () => {});
        return;
      }

      const layers = boundaryGroup.getLayers();
      editToolbar = new L.EditToolbar.Edit(map, {
        featureGroup: boundaryGroup,
        selectedPathOptions: { maintainColor: true }
      });
      editToolbar.enable();

      let anyEnabled = false;
      layers.forEach(layer => {
        try {
          if (_latLngsValidForEdit(layer) && layer.editing && typeof layer.editing.enable === 'function') {
            layer.editing.enable();
            anyEnabled = true;
          }
        } catch (e) { console.warn('[MapLoader] layer.editing.enable() failed', e); }
      });

      if (!anyEnabled) {
        try { editToolbar.disable(); } catch {}
        editToolbar = null;
        _mountCreatePolygon(map, boundaryGroup, () => {});
      }
    }

    async function saveEdits() {
      const geom = collectGeometryFromGroup(boundaryGroup);
      if (!updateUrl) {
        alert("Cannot save: missing updateUrl.");
        return;
      }
      if (!geom) {
        alert("No geometry to save.");
        return;
      }

      const expectedGeomType = pastureFeature?.geometry?.type || 'Polygon';
      const g = coerceGeometryType(geom, expectedGeomType);

      // best-effort CSRF fallback if getCSRF() returns empty
      const cookieCSRF = (() => {
        try {
          return document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "";
        } catch {
          return "";
        }
      })();
      const csrfToken = (typeof getCSRF === 'function' && getCSRF()) || cookieCSRF || "";

      // Match the same payload style as field autosave: FormData(field, value)
      const form = new FormData();
      form.append('field', 'geometry');
      form.append('value', JSON.stringify(g));

      try {
        const headers = {};
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        const resp = await fetch(updateUrl, {
          method: 'POST',
          headers,
          body: form,
        });

        const text = await resp.text().catch(() => '');

        if (!resp.ok && resp.status !== 204) {
          console.error('[MapLoader] save failed', resp.status, text);
          alert('Could not save pasture boundary. See console for details.');
          return;
        }

        console.info('[MapLoader] save success', resp.status, text.slice(0, 200));

        const newAcres = (typeof turf !== 'undefined' && turf.area)
          ? turf.area({ type: 'Feature', geometry: g }) / 4046.8564224
          : undefined;
        onStats({ paddockCount: paddockFeatureCount, acres: newAcres ?? undefined, saved: true });

        if (editToolbar) {
          try { editToolbar.disable(); } catch {}
          editToolbar = null;
        }
      } catch (e) {
        console.error('[MapLoader] save exception', e);
        alert('Could not save pasture boundary. See console for details.');
      }
    }

    function cancelEdits() {
      if (editToolbar) {
        try { editToolbar.revertLayers(); } catch {}
        try { editToolbar.disable(); } catch {}
        editToolbar = null;
      }
    }

    function _startCreateFlow() {
      if (editToolbar) { try { editToolbar.disable(); } catch {} editToolbar = null; }
      console.info("[MapLoader] create-mode: user requested new boundary.");
      _mountCreatePolygon(map, boundaryGroup, () => {});
    }

    // Keyboard shortcuts (E / Ctrl|Cmd+S / Esc)
    const keyHandler = (ev) => {
      const tag = (ev.target && ev.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || ev.target?.isContentEditable) return;
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); saveEdits(); }
      else if (ev.key === "Escape") { cancelEdits(); }
      else if (!ev.ctrlKey && !ev.metaKey && ev.key.toLowerCase() === "e") { enterEditMode(); }
    };

    // Floating controls: ✳️ Draw, ✏️ Edit, 💾 Save, ↩️ Cancel
    function addFloatingEditButtons() {
      const Ctrl = L.Control.extend({
        options: { position: 'topleft' },
        onAdd: function() {
          const c = L.DomUtil.create('div', 'leaflet-bar');
          c.style.display = 'grid'; c.style.gap = '2px'; c.style.padding = '2px';
          const mk = (t, label) => {
            const a = L.DomUtil.create('a', '', c);
            a.href = '#'; a.title = t; a.innerHTML = label;
            a.style.textAlign = 'center'; a.style.fontSize = '14px';
            a.style.lineHeight = '26px'; a.style.width = '28px'; a.style.height = '28px';
            a.style.userSelect = 'none'; a.style.cursor = 'pointer';
            L.DomEvent.disableClickPropagation(a);
            return a;
          };
          const drawBtn   = mk('Draw New Boundary', '✳️');
          const editBtn   = mk('Edit (E)', '✏️');
          const saveBtn   = mk('Save (Ctrl/Cmd+S)', '💾');
          const cancelBtn = mk('Cancel (Esc)', '↩️');

          drawBtn.onclick = e => { e.preventDefault(); _startCreateFlow(); };
          editBtn.onclick = e => { e.preventDefault(); enterEditMode(); };
          saveBtn.onclick = async e => { e.preventDefault(); await saveEdits(); };
          cancelBtn.onclick = e => { e.preventDefault(); cancelEdits(); };

          return c;
        }
      });
      map.addControl(new Ctrl());
    }

    if (enableEdit) {
      addFloatingEditButtons();
      const container = map.getContainer();
      (container || document).addEventListener("keydown", keyHandler);
      map.on("unload", () => {
        try { (container || document).removeEventListener("keydown", keyHandler); } catch {}
      });
    }

    fitAll();
    return { map, boundaryGroup, paddockGroup, paddockFeatureCount, acres };
  }

  // ---------- Paddock Detail ----------
  async function loadPaddockDetail({
    el,
    paddockFeature,
    pastureFeature,
    boundarySaveUrl,
    getCSRF = () => "",
    showLayerToggle = true,
    enableEdit = true,
    onStats = () => {},
  } = {}) {
    if (!el || !window.L) {
      console.warn("[MapLoader] loadPaddockDetail: missing element or Leaflet");
      return null;
    }

    const { map, boundaryGroup, paddockGroup, fitAll } = createMap(el, { showLayerToggle });

    const paddockFeatNorm = normalizeToFeature(paddockFeature);
    const pastureFeatNorm = normalizeToFeature(pastureFeature);

    // Draw parent pasture (non-editable) for context
    if (pastureFeatNorm) {
      L.geoJSON(pastureFeatNorm, {
        filter: isValidFeature,
        style: { weight: 1.6, color: "#16a34a", fillOpacity: 0.05 },
      }).eachLayer((l) => paddockGroup.addLayer(l));
    }

    // Draw paddock boundary into boundaryGroup (this is what we edit)
    if (paddockFeatNorm) {
      L.geoJSON(paddockFeatNorm, {
        filter: isValidFeature,
        style: { weight: 2.25, color: "#3b82f6", fillOpacity: 0.15 },
      }).eachLayer((l) => boundaryGroup.addLayer(l));
    }

    // Clean + ensure editable polygons
    const cleanStats = cleanAndPrepareForEdit(boundaryGroup, "paddockBoundary");
    if (!_groupHasEditablePolygon(boundaryGroup)) {
      console.info("[MapLoader] paddockBoundary: no editable polygons after clean; switching to create-mode.");
      _mountCreatePolygon(map, boundaryGroup, () => {});
    }

    // Compute acres (from paddock geometry if possible)
    let acres = null;
    const bl = boundaryGroup.getLayers();
    if (bl.length && typeof turf !== "undefined" && turf.area) {
      const fc = { type: "FeatureCollection", features: bl.map((l) => l.toGeoJSON()) };
      acres = turf.area(fc) / 4046.8564224;
    } else {
      acres = acresFromFeature(paddockFeatNorm) ?? null;
    }

    onStats({ acres, cleanStats });

    // ---- Edit / Save / Cancel logic (same feel as pasture detail) ----
    let editToolbar = null;

    function enterEditMode() {
      if (!window.L || !L.EditToolbar || !L.EditToolbar.Edit) {
        console.warn("[MapLoader] Leaflet.Draw not loaded; paddock edit disabled.");
        alert("Leaflet.Draw is not loaded on this page. Include leaflet.draw.js and leaflet.draw.css.");
        return;
      }
      if (editToolbar && typeof editToolbar.enabled === "function" && editToolbar.enabled()) return;

      const s = cleanAndPrepareForEdit(boundaryGroup, "enterPaddockEdit");
      if (!_groupHasEditablePolygon(boundaryGroup)) {
        _mountCreatePolygon(map, boundaryGroup, () => {});
        return;
      }

      const layers = boundaryGroup.getLayers();
      editToolbar = new L.EditToolbar.Edit(map, {
        featureGroup: boundaryGroup,
        selectedPathOptions: { maintainColor: true },
      });
      editToolbar.enable();

      let anyEnabled = false;
      layers.forEach((layer) => {
        try {
          if (_latLngsValidForEdit(layer) && layer.editing && typeof layer.editing.enable === "function") {
            layer.editing.enable();
            anyEnabled = true;
          }
        } catch (e) {
          console.warn("[MapLoader] paddock layer.editing.enable() failed", e);
        }
      });

      if (!anyEnabled) {
        try { editToolbar.disable(); } catch {}
        editToolbar = null;
        _mountCreatePolygon(map, boundaryGroup, () => {});
      }
    }

    async function saveEdits() {
      if (!boundarySaveUrl) {
        alert("Cannot save: missing boundarySaveUrl.");
        return;
      }
      const geom = collectGeometryFromGroup(boundaryGroup);
      if (!geom) {
        alert("No geometry to save.");
        return;
      }

      const expectedGeomType = paddockFeatNorm?.geometry?.type || "Polygon";
      const g = coerceGeometryType(geom, expectedGeomType);
      const feature = { type: "Feature", geometry: g, properties: {} };

      // CSRF
      const cookieCSRF = (() => {
        try {
          return document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "";
        } catch {
          return "";
        }
      })();
      const csrfToken = (typeof getCSRF === "function" && getCSRF()) || cookieCSRF || "";

      try {
        const headers = { "Content-Type": "application/json" };
        if (csrfToken) headers["X-CSRFToken"] = csrfToken;

        const resp = await fetch(boundarySaveUrl, {
          method: "POST",
          headers,
          body: JSON.stringify(feature),
        });

        const text = await resp.text().catch(() => "");
        if (!resp.ok && resp.status !== 204) {
          console.error("[MapLoader] paddock save failed", resp.status, text);
          alert("Could not save paddock boundary. See console for details.");
          return;
        }

        console.info("[MapLoader] paddock save success", resp.status, text.slice(0, 200));

        const newAcres =
          typeof turf !== "undefined" && turf.area ? turf.area(feature) / 4046.8564224 : acres;
        onStats({ acres: newAcres ?? acres, saved: true });

        if (editToolbar) {
          try { editToolbar.disable(); } catch {}
          editToolbar = null;
        }
      } catch (e) {
        console.error("[MapLoader] paddock save exception", e);
        alert("Could not save paddock boundary. See console for details.");
      }
    }

    function cancelEdits() {
      if (editToolbar) {
        try { editToolbar.revertLayers(); } catch {}
        try { editToolbar.disable(); } catch {}
        editToolbar = null;
      }
    }

    function startCreateFlow() {
      if (editToolbar) {
        try { editToolbar.disable(); } catch {}
        editToolbar = null;
      }
      console.info("[MapLoader] paddock create-mode: user requested new boundary.");
      _mountCreatePolygon(map, boundaryGroup, () => {});
    }

    // Keyboard shortcuts (E / Ctrl|Cmd+S / Esc) – same as pasture
    const keyHandler = (ev) => {
      const tag = (ev.target && ev.target.tagName) ? ev.target.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea" || ev.target?.isContentEditable) return;
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") {
        ev.preventDefault();
        saveEdits();
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        cancelEdits();
      } else if (!ev.ctrlKey && !ev.metaKey && ev.key.toLowerCase() === "e") {
        ev.preventDefault();
        enterEditMode();
      }
    };

    function addFloatingEditButtons() {
      const Ctrl = L.Control.extend({
        options: { position: "topleft" },
        onAdd: function () {
          const c = L.DomUtil.create("div", "leaflet-bar");
          c.style.display = "grid";
          c.style.gap = "2px";
          c.style.padding = "2px";
          const mk = (t, label) => {
            const a = L.DomUtil.create("a", "", c);
            a.href = "#";
            a.title = t;
            a.innerHTML = label;
            a.style.textAlign = "center";
            a.style.fontSize = "14px";
            a.style.lineHeight = "26px";
            a.style.width = "28px";
            a.style.height = "28px";
            a.style.userSelect = "none";
            a.style.cursor = "pointer";
            L.DomEvent.disableClickPropagation(a);
            return a;
          };
          const drawBtn = mk("Draw New Boundary", "✳️");
          const editBtn = mk("Edit (E)", "✏️");
          const saveBtn = mk("Save (Ctrl/Cmd+S)", "💾");
          const cancelBtn = mk("Cancel (Esc)", "↩️");

          drawBtn.onclick = (e) => {
            e.preventDefault();
            startCreateFlow();
          };
          editBtn.onclick = (e) => {
            e.preventDefault();
            enterEditMode();
          };
          saveBtn.onclick = (e) => {
            e.preventDefault();
            saveEdits();
          };
          cancelBtn.onclick = (e) => {
            e.preventDefault();
            cancelEdits();
          };

          return c;
        },
      });
      map.addControl(new Ctrl());
    }

    if (enableEdit) {
      addFloatingEditButtons();
      const container = map.getContainer();
      (container || document).addEventListener("keydown", keyHandler);
      map.on("unload", () => {
        try {
          (container || document).removeEventListener("keydown", keyHandler);
        } catch {}
      });
    }

    fitAll();
    return { map, boundaryGroup, paddockGroup, acres };
  }

  // ---------- Pasture List ----------
  async function loadPastureList({ el, showLayerToggle = true, onReady = () => {} } = {}) {
    const { map, boundaryGroup, paddockGroup, fitAll } = createMap(el, { showLayerToggle });
    const [pasturesFC, paddocksFC] = await Promise.all([fetchPasturesFC(null), fetchPaddocksFC(null)]);

    if (pasturesFC?.type === "FeatureCollection") {
      L.geoJSON(pasturesFC, {
        filter: isValidFeature,
        style: { weight: 1.6, color: "#16a34a", fillOpacity: 0.05 } })
        .eachLayer(l => boundaryGroup.addLayer(l));
      const s = cleanAndPrepareForEdit(boundaryGroup, "pastureList");
      if (s.after === 0) console.info("[MapLoader] pastureList: no polygons after clean.");
    }
    if (paddocksFC?.type === "FeatureCollection") {
      const tmp = L.featureGroup();
      L.geoJSON(paddocksFC, {
        filter: isValidFeature,
        style: { weight: 1.0, color: "#3b82f6", fillOpacity: 0.10 } })
        .eachLayer(l => tmp.addLayer(l));
      const before = tmp.getLayers().length;
      const split = splitMultiPolygons(tmp);
      const after = tmp.getLayers().length;
      console.info(`[MapLoader] paddockList(display): before=${before}, split=${split.splitCount}, after=${after}`);
      tmp.eachLayer(l => paddockGroup.addLayer(l));
    }

    fitAll();
    onReady({ pasturesFC, paddocksFC, map, boundaryGroup, paddockGroup });
    return { map, boundaryGroup, paddockGroup };
  }

  // Expose (runtime + small test surface)
  const api = { loadPastureDetail, loadPaddockDetail, loadPastureList, fmt };
  const _test = { isValidFeature, _cleanCoordsRing, coerceGeometryType, _latLngsValidForEdit, splitMultiPolygons, cleanAndPrepareForEdit };
  global.MapLoader = api;
  global.MapLoaderTest = _test;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { MapLoader: api, MapLoaderTest: _test };
  }
})(typeof window !== "undefined" ? window : globalThis);
