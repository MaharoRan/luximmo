import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import RankingPanel from "./RankingPanel";
import { fetchArrondissements, fetchIrisScores } from "../services/scoresService";
import "maplibre-gl/dist/maplibre-gl.css";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
  prix_score: "Prix immobilier",
};

/* ── Dégradé rouge → jaune → vert ── */
const SCORE_COLORS = [
  0,   "#d32f2f",
  25,  "#ef6c00",
  50,  "#fbc02d",
  75,  "#66bb6a",
  100, "#2e7d32",
];

function extendBounds(bounds, coordinates) {
  if (typeof coordinates[0] === "number") {
    bounds.extend(coordinates);
    return;
  }
  coordinates.forEach((coord) => extendBounds(bounds, coord));
}

function formatEuroShort(value) {
  if (value == null || value === 0) return "–";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function MapView({
  selectedIndicator,
  compareMode,
  compareTarget,
  selectedZone,
  setSelectedZone,
  setCompareZone,
}) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const arrDataRef = useRef({});
  const irisDataRef = useRef({});
  const popupRef = useRef(null);
  const selectedIndicatorRef = useRef(selectedIndicator);

  const compareModeRef = useRef(compareMode);
  const compareTargetRef = useRef(compareTarget);

  useEffect(() => {
    compareModeRef.current = compareMode;
  }, [compareMode]);

  useEffect(() => {
    compareTargetRef.current = compareTarget;
  }, [compareTarget]);

  useEffect(() => {
    selectedIndicatorRef.current = selectedIndicator;
  }, [selectedIndicator]);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [2.3522, 48.8566],
      zoom: 11,
    });

    mapRef.current = map;

    map.on("load", async () => {
      const arrData = await fetchArrondissements();
      arrDataRef.current = arrData;
      
      const irisData = await fetchIrisScores();
      irisDataRef.current = irisData;

      /* ── Arrondissements source (enrichi avec scores) ── */
      const arrResponse = await fetch("/data/arrondissements.geojson");
      const arrGeojson = await arrResponse.json();

      arrGeojson.features = arrGeojson.features.map((feature) => {
        const arrNum = feature.properties.c_ar;
        const data = arrData[arrNum] || {};
        return {
          ...feature,
          properties: {
            ...feature.properties,
            arrondissement: arrNum,
            score: data[selectedIndicator] ?? 50,
            quality: data.quality ?? 50,
            culture: data.culture ?? 50,
            services: data.services ?? 50,
            transport: data.transport ?? 50,
            prix_score: data.prix_score ?? 50,
            loyer_median: data.loyer_median ?? 0,
            loyer_moyen: data.loyer_moyen ?? 0,
            loyer_maximum: data.loyer_maximum ?? 0,
          },
        };
      });

      map.addSource("arrondissements", {
        type: "geojson",
        data: arrGeojson,
        generateId: true,
      });

      /* ── IRIS source (enrichi avec scores) ── */
      const irisResponse = await fetch("/data/iris_paris.geojson");
      const irisGeojson = await irisResponse.json();

      irisGeojson.features = irisGeojson.features.map((feature) => {
        const codeIris = feature.properties.code_iris;
        const data = irisData[codeIris] || {};
        return {
          ...feature,
          properties: {
            ...feature.properties,
            code_iris: codeIris,
            score: data[selectedIndicator] ?? 50,
            quality: data.quality ?? 50,
            culture: data.culture ?? 50,
            services: data.services ?? 50,
            transport: data.transport ?? 50,
            prix_score: data.prix_score ?? 50,
            loyer_median: data.loyer_median ?? 0,
            loyer_moyen: data.loyer_moyen ?? 0,
            loyer_maximum: data.loyer_maximum ?? 0,
          },
        };
      });

      map.addSource("iris", {
        type: "geojson",
        data: irisGeojson,
        generateId: true,
      });

      map.addLayer({
        id: "arr-fill",
        type: "fill",
        source: "arrondissements",
        maxzoom: 13,
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "score"],
            ...SCORE_COLORS,
          ],
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.78,
            0.55,
          ],
        },
      });

      map.addLayer({
        id: "arr-outline",
        type: "line",
        source: "arrondissements",
        maxzoom: 13,
        paint: {
          "line-color": "#183247",
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            10, 1.8,
            12, 2.6,
            14, 3.6,
          ],
          "line-opacity": 0.95,
        },
      });

      /* ── Arrondissement labels ── */
      map.addLayer({
        id: "arr-labels",
        type: "symbol",
        source: "arrondissements",
        maxzoom: 13,
        layout: {
          "text-field": ["concat", ["to-string", ["get", "c_ar"]], "e"],
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            10, 11,
            13, 16,
          ],
          "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": "#183247",
          "text-halo-color": "rgba(255,255,255,0.85)",
          "text-halo-width": 1.5,
        },
      });

      /* ── IRIS Layers ── */
      map.addLayer({
        id: "iris-fill",
        type: "fill",
        source: "iris",
        minzoom: 13,
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "score"],
            ...SCORE_COLORS,
          ],
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.8,
            0.6,
          ],
        },
      });

      map.addLayer({
        id: "iris-outline",
        type: "line",
        source: "iris",
        minzoom: 13,
        paint: {
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.4,
        },
      });

      /* ── Shared popup ── */
      popupRef.current = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 12,
      });

      /* ── Shared Hover Logic ── */
      let hoveredArrId = null;
      let hoveredIrisId = null;

      const handleMouseMove = (sourceName, layerId, hoveredIdRef) => (e) => {
        if (!e.features.length) return;

        const feature = e.features[0];
        const props = feature.properties;

        if (hoveredIdRef.current !== null) {
          map.setFeatureState(
            { source: sourceName, id: hoveredIdRef.current },
            { hover: false }
          );
        }

        hoveredIdRef.current = feature.id;
        map.setFeatureState(
          { source: sourceName, id: hoveredIdRef.current },
          { hover: true }
        );

        map.getCanvas().style.cursor = "pointer";

        const indicator = selectedIndicatorRef.current;
        let tooltipValue;

        if (indicator === "prix_score") {
          tooltipValue = `${formatEuroShort(props.loyer_median)} (médian)`;
        } else {
          const score = props[indicator] ?? props.score ?? "–";
          tooltipValue = `${score} / 100`;
        }

        const title = props.nom_iris || props.l_ar || `${props.c_ar}e Arrondissement`;

        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="map-tooltip">
              <strong>${title}</strong>
              <span>${indicatorLabels[indicator]}</span>
              <b>${tooltipValue}</b>
            </div>
          `)
          .addTo(map);
      };

      const handleMouseLeave = (sourceName, hoveredIdRef) => () => {
        if (hoveredIdRef.current !== null) {
          map.setFeatureState(
            { source: sourceName, id: hoveredIdRef.current },
            { hover: false }
          );
        }
        hoveredIdRef.current = null;
        map.getCanvas().style.cursor = "";
        popupRef.current.remove();
      };

      const arrHoverRef = { current: null };
      const irisHoverRef = { current: null };

      map.on("mousemove", "arr-fill", handleMouseMove("arrondissements", "arr-fill", arrHoverRef));
      map.on("mouseleave", "arr-fill", handleMouseLeave("arrondissements", arrHoverRef));

      map.on("mousemove", "iris-fill", handleMouseMove("iris", "iris-fill", irisHoverRef));
      map.on("mouseleave", "iris-fill", handleMouseLeave("iris", irisHoverRef));

      /* ── Shared Click Logic ── */
      const handleZoneClick = (e, isIris) => {
        const feature = e.features[0];
        const props = feature.properties;

        // Zoom into feature
        const bounds = new maplibregl.LngLatBounds();
        extendBounds(bounds, feature.geometry.coordinates);
        map.fitBounds(bounds, {
          padding: 90,
          duration: 900,
          maxZoom: isIris ? 15 : 13.5, // Stop at 13.5 for arr, 15 for iris
        });

        const zone = isIris 
          ? { ...(irisDataRef.current[props.code_iris] || props), code_iris: props.code_iris, nom_iris: props.nom_iris }
          : { ...(arrDataRef.current[props.c_ar || props.arrondissement] || props), arrondissement: props.c_ar || props.arrondissement, l_ar: props.l_ar };

        if (!compareModeRef.current) {
          setSelectedZone(zone);
          setCompareZone(null);
          return;
        }

        if (compareTargetRef.current === "A") {
          setSelectedZone(zone);
        } else {
          setCompareZone(zone);
        }
      };

      map.on("click", "arr-fill", (e) => handleZoneClick(e, false));
      map.on("click", "iris-fill", (e) => handleZoneClick(e, true));
    });

    return () => map.remove();
  }, []);

  /* ── Update colors on indicator change ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("arrondissements")) return;

      fetch("/data/arrondissements.geojson")
        .then((res) => res.json())
        .then((geojson) => {
          geojson.features = geojson.features.map((feature) => {
            const arrNum = feature.properties.c_ar;
            const data = arrDataRef.current[arrNum] || {};
            return {
              ...feature,
              properties: {
                ...feature.properties,
                arrondissement: arrNum,
                score: data[selectedIndicator] ?? 50,
                quality: data.quality ?? 50,
                culture: data.culture ?? 50,
                services: data.services ?? 50,
                transport: data.transport ?? 50,
                prix_score: data.prix_score ?? 50,
                loyer_median: data.loyer_median ?? 0,
                loyer_moyen: data.loyer_moyen ?? 0,
                loyer_maximum: data.loyer_maximum ?? 0,
              },
            };
          });

          map.getSource("arrondissements").setData(geojson);
        });

      if (map.getSource("iris")) {
        fetch("/data/iris_paris.geojson")
          .then((res) => res.json())
          .then((geojson) => {
            geojson.features = geojson.features.map((feature) => {
              const codeIris = feature.properties.code_iris;
              const data = irisDataRef.current[codeIris] || {};
              return {
                ...feature,
                properties: {
                  ...feature.properties,
                  code_iris: codeIris,
                  score: data[selectedIndicator] ?? 50,
                  quality: data.quality ?? 50,
                  culture: data.culture ?? 50,
                  services: data.services ?? 50,
                  transport: data.transport ?? 50,
                  prix_score: data.prix_score ?? 50,
                  loyer_median: data.loyer_median ?? 0,
                  loyer_moyen: data.loyer_moyen ?? 0,
                  loyer_maximum: data.loyer_maximum ?? 0,
                },
              };
            });

            map.getSource("iris").setData(geojson);
          });
      }
  }, [selectedIndicator]);

  return (
    <main className="map-section">
      <div className="map-header">
        <h2>Carte des scores immobiliers</h2>
        <p>Clique sur un arrondissement pour zoomer et voir les détails</p>
      </div>

      <div ref={mapContainer} className="map-container" />

      <RankingPanel selectedIndicator={selectedIndicator} />
    </main>
  );
}

export default MapView;