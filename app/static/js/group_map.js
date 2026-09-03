(function () {
  const config = window.groupMapConfig || {};
  const mapContainer = document.getElementById("operations-map");
  if (!mapContainer) {
    return;
  }

  const feedbackEl = document.getElementById("map-feedback");
  const saveAreaBtn = document.getElementById("save-area-btn");
  const actionMenu = document.getElementById("map-action-menu");

  const markerModalEl = document.getElementById("markerModal");
  const markerForm = document.getElementById("marker-form");
  const markerModalTitle = document.getElementById("markerModalTitle");
  const markerIdInput = document.getElementById("marker-id");
  const markerKindInput = document.getElementById("marker-kind");
  const codeInput = document.getElementById("marker-code");
  const lineSelect = document.getElementById("marker-line");
  const trapTypeWrap = document.getElementById("trap-type-wrap");
  const trapTypeSelect = document.getElementById("trap-type-id");
  const stationTypeWrap = document.getElementById("station-type-wrap");
  const stationTypeSelect = document.getElementById("station-type-id");
  const otherDetailsWrap = document.getElementById("other-details-wrap");
  const otherDetailsInput = document.getElementById("other-type-details");
  const latInput = document.getElementById("marker-latitude");
  const lngInput = document.getElementById("marker-longitude");
  const markerStatusInput = document.getElementById("marker-status");

  const markerModal = markerModalEl ? new bootstrap.Modal(markerModalEl) : null;

  let mapData = null;
  let pendingLatLng = null;
  let markerLayerMap = new Map();

  const mapBundle = window.MapCommon.createMap({
    containerId: "operations-map",
    enableDrawControl: !!config.canEdit,
    polygonStrokeColor: "#2e7d32",
  });
  const map = mapBundle.map;
  const markersLayer = mapBundle.markersLayer;
  const editableLayer = mapBundle.editableLayer;

  const feedback = window.MapCommon.createFeedback(feedbackEl);
  const actionMenuUi = window.MapCommon.createActionMenu(actionMenu);

  function markerPopupHtml(marker) {
    const title = marker.kind === "trap" ? "Trap" : "Bait Station";
    const details = marker.other_type_details ? `<div><strong>Other details:</strong> ${marker.other_type_details}</div>` : "";
    const editBtn = config.canEdit ? `<button class="btn btn-sm btn-outline-primary mt-2" type="button" data-marker-id="${marker.id}">Edit</button>` : "";

    return [
      `<div class="small">`,
      `<div><strong>${title}:</strong> ${marker.code}</div>`,
      `<div><strong>Type:</strong> ${marker.type_name || "-"}</div>`,
      `<div><strong>Status:</strong> ${marker.status || "-"}</div>`,
      `<div><strong>Line:</strong> ${marker.line_name || "-"}</div>`,
      `<div><strong>Lat/Lng:</strong> ${Number(marker.latitude).toFixed(6)}, ${Number(marker.longitude).toFixed(6)}</div>`,
      details,
      editBtn,
      `</div>`,
    ].join("");
  }

  function addMarkerToMap(marker) {
    window.MapCommon.addOrReplaceMarker({
      marker: marker,
      markersLayer: markersLayer,
      markerLayerMap: markerLayerMap,
      popupHtml: markerPopupHtml,
      canDragMarker: !!config.canEdit,
      onDragEnd: function (draggedMarker, newLatLng) {
        if (!config.canEdit) {
          return;
        }
        draggedMarker.latitude = Number(newLatLng.lat);
        draggedMarker.longitude = Number(newLatLng.lng);
        setMarkerModalModeEdit(draggedMarker);
        markerModal.show();
      },
      onEdit: function (selectedMarker) {
        setMarkerModalModeEdit(selectedMarker);
        markerModal.show();
      },
    });
  }

  function clearAndRenderMarkers(markers) {
    window.MapCommon.clearAndRenderMarkers({
      markersLayer: markersLayer,
      markerLayerMap: markerLayerMap,
      markers: markers || [],
      popupHtml: markerPopupHtml,
      canDragMarker: !!config.canEdit,
      onDragEnd: function (draggedMarker, newLatLng) {
        if (!config.canEdit) {
          return;
        }
        draggedMarker.latitude = Number(newLatLng.lat);
        draggedMarker.longitude = Number(newLatLng.lng);
        setMarkerModalModeEdit(draggedMarker);
        markerModal.show();
      },
      onEdit: function (selectedMarker) {
        setMarkerModalModeEdit(selectedMarker);
        markerModal.show();
      },
    });
  }

  function renderOperationalArea(geojson) {
    window.MapCommon.renderOperationalArea({
      editableLayer: editableLayer,
      geojson: geojson,
      map: map,
      strokeColor: "#2e7d32",
      fillColor: "#66bb6a",
    });
  }

  function getCurrentPolygonGeoJson() {
    return window.MapCommon.getCurrentPolygonGeoJson(editableLayer);
  }

  function populateTypeOptions(selectEl, options) {
    window.MapCommon.populateTypeOptions(selectEl, options || []);
  }

  function populateLineOptions(kind) {
    window.MapCommon.populateLineOptions({
      kind: kind,
      lineSelect: lineSelect,
      lines: mapData.lines || [],
    });
  }

  function setMarkerModalModeCreate(kind, latlng) {
    markerIdInput.value = "";
    markerKindInput.value = kind;
    markerModalTitle.textContent = kind === "trap" ? "Add Trap" : "Add Bait Station";

    trapTypeWrap.classList.toggle("d-none", kind !== "trap");
    trapTypeSelect.required = kind === "trap";
    stationTypeWrap.classList.toggle("d-none", kind !== "bait_station");
    stationTypeSelect.required = kind === "bait_station";

    otherDetailsWrap.classList.add("d-none");
    otherDetailsInput.value = "";

    latInput.value = Number(latlng.lat).toFixed(6);
    lngInput.value = Number(latlng.lng).toFixed(6);
    markerStatusInput.value = "Active";
    codeInput.value = "";
    lineSelect.value = "";

    populateLineOptions(kind);

    if (kind === "trap" && trapTypeSelect.options.length) {
      trapTypeSelect.selectedIndex = 0;
    }
    if (kind === "bait_station" && stationTypeSelect.options.length) {
      stationTypeSelect.selectedIndex = 0;
      toggleOtherDetails();
    }
  }

  function setMarkerModalModeEdit(marker) {
    markerIdInput.value = marker.id;
    markerKindInput.value = marker.kind;
    markerStatusInput.value = marker.status || "Active";
    markerModalTitle.textContent = marker.kind === "trap" ? "Edit Trap" : "Edit Bait Station";

    trapTypeWrap.classList.toggle("d-none", marker.kind !== "trap");
    trapTypeSelect.required = marker.kind === "trap";
    stationTypeWrap.classList.toggle("d-none", marker.kind !== "bait_station");
    stationTypeSelect.required = marker.kind === "bait_station";

    latInput.value = Number(marker.latitude).toFixed(6);
    lngInput.value = Number(marker.longitude).toFixed(6);
    codeInput.value = marker.code;

    populateLineOptions(marker.kind);
    lineSelect.value = String(marker.line_id);

    if (marker.kind === "trap") {
      populateTypeOptions(trapTypeSelect, mapData.trap_types || []);
      const trapTypeRow = (mapData.trap_types || []).find((t) => t.name === marker.type_name);
      if (trapTypeRow) {
        trapTypeSelect.value = String(trapTypeRow.id);
      }
    } else {
      populateTypeOptions(stationTypeSelect, mapData.bait_station_types || []);
      const stationTypeRow = (mapData.bait_station_types || []).find((t) => t.name === marker.type_name);
      if (stationTypeRow) {
        stationTypeSelect.value = String(stationTypeRow.id);
      }
      otherDetailsInput.value = marker.other_type_details || "";
      toggleOtherDetails();
    }
  }

  function hideActionMenu() {
    actionMenuUi.hide();
  }

  function showActionMenu(latlng, containerPoint) {
    if (!actionMenu || !config.canEdit) {
      return;
    }

    pendingLatLng = actionMenuUi.show(latlng, containerPoint);
  }

  function toggleOtherDetails() {
    window.MapCommon.toggleOtherDetails(stationTypeSelect, otherDetailsWrap, otherDetailsInput);
  }

  async function requestJson(url, options) {
    return window.MapCommon.requestJson(url, options);
  }

  async function loadMapData() {
    const data = await requestJson(config.dataUrl, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    mapData = data;
    populateTypeOptions(trapTypeSelect, data.trap_types || []);
    populateTypeOptions(stationTypeSelect, data.bait_station_types || []);

    renderOperationalArea(data.operational_area || null);
    clearAndRenderMarkers(data.markers || []);
  }

  async function saveOperationalArea() {
    const polygon = getCurrentPolygonGeoJson();
    await requestJson(config.saveAreaUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ polygon }),
    });
    feedback.show("Operational area saved.", "success");
  }

  async function createMarker(payload) {
    const data = await requestJson(config.createMarkerUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (data.marker) {
      addMarkerToMap(data.marker);
      feedback.show("Marker created successfully.", "success");
    }
  }

  async function updateMarker(markerId, payload) {
    const url = `${config.createMarkerUrl}/${markerId}`;
    const data = await requestJson(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (data.marker) {
      addMarkerToMap(data.marker);
      feedback.show("Marker updated successfully.", "success");
    }
  }

  map.on(L.Draw.Event.CREATED, function (event) {
    editableLayer.clearLayers();
    editableLayer.addLayer(event.layer);
    feedback.hide();
  });

  map.on(L.Draw.Event.EDITED, function () {
    feedback.hide();
  });

  map.on(L.Draw.Event.DELETED, function () {
    feedback.hide();
  });

  map.on("dblclick", function (event) {
    showActionMenu(event.latlng, map.latLngToContainerPoint(event.latlng));
  });

  map.on("click", function () {
    hideActionMenu();
  });

  document.addEventListener("click", function (event) {
    if (actionMenu && actionMenu.style.display === "block" && !actionMenu.contains(event.target)) {
      hideActionMenu();
    }
  });

  if (actionMenu) {
    actionMenu.addEventListener("click", function (event) {
      const button = event.target.closest("button[data-kind]");
      if (!button || !pendingLatLng) {
        return;
      }

      const kind = button.getAttribute("data-kind");
      setMarkerModalModeCreate(kind, pendingLatLng);
      hideActionMenu();
      markerModal.show();
    });
  }

  if (stationTypeSelect) {
    stationTypeSelect.addEventListener("change", toggleOtherDetails);
  }

  if (saveAreaBtn) {
    saveAreaBtn.addEventListener("click", async function () {
      try {
        feedback.hide();
        await saveOperationalArea();
      } catch (error) {
        feedback.show(error.message, "danger");
      }
    });
  }

  if (markerForm) {
    markerForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      const markerId = markerIdInput.value;
      const isEdit = !!markerId;

      const payload = {
        kind: markerKindInput.value,
        code: codeInput.value.trim(),
        line_id: lineSelect.value,
        latitude: latInput.value,
        longitude: lngInput.value,
        status: markerStatusInput.value,
      };

      if (payload.kind === "trap") {
        payload.trap_type_id = trapTypeSelect.value;
      } else {
        payload.bait_station_type_id = stationTypeSelect.value;
        payload.other_type_details = otherDetailsInput.value.trim();
      }

      try {
        feedback.hide();
        if (isEdit) {
          await updateMarker(markerId, payload);
        } else {
          await createMarker(payload);
        }
        markerModal.hide();
      } catch (error) {
        feedback.show(error.message, "danger");
      }
    });
  }

  loadMapData().catch((error) => feedback.show(error.message, "danger"));
})();
