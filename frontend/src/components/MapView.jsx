import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import RankingPanel from "./RankingPanel";
import { fetchScores, getScoreFromData } from "../services/scoresService";
import "maplibre-gl/dist/maplibre-gl.css";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
};

function extendBounds(bounds, coordinates) {
  if (typeof coordinates[0] === "number") {
    bounds.extend(coordinates);
    return;
  }

  coordinates.forEach((coord) => extendBounds(bounds, coord));
}

function MapView({
  selectedIndicator,
  compareMode,
  compareTarget,
  setSelectedZone,
  setCompareZone,
}) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const scoresRef = useRef({});
  const popupRef = useRef(null);

  const compareModeRef = useRef(compareMode);
  const compareTargetRef = useRef(compareTarget);

  useEffect(() => {
    compareModeRef.current = compareMode;
  }, [compareMode]);

  useEffect(() => {
    compareTargetRef.current = compareTarget;
  }, [compareTarget]);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [2.3522, 48.8566],
      zoom: 11,
    });

    mapRef.current = map;

    map.on("load", async () => {
      const scores = await fetchScores();
      scoresRef.current = scores;

      map.addSource("arrondissements", {
        type: "geojson",
        data: "/data/arrondissements.geojson",
      });

      map.addLayer({
        id: "arr-fill",
        type: "fill",
        source: "arrondissements",
        maxzoom: 11.8,
        paint: {
          "fill-color": "#76b7ae",
          "fill-opacity": 0.35,
        },
      });

      const irisResponse = await fetch("/data/iris_paris.geojson");
      const irisGeojson = await irisResponse.json();

      irisGeojson.features = irisGeojson.features.map((feature) => ({
        ...feature,
        properties: {
          ...feature.properties,
          score: getScoreFromData(
            scoresRef.current,
            feature.properties.code_iris,
            selectedIndicator
          ),
        },
      }));

      map.addSource("iris", {
        type: "geojson",
        data: irisGeojson,
        generateId: true,
      });

      map.addLayer({
        id: "iris-fill",
        type: "fill",
        source: "iris",
        minzoom: 11.5,
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "score"],
            0, "#f4f4f4",
            25, "#b7e4c7",
            50, "#74c69d",
            75, "#2a9d8f",
            100, "#264653",
          ],
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.85,
            0.62,
          ],
        },
      });

      map.addLayer({
        id: "iris-outline",
        type: "line",
        source: "iris",
        minzoom: 11.5,
        paint: {
          "line-color": "#ffffff",
          "line-width": 0.7,
          "line-opacity": 0.9,
        },
      });

      map.addLayer({
        id: "arr-outline",
        type: "line",
        source: "arrondissements",
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

      map.on("click", "arr-fill", (e) => {
        const feature = e.features[0];
        const bounds = new maplibregl.LngLatBounds();

        extendBounds(bounds, feature.geometry.coordinates);

        map.fitBounds(bounds, {
          padding: 90,
          duration: 900,
          maxZoom: 13.3,
        });
      });

      popupRef.current = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 12,
      });

      let hoveredId = null;

      map.on("mousemove", "iris-fill", (e) => {
        if (!e.features.length) return;

        const feature = e.features[0];
        const properties = feature.properties;

        if (hoveredId !== null) {
          map.setFeatureState(
            { source: "iris", id: hoveredId },
            { hover: false }
          );
        }

        hoveredId = feature.id;

        map.setFeatureState(
          { source: "iris", id: hoveredId },
          { hover: true }
        );

        map.getCanvas().style.cursor = "pointer";

        const score = getScoreFromData(
          scoresRef.current,
          properties.code_iris,
          selectedIndicator
        );

        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="map-tooltip">
              <strong>${properties.nom_iris || "Zone IRIS"}</strong>
              <span>${indicatorLabels[selectedIndicator]}</span>
              <b>${score} / 100</b>
            </div>
          `)
          .addTo(map);
      });

      map.on("mouseleave", "iris-fill", () => {
        if (hoveredId !== null) {
          map.setFeatureState(
            { source: "iris", id: hoveredId },
            { hover: false }
          );
        }

        hoveredId = null;
        map.getCanvas().style.cursor = "";
        popupRef.current.remove();
      });

      map.on("click", "iris-fill", (e) => {
        const clickedZone = e.features[0].properties;

        if (!compareModeRef.current) {
          setSelectedZone(clickedZone);
          setCompareZone(null);
          return;
        }

        if (compareTargetRef.current === "A") {
          setSelectedZone(clickedZone);
        } else {
          setCompareZone(clickedZone);
        }
      });
    });

    return () => map.remove();
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("iris")) return;

    fetch("/data/iris_paris.geojson")
      .then((res) => res.json())
      .then((geojson) => {
        geojson.features = geojson.features.map((feature) => ({
          ...feature,
          properties: {
            ...feature.properties,
            score: getScoreFromData(
              scoresRef.current,
              feature.properties.code_iris,
              selectedIndicator
            ),
          },
        }));

        map.getSource("iris").setData(geojson);
      });
  }, [selectedIndicator]);

  return (
    <main className="map-section">
      <div className="map-header">
        <h2>Carte des scores immobiliers</h2>
        <p>Clique sur un arrondissement pour zoomer · IRIS visibles au zoom</p>
      </div>

      <div ref={mapContainer} className="map-container" />

      <RankingPanel selectedIndicator={selectedIndicator} />
    </main>
  );
}

export default MapView;