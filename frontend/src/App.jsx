import { useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import "./App.css";

function App() {
  const [selectedIndicator, setSelectedIndicator] = useState("quality");
  const [selectedZone, setSelectedZone] = useState(null);

  return (
    <div className="app">
      <Sidebar
        selectedIndicator={selectedIndicator}
        setSelectedIndicator={setSelectedIndicator}
        selectedZone={selectedZone}
      />

      <MapView
        selectedIndicator={selectedIndicator}
        setSelectedZone={setSelectedZone}
      />
    </div>
  );
}

export default App;