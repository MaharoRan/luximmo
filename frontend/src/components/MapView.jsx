import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import RankingPanel from "./RankingPanel";
import LayerControl from "./LayerControl";
import {
  fetchArrondissements,
  fetchIrisScores,
  formatEuro,
} from "../services/scoresService";
import "maplibre-gl/dist/maplibre-gl.css";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
  prix_score: "Prix immobilier",
};

const SCORE_COLORS = [
  0, "#d32f2f",
  25, "#ef6c00",
  50, "#fbc02d",
  75, "#66bb6a",
  100, "#2e7d32",
];

function extendBounds(bounds, coordinates) {
  if (typeof coordinates[0] === "number") {
    bounds.extend(coordinates);
    return;
  }

  coordinates.forEach((coord) => extendBounds(bounds, coord));
}

function getTooltipValue(properties, indicator) {
  if (indicator === "prix_score") {
    return `${formatEuro(properties.loyer_median)} médian`;
  }

  const score = properties[indicator] ?? properties.score ?? "–";
  return `${score} / 100`;
}

function enrichArrondissementsGeojson(geojson, arrData, indicator) {
  return {
    ...geojson,
    features: geojson.features.map((feature) => {
      const arrNum = Number(feature.properties.c_ar);
      const data = arrData[arrNum] || {};

      return {
        ...feature,
        id: arrNum,
        properties: {
          ...feature.properties,
          arrondissement: arrNum,
          score: data[indicator] ?? 50,
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
    }),
  };
}

function enrichIrisGeojson(geojson, irisData, indicator) {
  return {
    ...geojson,
    features: geojson.features.map((feature) => {
      const codeIris = feature.properties.code_iris;
      const data = irisData[codeIris] || {};

      return {
        ...feature,
        id: Number(codeIris),
        properties: {
          ...feature.properties,
          code_iris: codeIris,
          score: data[indicator] ?? 50,
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
    }),
  };
}

function MapView({
  selectedIndicator,
  selectedYear,
  compareMode,
  compareTarget,
  selectedZone,
  compareZone,
  setSelectedZone,
  setCompareZone,
}) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const arrDataRef = useRef({});
  const irisDataRef = useRef({});
  const popupRef = useRef(null);

  const [activeLayers, setActiveLayers] = useState([]);

  const compareModeRef = useRef(compareMode);
  const compareTargetRef = useRef(compareTarget);
  const selectedIndicatorRef = useRef(selectedIndicator);
  const selectedYearRef = useRef(selectedYear);
  const selectedZoneRef = useRef(selectedZone);
  const compareZoneRef = useRef(compareZone);

  useEffect(() => {
    selectedZoneRef.current = selectedZone;
    compareZoneRef.current = compareZone;
    updateOutlineFilters();
  }, [selectedZone, compareZone]);

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
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer("chantiers-fill")) {
      const visibility = activeLayers.includes("chantiers") ? "visible" : "none";
      map.setLayoutProperty("chantiers-fill", "visibility", visibility);
      map.setLayoutProperty("chantiers-icon", "visibility", visibility);
    }
    
    if (map.getLayer("trafic-line")) {
      const visibility = activeLayers.includes("trafic") ? "visible" : "none";
      map.setLayoutProperty("trafic-line", "visibility", visibility);
    }
  }, [activeLayers]);

  useEffect(() => {
    selectedYearRef.current = selectedYear;
  }, [selectedYear]);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [2.3522, 48.8566],
      zoom: 11,
    });

    mapRef.current = map;

    map.on("load", async () => {
      const [arrData, irisData, arrResponse, irisResponse] = await Promise.all([
        fetchArrondissements(selectedYearRef.current),
        fetchIrisScores(selectedYearRef.current),
        fetch("/data/arrondissements.geojson"),
        fetch("/data/iris_paris.geojson"),
      ]);

      arrDataRef.current = arrData;
      irisDataRef.current = irisData;

      const arrGeojsonRaw = await arrResponse.json();
      const irisGeojsonRaw = await irisResponse.json();

      const arrGeojson = enrichArrondissementsGeojson(
        arrGeojsonRaw,
        arrDataRef.current,
        selectedIndicatorRef.current
      );

      const irisGeojson = enrichIrisGeojson(
        irisGeojsonRaw,
        irisDataRef.current,
        selectedIndicatorRef.current
      );

      map.addSource("arrondissements", {
        type: "geojson",
        data: arrGeojson
      });

      map.addSource("iris", {
        type: "geojson",
        data: irisGeojson
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

      map.addLayer({
        id: "arr-labels",
        type: "symbol",
        source: "arrondissements",
        maxzoom: 13,
        layout: {
          "text-field": ["concat", ["to-string", ["get", "c_ar"]], "e"],
          "text-size": [
            "interpolate",
            ["linear"],
            ["zoom"],
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

      // --- NEW: Chantiers Layer ---
      map.addSource("chantiers_live", {
        type: "geojson",
        data: "/data/chantiers_live.geojson",
      });

      map.addLayer({
        id: "chantiers-fill",
        type: "fill",
        source: "chantiers_live",
        paint: {
          "fill-color": "#ec4899", // pink
          "fill-opacity": 0.4,
        },
        layout: {
          "visibility": "none",
        }
      });

      map.addLayer({
        id: "chantiers-icon",
        type: "symbol",
        source: "chantiers_live",
        layout: {
          "text-field": "🚧",
          "text-size": 16,
          "text-allow-overlap": true,
          "visibility": "none",
        },
        paint: {
          "text-color": "#fbbf24", // yellow
          "text-halo-color": "#000000", // black border
          "text-halo-width": 2
        }
      });

      // --- NEW: Trafic Layer ---
      map.addSource("trafic_live", {
        type: "geojson",
        data: "/data/trafic_live.geojson",
      });

      map.addLayer({
        id: "trafic-line",
        type: "line",
        source: "trafic_live",
        layout: {
          "line-join": "round",
          "line-cap": "round",
          "visibility": "none",
        },
        paint: {
          "line-width": 4,
          "line-color": [
            "match",
            ["get", "etat_trafic"],
            "Fluide", "#10b981",       // green
            "Pré-saturé", "#f59e0b",   // orange
            "Saturé", "#ef4444",       // red
            "Bloqué", "#7f1d1d",       // dark red
            "#9ca3af"                  // Inconnu / default gray
          ]
        }
      });

      // Highlight overlays driven by feature-state
      ["arrondissements", "iris"].forEach((source) => {
        map.addLayer({
          id: `${source}-highlight-fill`,
          type: "fill",
          source: source,
          paint: {
            "fill-color": [
              "case",
              ["boolean", ["feature-state", "isZoneA"], false], "#3b82f6",
              ["boolean", ["feature-state", "isZoneB"], false], "#ec4899",
              "transparent"
            ],
            "fill-opacity": 0.3,
          },
        });

        map.addLayer({
          id: `${source}-highlight-outline`,
          type: "line",
          source: source,
          paint: {
            "line-color": [
              "case",
              ["boolean", ["feature-state", "isZoneA"], false], "#3b82f6",
              ["boolean", ["feature-state", "isZoneB"], false], "#ec4899",
              "transparent"
            ],
            "line-width": 5,
          },
        });
      });

      popupRef.current = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 12,
      });

      const arrHoverRef = { current: null };
      const irisHoverRef = { current: null };

      const handleMouseMove = (sourceName, hoveredRef) => (e) => {
        if (!e.features.length) return;

        const feature = e.features[0];
        const props = feature.properties;

        if (hoveredRef.current !== null) {
          map.setFeatureState(
            { source: sourceName, id: hoveredRef.current },
            { hover: false }
          );
        }

        hoveredRef.current = feature.id;

        map.setFeatureState(
          { source: sourceName, id: hoveredRef.current },
          { hover: true }
        );

        map.getCanvas().style.cursor = "pointer";

        const indicator = selectedIndicatorRef.current;
        const title =
          props.nom_iris ||
          props.l_ar ||
          `${props.arrondissement || props.c_ar}e Arrondissement`;

        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="map-tooltip">
              <strong>${title}</strong>
              <span>${indicatorLabels[indicator]}</span>
              <b>${getTooltipValue(props, indicator)}</b>
            </div>
          `)
          .addTo(map);
      };

      const handleMouseLeave = (sourceName, hoveredRef) => () => {
        if (hoveredRef.current !== null) {
          map.setFeatureState(
            { source: sourceName, id: hoveredRef.current },
            { hover: false }
          );
        }

        hoveredRef.current = null;
        map.getCanvas().style.cursor = "";
        popupRef.current.remove();
      };

      map.on("mousemove", "arr-fill", handleMouseMove("arrondissements", arrHoverRef));
      map.on("mouseleave", "arr-fill", handleMouseLeave("arrondissements", arrHoverRef));

      map.on("mousemove", "iris-fill", handleMouseMove("iris", irisHoverRef));
      map.on("mouseleave", "iris-fill", handleMouseLeave("iris", irisHoverRef));

      const handleZoneClick = (e, isIris) => {
        const feature = e.features[0];
        const props = feature.properties;

        if (!compareModeRef.current) {
          const bounds = new maplibregl.LngLatBounds();
          extendBounds(bounds, feature.geometry.coordinates);

          map.fitBounds(bounds, {
            padding: 90,
            duration: 900,
            maxZoom: isIris ? 15 : 13.5,
          });
        }

        const zone = isIris
          ? {
              ...(irisDataRef.current[props.code_iris] || props),
              code_iris: props.code_iris,
              nom_iris: props.nom_iris,
            }
          : {
              ...(arrDataRef.current[props.arrondissement || props.c_ar] || props),
              arrondissement: props.arrondissement || props.c_ar,
              l_ar: props.l_ar,
            };

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

  const previousHighlightARef = useRef(null);
  const previousHighlightBRef = useRef(null);

  const updateOutlineFilters = () => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const zoneA = selectedZoneRef.current;
    const zoneB = compareZoneRef.current;

    // Clear previous feature states
    if (previousHighlightARef.current) {
      map.setFeatureState(previousHighlightARef.current, { isZoneA: false });
      previousHighlightARef.current = null;
    }
    if (previousHighlightBRef.current) {
      map.setFeatureState(previousHighlightBRef.current, { isZoneB: false });
      previousHighlightBRef.current = null;
    }

    // Set new feature states
    if (zoneA) {
      const isIris = zoneA.code_iris !== undefined;
      const source = isIris ? "iris" : "arrondissements";
      const id = isIris ? Number(zoneA.code_iris) : Number(zoneA.arrondissement || zoneA.c_ar);
      
      const featureIdentifier = { source, id };
      map.setFeatureState(featureIdentifier, { isZoneA: true });
      previousHighlightARef.current = featureIdentifier;
    }

    if (zoneB) {
      const isIris = zoneB.code_iris !== undefined;
      const source = isIris ? "iris" : "arrondissements";
      const id = isIris ? Number(zoneB.code_iris) : Number(zoneB.arrondissement || zoneB.c_ar);

      const featureIdentifier = { source, id };
      map.setFeatureState(featureIdentifier, { isZoneB: true });
      previousHighlightBRef.current = featureIdentifier;
    }
  };

  useEffect(() => {
    const map = mapRef.current;

    if (
      !map ||
      !map.getSource("arrondissements") ||
      !map.getSource("iris")
    ) {
      return;
    }

    selectedIndicatorRef.current = selectedIndicator;
    selectedYearRef.current = selectedYear;

    Promise.all([
      fetchArrondissements(selectedYear),
      fetchIrisScores(selectedYear),
      fetch("/data/arrondissements.geojson"),
      fetch("/data/iris_paris.geojson"),
    ]).then(async ([arrData, irisData, arrResponse, irisResponse]) => {
      arrDataRef.current = arrData;
      irisDataRef.current = irisData;

      const arrGeojsonRaw = await arrResponse.json();
      const irisGeojsonRaw = await irisResponse.json();

      map.getSource("arrondissements").setData(
        enrichArrondissementsGeojson(arrGeojsonRaw, arrData, selectedIndicator)
      );

      map.getSource("iris").setData(
        enrichIrisGeojson(irisGeojsonRaw, irisData, selectedIndicator)
      );
    });
  }, [selectedIndicator, selectedYear]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("arrondissements")) return;

    const updateData = async () => {
      const arrData = await fetchArrondissements(selectedYear);
      arrDataRef.current = arrData;
      
      const irisData = await fetchIrisScores(selectedYear);
      irisDataRef.current = irisData;
      
      // Update Arrondissement Source
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

      map.getSource("arrondissements").setData(arrGeojson);
      
      // Update IRIS Source
      if (map.getSource("iris")) {
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
         map.getSource("iris").setData(irisGeojson);
      }
      
      // Update selected/compare zones
      if (selectedZone) {
        const isIris = !!selectedZone.code_iris;
        const id = isIris ? selectedZone.code_iris : selectedZone.arrondissement;
        const newData = isIris ? irisData[id] : arrData[id];
        if (newData) {
          setSelectedZone(isIris ? { ...newData, code_iris: id, nom_iris: selectedZone.nom_iris } : { ...newData, arrondissement: id, l_ar: selectedZone.l_ar });
        }
      }
      if (compareZone) {
        const isIris = !!compareZone.code_iris;
        const id = isIris ? compareZone.code_iris : compareZone.arrondissement;
        const newData = isIris ? irisData[id] : arrData[id];
        if (newData) {
          setCompareZone(isIris ? { ...newData, code_iris: id, nom_iris: compareZone.nom_iris } : { ...newData, arrondissement: id, l_ar: compareZone.l_ar });
        }
      }
    };
    
    updateData();
  }, [selectedYear]);

  const toggleLayer = (layerId) => {
    setActiveLayers(prev => 
      prev.includes(layerId) ? prev.filter(l => l !== layerId) : [...prev, layerId]
    );
  };

  return (
    <main className="map-section">
      <div className="map-header">
        <h2 className="map-title">{indicatorLabels[selectedIndicator]}</h2>
      </div>

      <div className="map-wrapper">
        <div ref={mapContainer} className="map-container" />
        <LayerControl activeLayers={activeLayers} toggleLayer={toggleLayer} />
      </div>

      {compareMode && (
        <RankingPanel
          selectedIndicator={selectedIndicator}
          selectedYear={selectedYear}
        />
      )}
    </main>
  );
}

export default MapView;