/* static/js/map/geojson_map_utils.js */
(function () {
  "use strict";

  // ----------------------------
  // Parsing + GeoJSON normalization
  // ----------------------------
  function parseMaybeJSON(val) {
    if (!val) return null;
    if (typeof val === "object") return val;
    if (typeof val === "string") {
      try {
        return JSON.parse(val);
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  function asFeature(item) {
    if (!item) return null;

    // Already GeoJSON Feature
    if (item.type === "Feature" && item.geometry) {
      if (typeof item.geometry === "string") {
        var g0 = parseMaybeJSON(item.geometry);
        if (g0) item.geometry = g0;
      }
      return item;
    }

    // Try common geometry field names from Django/DRF
    var geom =
      parseMaybeJSON(item.geometry) ||
      parseMaybeJSON(item.boundary) ||
      parseMaybeJSON(item.geojson) ||
      parseMaybeJSON(item.geom) ||
      null;

    if (!geom || !geom.type || !geom.coordinates) return null;

    var props = Object.assign({}, item.properties || {});
    if (item.id != null && props.id == null) props.id = item.id;
    if (item.name && !props.name) props.name = item.name;
    if (item.detail_url && !props.detail_url) props.detail_url = item.detail_url;
    if (item.url && !props.url) props.url = item.url;

    return {
      type: "Feature",
      id: item.id || props.id || null,
      properties: props,
      geometry: geom
    };
  }

  function normalizeToFeatureCollection(data) {
    // FeatureCollection already
    if (data && data.type === "FeatureCollection" && Array.isArray(data.features)) {
      return {
        type: "FeatureCollection",
        features: data.features.map(asFeature).filter(Boolean)
      };
    }

    // DRF paginated
    if (data && Array.isArray(data.results)) {
      return {
        type: "FeatureCollection",
        features: data.results.map(asFeature).filter(Boolean)
      };
    }

    // Plain array
    if (Array.isArray(data)) {
      return {
        type: "FeatureCollection",
        features: data.map(asFeature).filter(Boolean)
      };
    }

    return { type: "FeatureCollection", features: [] };
  }

  // ----------------------------
  // Acres computation (Turf)
  // ----------------------------
  function computeAcresFromGeom(feature) {
    try {
      if (window.turf && feature && feature.geometry) {
        var areaSqM = turf.area(feature); // expects Feature
        if (areaSqM && areaSqM > 0) return areaSqM / 4046.8564224;
      }
    } catch (e) {
      console.warn("[MapUtils] turf.area error:", e);
    }
    return null;
  }

  // ----------------------------
  // URL + naming helpers
  // ----------------------------
  function resolveName(props, fallbackType) {
    if (!props) return fallbackType || "Unknown";
    return (
      props.name ||
      props.label ||
      props.pasture_name ||
      props.paddock_name ||
      fallbackType ||
      "Unknown"
    );
  }

  function getDetailURL(feature, type) {
    if (!feature) return null;
    var props = feature.properties || {};

    if (props.detail_url) return props.detail_url;
    if (props.url) return props.url;

    var id = props.id || feature.id;
    if (!id) return null;

    if (type === "pasture") return "/pastures/" + id + "/";
    if (type === "paddock") return "/pastures/paddock/" + id + "/";
    return null;
  }

  // ----------------------------
  // UX upgrades: legend + highlight
  // ----------------------------
  function addLegend(map, items, position) {
    var pos = position || "bottomright";
    var legend = L.control({ position: pos });

    legend.onAdd = function () {
      var div = L.DomUtil.create("div");
      div.className = "leaflet-control leaflet-bar";
      div.style.background = "white";
      div.style.padding = "8px 10px";
      div.style.borderRadius = "10px";
      div.style.boxShadow = "0 10px 15px -3px rgba(15, 23, 42, 0.15)";
      div.style.fontSize = "12px";
      div.style.lineHeight = "1.2";

      var html = "<div style='font-weight:700;margin-bottom:6px;'>Legend</div>";
      (items || []).forEach(function (it) {
        var sw = "<span style='display:inline-block;width:14px;height:10px;margin-right:8px;vertical-align:middle;border:2px solid " + it.color + ";"
          + (it.fill ? ("background:" + it.fill + ";") : "")
          + (it.dashed ? "border-style:dashed;" : "")
          + "'></span>";
        html += "<div style='margin:4px 0;white-space:nowrap;'>" + sw + it.label + "</div>";
      });

      div.innerHTML = html;
      return div;
    };

    legend.addTo(map);
    return legend;
  }

  function enableClickHighlight(layer, baseStyle, highlightStyle, timeoutMs) {
    var base = baseStyle || {};
    var hi = highlightStyle || { weight: (base.weight || 2) + 2 };
    var ms = timeoutMs || 1200;

    layer.on("click", function () {
      // Only GeoJSON vector layers have setStyle
      if (layer.setStyle) {
        layer.setStyle(hi);
        window.setTimeout(function () {
          layer.setStyle(base);
        }, ms);
      }
    });
  }

  // ----------------------------
  // Layer creation helpers
  // ----------------------------
  function createPanes(map) {
    if (!map.getPane("pastures")) {
      map.createPane("pastures");
      map.getPane("pastures").style.zIndex = 450;
    }
    if (!map.getPane("paddocks")) {
      map.createPane("paddocks");
      map.getPane("paddocks").style.zIndex = 460;
    }
  }

  function fitToGroups(map, groups, padding) {
    try {
      var all = L.featureGroup(groups.filter(Boolean));
      if (all.getLayers().length) {
        map.fitBounds(all.getBounds(), { padding: padding || [20, 20] });
        return true;
      }
    } catch (e) {
      console.warn("[MapUtils] fitBounds error:", e);
    }
    return false;
  }

  // ----------------------------
  // Expose API
  // ----------------------------
  window.MapUtils = {
    parseMaybeJSON: parseMaybeJSON,
    asFeature: asFeature,
    normalizeToFeatureCollection: normalizeToFeatureCollection,
    computeAcresFromGeom: computeAcresFromGeom,
    resolveName: resolveName,
    getDetailURL: getDetailURL,
    addLegend: addLegend,
    enableClickHighlight: enableClickHighlight,
    createPanes: createPanes,
    fitToGroups: fitToGroups
  };
})();