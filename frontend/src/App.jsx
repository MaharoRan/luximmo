import { useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import "./App.css";

function App() {
  const [selectedIndicator, setSelectedIndicator] = useState("quality");
  const [selectedYear, setSelectedYear] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [compareZone, setCompareZone] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareTarget, setCompareTarget] = useState("A");

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
        setSelectedZone={setSelectedZone}
        setCompareZone={setCompareZone}
      />
    </div>
  );
}

export default App;