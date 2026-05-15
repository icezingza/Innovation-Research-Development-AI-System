import React from 'react';
import './index.css';

const App: React.FC = () => {
  return (
    <div className="layout">
      <nav className="navbar">
        <h1>NamoNexus Dashboard</h1>
      </nav>
      <div className="kpi-container">
        <div className="kpi-pill">System Health: Normal</div>
        <div className="kpi-pill">Active Agents: 12</div>
      </div>
      <main className="content">
        <h2>System Overview</h2>
        {/* Main Dashboard Content Goes Here */}
      </main>
    </div>
  );
};

export default App;
