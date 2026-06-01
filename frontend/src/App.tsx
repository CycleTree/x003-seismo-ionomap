import { useEffect, useRef, useState } from "react";
import maplibregl, { GeoJSONSource, Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const defaultApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const sourceId = "anomaly-grid";
const apiStorageKey = "seismo-ionomap.api-base-url";

type GridFeature = {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
  properties: {
    time: string;
    grid_lat_deg: number;
    grid_lon_deg: number;
    sample_count: number;
    median_vtec_tecu: number;
    baseline_vtec_tecu: number;
    delta_vtec_tecu: number;
    z_score: number;
    abs_z_score: number;
  };
};

type FeatureCollection = {
  type: "FeatureCollection";
  features: GridFeature[];
};

type ApiResponse = {
  time: string;
  featureCollection: FeatureCollection;
  stats: {
    cellCount: number;
    maxAbsZScore: number;
    meanZScore: number;
  };
};

function getFillColorExpression() {
  return [
    "interpolate",
    ["linear"],
    ["get", "z_score"],
    -3,
    "#0b3c5d",
    -1,
    "#65a9d7",
    0,
    "#f8fafc",
    1,
    "#f59e0b",
    3,
    "#b91c1c",
  ] as maplibregl.ExpressionSpecification;
}

export default function App() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const [apiBaseUrlInput, setApiBaseUrlInput] = useState<string>(() => {
    if (typeof window === "undefined") {
      return defaultApiBaseUrl;
    }
    return window.localStorage.getItem(apiStorageKey) ?? defaultApiBaseUrl;
  });
  const [apiBaseUrl, setApiBaseUrl] = useState<string>(() => {
    if (typeof window === "undefined") {
      return defaultApiBaseUrl;
    }
    return window.localStorage.getItem(apiStorageKey) ?? defaultApiBaseUrl;
  });
  const [times, setTimes] = useState<string[]>([]);
  const [selectedTime, setSelectedTime] = useState<string>("");
  const [stats, setStats] = useState<ApiResponse["stats"] | null>(null);
  const [rawFeatureCollection, setRawFeatureCollection] = useState<FeatureCollection>({
    type: "FeatureCollection",
    features: [],
  });
  const [minSampleCount, setMinSampleCount] = useState<number>(1);
  const [minAbsZScore, setMinAbsZScore] = useState<number>(0);
  const [fillOpacity, setFillOpacity] = useState<number>(0.78);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [141.0, 38.0],
      zoom: 4.5,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.on("load", () => {
      map.addSource(sourceId, {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });
      map.addLayer({
        id: "anomaly-fill",
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": getFillColorExpression(),
          "fill-opacity": fillOpacity,
        },
      });
      map.addLayer({
        id: "anomaly-outline",
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#0f172a",
          "line-width": 0.35,
          "line-opacity": 0.35,
        },
      });

      map.on("click", "anomaly-fill", (event) => {
        const feature = event.features?.[0];
        if (!feature) {
          return;
        }
        const props = feature.properties as Record<string, string | number>;
        new maplibregl.Popup({ closeButton: false, offset: 8 })
          .setLngLat(event.lngLat)
          .setHTML(
            [
              `<strong>${String(props.time)}</strong>`,
              `z-score: ${Number(props.z_score).toFixed(2)}`,
              `delta TEC: ${Number(props.delta_vtec_tecu).toFixed(2)}`,
              `median VTEC: ${Number(props.median_vtec_tecu).toFixed(2)}`,
              `samples: ${Number(props.sample_count)}`,
            ].join("<br />"),
          )
          .addTo(map);
      });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [fillOpacity]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(apiStorageKey, apiBaseUrl);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    const source = mapRef.current?.getSource(sourceId) as GeoJSONSource | undefined;
    if (!source) {
      return;
    }
    source.setData({
      type: "FeatureCollection",
      features: rawFeatureCollection.features.filter((feature) => {
        return (
          feature.properties.sample_count >= minSampleCount &&
          Math.abs(feature.properties.z_score) >= minAbsZScore
        );
      }),
    });
  }, [rawFeatureCollection, minSampleCount, minAbsZScore]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("anomaly-fill")) {
      return;
    }
    map.setPaintProperty("anomaly-fill", "fill-opacity", fillOpacity);
  }, [fillOpacity]);

  useEffect(() => {
    async function loadTimes() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${apiBaseUrl}/api/anomaly-grid/times`);
        if (!response.ok) {
          throw new Error(`Failed to fetch available times: ${response.status}`);
        }
        const payload = (await response.json()) as { times: string[] };
        setTimes(payload.times);
        if (payload.times.length > 0) {
          setSelectedTime((currentSelectedTime) =>
            currentSelectedTime && payload.times.includes(currentSelectedTime)
              ? currentSelectedTime
              : payload.times[payload.times.length - 1],
          );
        }
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    void loadTimes();
  }, [apiBaseUrl]);

  useEffect(() => {
    async function loadGrid() {
      if (!selectedTime || !mapRef.current) {
        return;
      }
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${apiBaseUrl}/api/anomaly-grid?time=${encodeURIComponent(selectedTime)}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch anomaly grid: ${response.status}`);
        }
        const payload = (await response.json()) as ApiResponse;
        setStats(payload.stats);
        setRawFeatureCollection(payload.featureCollection);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    void loadGrid();
  }, [apiBaseUrl, selectedTime]);

  function handleApplyApiBaseUrl() {
    const normalizedValue = apiBaseUrlInput.trim().replace(/\/+$/, "");
    if (!normalizedValue) {
      setError("API URL is empty");
      return;
    }
    setApiBaseUrl(normalizedValue);
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top left, rgba(234, 179, 8, 0.18), transparent 28%), linear-gradient(135deg, #07111f 0%, #10243e 50%, #18314f 100%)",
        color: "#e2e8f0",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(280px, 360px) 1fr",
          minHeight: "100vh",
        }}
      >
        <aside
          style={{
            padding: "1.25rem",
            borderRight: "1px solid rgba(148, 163, 184, 0.15)",
            background: "rgba(7, 17, 31, 0.72)",
            backdropFilter: "blur(18px)",
          }}
        >
          <p style={{ margin: 0, letterSpacing: "0.14em", fontSize: "0.75rem", textTransform: "uppercase", color: "#fbbf24" }}>
            Seismo Ionomap
          </p>
          <h1 style={{ marginTop: "0.5rem", marginBottom: "0.75rem", fontSize: "2rem", lineHeight: 1.05 }}>
            TEC Anomaly Grid
          </h1>
          <p style={{ marginTop: 0, color: "#cbd5e1", lineHeight: 1.55 }}>
            <code>anomaly_grid.parquet</code> を GeoJSON 化して、z-score を格子塗りで表示しています。
          </p>

          <section
            style={{
              marginTop: "1.25rem",
              padding: "1rem",
              borderRadius: "1rem",
              background: "rgba(15, 23, 42, 0.62)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
            }}
          >
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Viewer Settings</h2>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#cbd5e1", marginBottom: "0.45rem" }}>
              API URL
            </label>
            <input
              value={apiBaseUrlInput}
              onChange={(event) => setApiBaseUrlInput(event.target.value)}
              style={{
                width: "100%",
                padding: "0.8rem 0.9rem",
                borderRadius: "0.8rem",
                border: "1px solid rgba(148, 163, 184, 0.25)",
                background: "rgba(15, 23, 42, 0.9)",
                color: "#f8fafc",
                boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", gap: "0.65rem", marginTop: "0.75rem" }}>
              <button
                onClick={handleApplyApiBaseUrl}
                style={{
                  border: 0,
                  borderRadius: "0.75rem",
                  padding: "0.7rem 0.9rem",
                  background: "#f59e0b",
                  color: "#111827",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Apply
              </button>
              <button
                onClick={() => {
                  setApiBaseUrlInput(defaultApiBaseUrl);
                  setApiBaseUrl(defaultApiBaseUrl);
                }}
                style={{
                  border: "1px solid rgba(148, 163, 184, 0.25)",
                  borderRadius: "0.75rem",
                  padding: "0.7rem 0.9rem",
                  background: "rgba(15, 23, 42, 0.9)",
                  color: "#f8fafc",
                  cursor: "pointer",
                }}
              >
                Reset
              </button>
            </div>
            <p style={{ margin: "0.75rem 0 0", color: "#94a3b8", fontSize: "0.85rem" }}>
              現在の接続先: <code>{apiBaseUrl}</code>
            </p>
          </section>

          <label style={{ display: "block", marginTop: "1.5rem", marginBottom: "0.5rem", fontWeight: 600 }}>
            Time Slice
          </label>
          <select
            value={selectedTime}
            onChange={(event) => setSelectedTime(event.target.value)}
            style={{
              width: "100%",
              padding: "0.8rem 0.9rem",
              borderRadius: "0.8rem",
              border: "1px solid rgba(148, 163, 184, 0.25)",
              background: "rgba(15, 23, 42, 0.9)",
              color: "#f8fafc",
            }}
          >
            {times.map((time) => (
              <option key={time} value={time}>
                {time}
              </option>
            ))}
          </select>

          <section
            style={{
              marginTop: "1.25rem",
              padding: "1rem",
              borderRadius: "1rem",
              background: "rgba(15, 23, 42, 0.62)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
            }}
          >
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Grid Stats</h2>
            <p style={{ margin: "0.4rem 0" }}>API: <code>{apiBaseUrl}</code></p>
            <p style={{ margin: "0.4rem 0" }}>Cells: {stats?.cellCount ?? "-"}</p>
            <p style={{ margin: "0.4rem 0" }}>Max |z|: {stats ? stats.maxAbsZScore.toFixed(2) : "-"}</p>
            <p style={{ margin: "0.4rem 0" }}>Mean z: {stats ? stats.meanZScore.toFixed(2) : "-"}</p>
            <p style={{ margin: "0.4rem 0" }}>Status: {loading ? "loading" : "ready"}</p>
            {error ? <p style={{ marginBottom: 0, color: "#fca5a5" }}>{error}</p> : null}
          </section>

          <section
            style={{
              marginTop: "1.25rem",
              padding: "1rem",
              borderRadius: "1rem",
              background: "rgba(15, 23, 42, 0.62)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
            }}
          >
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Display Filters</h2>
            <label style={{ display: "block", marginBottom: "0.4rem" }}>
              Min sample count: <strong>{minSampleCount}</strong>
            </label>
            <input
              type="range"
              min={1}
              max={20}
              step={1}
              value={minSampleCount}
              onChange={(event) => setMinSampleCount(Number(event.target.value))}
              style={{ width: "100%" }}
            />

            <label style={{ display: "block", marginTop: "1rem", marginBottom: "0.4rem" }}>
              Min |z-score|: <strong>{minAbsZScore.toFixed(1)}</strong>
            </label>
            <input
              type="range"
              min={0}
              max={5}
              step={0.1}
              value={minAbsZScore}
              onChange={(event) => setMinAbsZScore(Number(event.target.value))}
              style={{ width: "100%" }}
            />

            <label style={{ display: "block", marginTop: "1rem", marginBottom: "0.4rem" }}>
              Fill opacity: <strong>{fillOpacity.toFixed(2)}</strong>
            </label>
            <input
              type="range"
              min={0.1}
              max={1}
              step={0.01}
              value={fillOpacity}
              onChange={(event) => setFillOpacity(Number(event.target.value))}
              style={{ width: "100%" }}
            />
          </section>

          <section style={{ marginTop: "1.25rem" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "0.5rem" }}>
              {[
                ["z ≤ -3", "#0b3c5d"],
                ["-1", "#65a9d7"],
                ["0", "#f8fafc"],
                ["+1", "#f59e0b"],
                ["z ≥ +3", "#b91c1c"],
              ].map(([label, color]) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
                  <span style={{ width: "1.2rem", height: "1.2rem", borderRadius: "0.3rem", background: color }} />
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>

        <section style={{ position: "relative" }}>
          <div ref={mapContainerRef} style={{ position: "absolute", inset: 0 }} />
        </section>
      </div>
    </main>
  );
}
