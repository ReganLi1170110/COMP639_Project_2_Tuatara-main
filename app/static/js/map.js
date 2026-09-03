window.MapCommon = (function () {
  function applyDrawLocale() {
    L.drawLocal.edit.handlers.remove.tooltip.text = "Remove operational area";
    L.drawLocal.edit.handlers.edit.tooltip.text = "Drag a point to edit operational area";
    L.drawLocal.edit.toolbar.buttons.edit = "Edit operational area";
    L.drawLocal.edit.toolbar.buttons.remove = "Remove operational area";
    L.drawLocal.draw.toolbar.buttons.polygon = "Draw polygon";
    L.drawLocal.draw.handlers.polygon.tooltip.start = "Click to start drawing";
    L.drawLocal.draw.handlers.polygon.tooltip.cont = "Click to continue drawing";
    L.drawLocal.draw.handlers.polygon.tooltip.end = "Click first point to finish";
  }

  function createMap(options) {
    const map = L.map(options.containerId || "operations-map").setView([-41.3, 174.7], 6);
    map.doubleClickZoom.disable();

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    const editableLayer = new L.FeatureGroup();
    map.addLayer(editableLayer);

    applyDrawLocale();

    if (options.enableDrawControl) {
      const drawControl = new L.Control.Draw({
        draw: {
          polygon: {
            shapeOptions: {
              color: options.polygonStrokeColor || "#2e7d32",
              fillOpacity: 0.12,
            },
            allowIntersection: false,
          },
          polyline: false,
          rectangle: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: {
          featureGroup: editableLayer,
        },
      });
      map.addControl(drawControl);
    }

    return { map, markersLayer, editableLayer };
  }

  function createFeedback(feedbackEl) {
    function show(message, kind) {
      if (!feedbackEl) {
        return;
      }
      feedbackEl.classList.remove("d-none", "alert-success", "alert-danger", "alert-warning", "alert-info");
      feedbackEl.classList.add("alert-" + (kind || "info"));
      feedbackEl.textContent = message;
    }

    function hide() {
      if (!feedbackEl) {
        return;
      }
      feedbackEl.classList.add("d-none");
      feedbackEl.textContent = "";
    }

    return { show, hide };
  }

  async function requestJson(url, options) {
    const response = await fetch(url, options);
    const data = await response.json().catch(function () {
      return {};
    });

    if (!response.ok) {
      throw new Error(data.error || "Request failed.");
    }

    return data;
  }

  function createMarkerIcon(marker) {
    const isTrap = marker.kind === "trap";
    const color = isTrap ? "#0d6efd" : "#ff7a18";
    return L.divIcon({
      className: "map-marker-dot-wrap",
      html: '<span style="display:block;width:14px;height:14px;border-radius:999px;background:' + color + ';border:2px solid #fff;box-shadow:0 0 0 1px ' + color + '"></span>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
      popupAnchor: [0, -10],
    });
  }

  const reverseGeocodeCache = new Map();
  const reverseGeocodeInFlight = new Map();

  function markerCoordinateKey(latitude, longitude) {
    return Number(latitude).toFixed(5) + "," + Number(longitude).toFixed(5);
  }

  function markerFallbackHoverLabel(marker) {
    return (
      marker.place_name ||
      marker.name ||
      marker.line_name ||
      marker.group_name ||
      marker.code ||
      ""
    ).toString().trim();
  }

  async function lookupPlaceNameByCoordinates(latitude, longitude) {
    const lat = Number(latitude);
    const lng = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return "";
    }

    const cacheKey = markerCoordinateKey(lat, lng);
    if (reverseGeocodeCache.has(cacheKey)) {
      return reverseGeocodeCache.get(cacheKey);
    }

    if (reverseGeocodeInFlight.has(cacheKey)) {
      return reverseGeocodeInFlight.get(cacheKey);
    }

    const request = fetch(
      "https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=" +
        encodeURIComponent(lat) +
        "&lon=" +
        encodeURIComponent(lng) +
        "&zoom=16&addressdetails=1",
      {
        headers: {
          "Accept": "application/json",
        },
      }
    )
      .then(function (response) {
        if (!response.ok) {
          return null;
        }
        return response.json().catch(function () {
          return null;
        });
      })
      .then(function (data) {
        const placeName = data && (data.name || data.display_name)
          ? String(data.name || data.display_name).trim()
          : "";
        reverseGeocodeCache.set(cacheKey, placeName);
        return placeName;
      })
      .catch(function () {
        reverseGeocodeCache.set(cacheKey, "");
        return "";
      })
      .finally(function () {
        reverseGeocodeInFlight.delete(cacheKey);
      });

    reverseGeocodeInFlight.set(cacheKey, request);
    return request;
  }

  function addOrReplaceMarker(options) {
    const marker = options.marker;
    const markerKey = marker.kind + "_" + marker.id;
    const existing = options.markerLayerMap.get(markerKey);

    if (existing) {
      options.markersLayer.removeLayer(existing.layer);
      options.markerLayerMap.delete(markerKey);
    }

    const canDrag = typeof options.canDragMarker === "function"
      ? !!options.canDragMarker(marker)
      : !!options.canDragMarker;

    const layer = L.marker([marker.latitude, marker.longitude], {
      icon: createMarkerIcon(marker),
      draggable: canDrag,
    });

    const hoverLabel = markerFallbackHoverLabel(marker);

    if (hoverLabel) {
      layer.bindTooltip(hoverLabel, {
        direction: "top",
        offset: [0, -10],
        opacity: 0.95,
      });
    }

    if (!marker.place_name) {
      lookupPlaceNameByCoordinates(marker.latitude, marker.longitude)
        .then(function (placeName) {
          if (!placeName) {
            return;
          }

          const markerMapEntry = options.markerLayerMap.get(markerKey);
          if (!markerMapEntry || markerMapEntry.layer !== layer) {
            return;
          }

          const existingTooltip = layer.getTooltip();
          if (existingTooltip) {
            existingTooltip.setContent(placeName);
          } else {
            layer.bindTooltip(placeName, {
              direction: "top",
              offset: [0, -10],
              opacity: 0.95,
            });
          }
        })
        .catch(function () {
          return null;
        });
    }

    const popupContent = document.createElement("div");
    popupContent.innerHTML = options.popupHtml(marker);

    const editBtn = popupContent.querySelector("[data-marker-id]");
    if (editBtn && typeof options.onEdit === "function") {
      editBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        options.onEdit(marker);
      });
    }

    if (canDrag && typeof options.onDragEnd === "function") {
      layer.on("dragend", function (event) {
        const newLatLng = event.target.getLatLng();
        options.onDragEnd(marker, newLatLng, layer);
      });
    }

    layer.bindPopup(popupContent);
    layer.addTo(options.markersLayer);
    options.markerLayerMap.set(markerKey, { layer: layer, marker: marker });
  }

  function clearAndRenderMarkers(options) {
    options.markersLayer.clearLayers();
    options.markerLayerMap.clear();
    (options.markers || []).forEach(function (marker) {
      addOrReplaceMarker({
        marker: marker,
        markersLayer: options.markersLayer,
        markerLayerMap: options.markerLayerMap,
        popupHtml: options.popupHtml,
        onEdit: options.onEdit,
        canDragMarker: options.canDragMarker,
        onDragEnd: options.onDragEnd,
      });
    });
  }

  function renderOperationalArea(options) {
    options.editableLayer.clearLayers();
    if (!options.geojson) {
      return;
    }

    const polygonLayer = L.geoJSON(options.geojson, {
      style: {
        color: options.strokeColor || "#2e7d32",
        fillColor: options.fillColor || "#66bb6a",
        fillOpacity: 0.14,
      },
    });

    polygonLayer.eachLayer(function (layer) {
      options.editableLayer.addLayer(layer);
    });

    const bounds = polygonLayer.getBounds();
    if (bounds.isValid() && options.map) {
      options.map.fitBounds(bounds.pad(0.2));
    }
  }

  function getCurrentPolygonGeoJson(editableLayer) {
    if (!editableLayer.getLayers().length) {
      return null;
    }
    const firstLayer = editableLayer.getLayers()[0];
    return firstLayer.toGeoJSON().geometry;
  }

  function populateTypeOptions(selectEl, options) {
    selectEl.innerHTML = "";
    (options || []).forEach(function (opt) {
      const option = document.createElement("option");
      option.value = String(opt.id);
      option.textContent = opt.name;
      selectEl.appendChild(option);
    });
  }

  function populateLineOptions(options) {
    const kind = options.kind;
    const lineSelect = options.lineSelect;
    const lines = options.lines || [];

    const expectedLineType = kind === "trap" ? "Trap" : "Bait";
    const validLines = lines.filter(function (line) {
      if (kind === "trap") {
        return line.type === "Trap";
      }
      return line.type !== "Trap";
    });

    lineSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select " + expectedLineType + " line";
    lineSelect.appendChild(placeholder);

    validLines.forEach(function (line) {
      const option = document.createElement("option");
      option.value = String(line.line_id);
      option.textContent = line.name;
      lineSelect.appendChild(option);
    });
  }

  function createActionMenu(actionMenu) {
    function hide() {
      if (actionMenu) {
        actionMenu.style.display = "none";
      }
    }

    function show(latlng, containerPoint) {
      if (!actionMenu) {
        return;
      }

      actionMenu.style.left = containerPoint.x + "px";
      actionMenu.style.top = containerPoint.y + "px";
      actionMenu.style.display = "block";
      return latlng;
    }

    return { show, hide };
  }

  function toggleOtherDetails(stationTypeSelect, otherDetailsWrap, otherDetailsInput) {
    const selected = stationTypeSelect.options[stationTypeSelect.selectedIndex];
    const isOther = selected && selected.textContent.trim().toLowerCase() === "other";
    otherDetailsWrap.classList.toggle("d-none", !isOther);
    otherDetailsInput.required = !!isOther;
    if (!isOther) {
      otherDetailsInput.value = "";
    }
  }

  return {
    createMap: createMap,
    createFeedback: createFeedback,
    requestJson: requestJson,
    addOrReplaceMarker: addOrReplaceMarker,
    clearAndRenderMarkers: clearAndRenderMarkers,
    renderOperationalArea: renderOperationalArea,
    getCurrentPolygonGeoJson: getCurrentPolygonGeoJson,
    populateTypeOptions: populateTypeOptions,
    populateLineOptions: populateLineOptions,
    createActionMenu: createActionMenu,
    toggleOtherDetails: toggleOtherDetails,
  };
})();
