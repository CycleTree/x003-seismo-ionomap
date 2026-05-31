const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  return (
    <main
      style={{
        minHeight: "100vh",
        fontFamily: "sans-serif",
        display: "grid",
        placeItems: "center",
        background: "#f3f4f6",
        color: "#111827",
      }}
    >
      <section
        style={{
          padding: "2rem",
          borderRadius: "1rem",
          background: "#ffffff",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.08)",
          maxWidth: "42rem",
        }}
      >
        <h1 style={{ marginTop: 0 }}>seismo-ionomap</h1>
        <p>Frontend and backend containers are wired up.</p>
        <p>
          API base URL: <code>{apiBaseUrl}</code>
        </p>
      </section>
    </main>
  );
}
