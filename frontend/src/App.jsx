import { useState, useEffect } from "react";
import Sidebar from "./components/SideBar";
import MapView from "./components/MapView";
import Login from "./components/Login";
import "./App.css";

function App() {
  const [token, setToken] = useState(localStorage.getItem("luximmo_token"));
  const [selectedIndicator, setSelectedIndicator] = useState("prix_score");
  const [selectedYear, setSelectedYear] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [compareZone, setCompareZone] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareTarget, setCompareTarget] = useState("A");

  if (!token) {
    return <Login onLoginSuccess={setToken} />;
  }

  return (
    <div className="app">
      <Sidebar
        selectedIndicator={selectedIndicator}
        setSelectedIndicator={setSelectedIndicator}
        selectedYear={selectedYear}
        setSelectedYear={setSelectedYear}
        selectedZone={selectedZone}
        compareZone={compareZone}
        compareMode={compareMode}
        setCompareMode={setCompareMode}
        compareTarget={compareTarget}
        setCompareTarget={setCompareTarget}
        setSelectedZone={setSelectedZone}
        setCompareZone={setCompareZone}
      />

      <MapView
        selectedIndicator={selectedIndicator}
        selectedYear={selectedYear}
        compareMode={compareMode}
        compareTarget={compareTarget}
        selectedZone={selectedZone}
        compareZone={compareZone}
        setSelectedZone={setSelectedZone}
        setCompareZone={setCompareZone}
      />
    </div>
  );
}

export default App;